"""
Hacker News 爬虫
策略：
- 只保留「Ask HN」「Show HN」「技术工具/教程」类型的帖子
- 对于 Show HN/Ask HN，抓取帖子的 text 内容（帖子正文）
- 对于外链文章，通过 Algolia HN API 获取摘要
- 过滤掉纯新闻、观点文章、随笔
"""
import json
import asyncio
import logging
from .base import BaseCrawler, CrawledItem

logger = logging.getLogger(__name__)

# HN Algolia 搜索 API（可获取文章摘要）
ALGOLIA_SEARCH_URL = "https://hn.algolia.com/api/v1/search"

# 质量阈值
MIN_SCORE = 50      # 最低 HN 分数
MIN_COMMENTS = 10   # 最低评论数（有讨论价值的帖子）

# 技术关键词（出现在标题中则保留）
TECH_TITLE_KEYWORDS = [
    # 工程实践
    "how to", "how i", "how we", "building", "built", "i built",
    "guide", "tutorial", "step by step", "introduction to",
    "deep dive", "inside", "under the hood", "behind the scenes",
    "implementing", "implement", "deploy", "debugging", "benchmark",
    "architecture", "design", "pattern", "best practice",
    # 工具类
    "open source", "show hn", "ask hn", "launch hn",
    "cli", "tool", "library", "framework", "api", "sdk",
    "rust", "python", "go lang", "typescript", "llm", "ai agent",
    "database", "postgres", "sqlite", "redis", "kafka",
    "docker", "kubernetes", "terraform", "linux", "shell",
    "git", "ci/cd", "devops", "microservice", "serverless",
    "performance", "memory", "cache", "async", "concurrency",
    "security", "encryption", "auth", "oauth",
    # 技术洞察
    "what i learned", "lessons from", "mistakes", "pitfalls",
    "why we switched", "migrating from", "replacing",
]

# 噪音标题关键词（直接排除）
NOISE_TITLE_KEYWORDS = [
    "years of", "you are not", " – reflections", "opinion:",
    "collaboration is", "trillion dollar", "cigarette lighter",
    "vibe-coding spam", "mental health diary", "i'm quitting",
    "stock market", "bitcoin", "crypto price", "nft", "elon",
    "first and lego", "breaking news",
]

# 并发请求数
CONCURRENCY = 5


class HackerNewsCrawler(BaseCrawler):
    """Hacker News 爬虫（技术内容精筛版）"""

    source_name = "hackernews"
    TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
    BEST_STORIES_URL = "https://hacker-news.firebaseio.com/v0/beststories.json"
    ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"

    async def crawl(self) -> list[CrawledItem]:
        # 同时拉取 top + best，合并去重后筛选
        top_resp, best_resp = await asyncio.gather(
            self.client.get(self.TOP_STORIES_URL),
            self.client.get(self.BEST_STORIES_URL),
        )
        top_resp.raise_for_status()
        best_resp.raise_for_status()

        top_ids = set(top_resp.json()[:50])
        best_ids = set(best_resp.json()[:50])
        all_ids = list(top_ids | best_ids)[:80]  # 最多检查 80 个

        semaphore = asyncio.Semaphore(CONCURRENCY)

        async def fetch_story(story_id: int) -> dict | None:
            async with semaphore:
                try:
                    r = await self.client.get(self.ITEM_URL.format(story_id))
                    r.raise_for_status()
                    return r.json()
                except Exception:
                    return None

        stories_raw = await asyncio.gather(*[fetch_story(sid) for sid in all_ids])

        items = []
        seen_titles = set()

        for story in stories_raw:
            if not story or story.get("type") != "story":
                continue

            title = story.get("title", "").strip()
            if not title or title in seen_titles:
                continue

            score = story.get("score", 0)
            descendants = story.get("descendants", 0)
            by = story.get("by", "unknown")
            story_id = story.get("id")
            url = story.get("url", f"https://news.ycombinator.com/item?id={story_id}")
            text = story.get("text", "") or ""  # Show HN / Ask HN 的正文

            title_lower = title.lower()

            # 1. 噪音过滤
            if any(kw in title_lower for kw in NOISE_TITLE_KEYWORDS):
                logger.debug(f"[hn] 噪音过滤: {title}")
                continue

            # 2. 分数/评论过滤
            if score < MIN_SCORE:
                logger.debug(f"[hn] 分数不足({score}): {title}")
                continue

            # 3. 内容类型判断
            is_show_ask_hn = (
                title_lower.startswith("show hn:") or
                title_lower.startswith("ask hn:") or
                title_lower.startswith("launch hn:")
            )
            has_tech_keyword = any(kw in title_lower for kw in TECH_TITLE_KEYWORDS)

            if not is_show_ask_hn and not has_tech_keyword:
                logger.debug(f"[hn] 非技术内容过滤: {title}")
                continue

            seen_titles.add(title)

            # 构建 raw_content
            # 对于 Show HN / Ask HN，text 是帖子正文（含 HTML），清理后保留
            clean_text = _strip_html(text) if text else ""

            if clean_text:
                raw_content = (
                    f"# {title}\n\n"
                    f"{clean_text}\n\n"
                    f"---\n"
                    f"HN Score: {score} | Comments: {descendants} | By: {by}\n"
                    f"URL: {url}"
                )
            else:
                raw_content = (
                    f"# {title}\n\n"
                    f"HN Score: {score} | Comments: {descendants} | By: {by}\n"
                    f"URL: {url}\n\n"
                    f"(外链文章，请参考原始 URL 获取完整内容)"
                )

            description = f"HN Score: {score} | 评论: {descendants} | 作者: {by}"

            items.append(CrawledItem(
                title=title,
                source="hackernews",
                source_url=url,
                description=description,
                raw_content=raw_content,
                stars=score,
            ))

            logger.info(f"[hn] ✅ 保留: {title[:60]} (score={score})")

        logger.info(f"[hn] 最终保留 {len(items)} 条高质量技术帖")
        return items


def _strip_html(html_text: str) -> str:
    """简单清理 HN 帖子中的 HTML 标签"""
    import re
    # 把 <p> 换成换行
    text = re.sub(r"<p>", "\n\n", html_text)
    # 保留 <a> 的文字
    text = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>', r"\2 (\1)", text)
    # 移除其他标签
    text = re.sub(r"<[^>]+>", "", text)
    # 解码 HTML 实体
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&#x27;", "'").replace("&quot;", '"')
    return text.strip()
