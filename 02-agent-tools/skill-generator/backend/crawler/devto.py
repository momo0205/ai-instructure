"""
Dev.to 爬虫
使用官方 API 获取热门文章，并拉取每篇文章的完整正文（body_markdown）
质量过滤：reactions >= 5 或 comments >= 2
"""
import json
import asyncio
import logging
from .base import BaseCrawler, CrawledItem

logger = logging.getLogger(__name__)

# 噪音标题特征词（非技术性文章）
NOISE_TITLE_KEYWORDS = [
    "years of", "you are not your", "bullshit", "#100daysofcode day",
    "first and ", "vibe-coding spam", "trillion dollar", "lighter",
    "i'm quitting", "mental health", "burnout", "motivat",
    "coalescing - phase", "day 48 of", "day 49 of", "day 50 of",
]

# 技术性 tag，至少命中一个才保留（如果文章 tag 列表非空）
TECH_TAGS = {
    "python", "javascript", "typescript", "rust", "go", "java", "kotlin",
    "react", "vue", "nextjs", "node", "backend", "frontend", "webdev",
    "devops", "cloud", "aws", "azure", "gcp", "docker", "kubernetes",
    "ai", "ml", "llm", "openai", "api", "database", "sql", "nosql",
    "security", "performance", "tutorial", "beginners", "architecture",
    "productivity", "cli", "linux", "git", "testing", "ci", "cd",
    "mcp", "agent", "fastapi", "django", "rails", "rust", "wasm",
    "opensource", "programming", "engineering", "tooling",
}


class DevtoCrawler(BaseCrawler):
    """Dev.to 爬虫（使用官方 API，获取完整正文）"""

    source_name = "devto"
    LIST_URL = "https://dev.to/api/articles"
    DETAIL_URL = "https://dev.to/api/articles/{article_id}"

    # 并发限制（避免 429）
    CONCURRENCY = 5
    MIN_REACTIONS = 5   # 最少 reactions 数
    MIN_READING_TIME = 2  # 最少阅读时间（分钟），过滤掉太短的碎片文章

    async def crawl(self) -> list[CrawledItem]:
        # Step 1：获取热门文章列表（最近 3 天，取 50 条用于筛选）
        resp = await self.client.get(
            self.LIST_URL,
            params={
                "per_page": 50,
                "top": 3,  # 最近 3 天热门，比 1 天更稳定
            },
        )
        resp.raise_for_status()
        articles = resp.json()

        # Step 2：质量预筛选（在拉取正文之前，过滤掉明显的噪音）
        candidates = []
        for article in articles:
            title = article.get("title", "")
            reactions = article.get("positive_reactions_count", 0)
            reading_time = article.get("reading_time_minutes", 0)
            tag_list = [t.lower() for t in article.get("tag_list", [])]

            # 过滤噪音标题
            title_lower = title.lower()
            if any(kw in title_lower for kw in NOISE_TITLE_KEYWORDS):
                logger.debug(f"[devto] 噪音过滤: {title}")
                continue

            # 过滤低质量文章
            if reactions < self.MIN_REACTIONS:
                logger.debug(f"[devto] reactions 不足({reactions}): {title}")
                continue

            # 如果有 tag，过滤非技术性文章
            if tag_list and not any(t in TECH_TAGS for t in tag_list):
                logger.debug(f"[devto] 非技术 tag 过滤: {title} tags={tag_list}")
                continue

            # 阅读时间过滤（太短的文章内容通常稀薄）
            if reading_time < self.MIN_READING_TIME:
                logger.debug(f"[devto] 阅读时间过短({reading_time}min): {title}")
                continue

            candidates.append(article)

        logger.info(f"[devto] 预筛选后 {len(candidates)} 篇候选，开始拉取正文…")

        # Step 3：并发拉取完整正文（带并发限制）
        semaphore = asyncio.Semaphore(self.CONCURRENCY)

        async def fetch_full_article(article: dict) -> CrawledItem | None:
            article_id = article.get("id")
            title = article.get("title", "")
            async with semaphore:
                try:
                    detail_resp = await self.client.get(
                        self.DETAIL_URL.format(article_id=article_id)
                    )
                    detail_resp.raise_for_status()
                    detail = detail_resp.json()

                    body_markdown = detail.get("body_markdown", "") or ""
                    url = detail.get("url", article.get("url", ""))
                    description = detail.get("description", article.get("description", ""))
                    tag_list = detail.get("tag_list", article.get("tag_list", []))
                    reactions = detail.get("positive_reactions_count", article.get("positive_reactions_count", 0))
                    comments = detail.get("comments_count", article.get("comments_count", 0))
                    user = detail.get("user", {}).get("username", "unknown")
                    reading_time = detail.get("reading_time_minutes", 0)

                    # 正文太短说明内容稀薄（少于 300 字符），跳过
                    if len(body_markdown.strip()) < 300:
                        logger.debug(f"[devto] 正文过短({len(body_markdown)}字符): {title}")
                        return None

                    # raw_content = 完整正文（这才是 AI 提炼的真正素材）
                    raw_content = body_markdown

                    logger.info(f"[devto] ✅ 已获取正文 {len(body_markdown)} 字符: {title[:50]}")
                    return CrawledItem(
                        title=title,
                        source="devto",
                        source_url=url,
                        description=description,
                        raw_content=raw_content,
                        tags=json.dumps(tag_list) if tag_list else None,
                        stars=reactions,
                    )
                except Exception as e:
                    logger.warning(f"[devto] 拉取正文失败 ({title[:40]}): {e}")
                    return None

        tasks = [fetch_full_article(a) for a in candidates[:25]]  # 最多处理 25 篇
        results = await asyncio.gather(*tasks)

        items = [r for r in results if r is not None]
        logger.info(f"[devto] 最终获得 {len(items)} 条高质量文章（含完整正文）")
        return items
