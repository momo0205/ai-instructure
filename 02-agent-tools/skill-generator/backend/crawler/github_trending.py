"""
GitHub Trending 爬虫
从 GitHub Trending 爬取热门仓库，并通过 GitHub API 获取 README 全文

策略：
- 只保留「工具类/框架类」仓库（有实际的使用教程价值）
- 通过 GitHub raw README API 获取完整 README
- 过滤掉 README 过短或明显是「课程/教程仓库」的结果
"""
import json
import asyncio
import logging
import base64
from bs4 import BeautifulSoup
from .base import BaseCrawler, CrawledItem

logger = logging.getLogger(__name__)

# README 内容最少字符数（太短的没有实际价值）
MIN_README_CHARS = 500

# 排除的仓库类型关键词（纯资源列表/课程/学习资料，不是工具）
EXCLUDE_KEYWORDS = [
    "awesome-", "awesome_", "learning", "interview", "roadmap",
    "cheatsheet", "cheat-sheet", "study", "curriculum", "notes",
    "book", "papers", "resources", "collection", "list of",
]

# 并发数（GitHub API 限制较严）
CONCURRENCY = 3


class GitHubTrendingCrawler(BaseCrawler):
    """GitHub Trending 爬虫（含 README 全文）"""

    source_name = "github"
    TRENDING_URL = "https://github.com/trending"
    README_API = "https://api.github.com/repos/{repo_path}/readme"
    REPO_API = "https://api.github.com/repos/{repo_path}"

    async def crawl(self) -> list[CrawledItem]:
        resp = await self.client.get(self.TRENDING_URL, params={"since": "daily"})
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        candidates = []

        for article in soup.select("article.Box-row"):
            h2 = article.select_one("h2 a")
            if not h2:
                continue

            repo_path = h2.get("href", "").strip("/")
            title = repo_path.replace("/", " / ")
            source_url = f"https://github.com/{repo_path}"

            # 描述
            desc_el = article.select_one("p")
            description = desc_el.get_text(strip=True) if desc_el else ""

            # 编程语言
            lang_el = article.select_one("[itemprop='programmingLanguage']")
            language = lang_el.get_text(strip=True) if lang_el else None

            # Stars
            stars = None
            for star_el in article.select("a.Link--muted"):
                if "/stargazers" in star_el.get("href", ""):
                    try:
                        stars = int(star_el.get_text(strip=True).replace(",", ""))
                    except ValueError:
                        pass
                    break

            # Today stars
            today_el = article.select_one("span.d-inline-block.float-sm-right")
            today_stars = today_el.get_text(strip=True) if today_el else ""

            # 过滤 awesome-list / 学习资料类仓库
            repo_lower = repo_path.lower()
            desc_lower = description.lower()
            if any(kw in repo_lower or kw in desc_lower for kw in EXCLUDE_KEYWORDS):
                logger.debug(f"[github] 排除非工具仓库: {title}")
                continue

            candidates.append({
                "repo_path": repo_path,
                "title": title,
                "source_url": source_url,
                "description": description,
                "language": language,
                "stars": stars,
                "today_stars": today_stars,
            })

        logger.info(f"[github] Trending 页面获得 {len(candidates)} 个候选仓库，开始拉取 README…")

        # 并发拉取 README
        semaphore = asyncio.Semaphore(CONCURRENCY)

        async def fetch_readme(info: dict) -> CrawledItem | None:
            repo_path = info["repo_path"]
            title = info["title"]
            async with semaphore:
                try:
                    # 优先尝试获取 README（GitHub API，支持无 token）
                    readme_resp = await self.client.get(
                        self.README_API.format(repo_path=repo_path),
                        headers={"Accept": "application/vnd.github.v3+json"},
                    )

                    if readme_resp.status_code == 200:
                        readme_data = readme_resp.json()
                        # README 内容是 base64 编码
                        content_b64 = readme_data.get("content", "")
                        readme_text = base64.b64decode(
                            content_b64.replace("\n", "")
                        ).decode("utf-8", errors="replace")

                        # 过滤太短的 README
                        if len(readme_text.strip()) < MIN_README_CHARS:
                            logger.debug(f"[github] README 过短({len(readme_text)}字符): {title}")
                            # 降级：使用描述 + 基本信息
                            readme_text = _build_fallback_content(info)
                    elif readme_resp.status_code == 404:
                        # 没有 README，降级为描述
                        readme_text = _build_fallback_content(info)
                    else:
                        readme_resp.raise_for_status()
                        readme_text = _build_fallback_content(info)

                    # 截断过长的 README（避免超出 LLM 上下文）
                    if len(readme_text) > 8000:
                        readme_text = readme_text[:8000] + "\n\n[README 内容已截断...]"

                    tags_list = [info["language"]] if info["language"] else []

                    logger.info(
                        f"[github] ✅ README {len(readme_text)} 字符: {title[:50]}"
                    )
                    return CrawledItem(
                        title=title,
                        source="github",
                        source_url=info["source_url"],
                        description=info["description"],
                        raw_content=readme_text,
                        tags=json.dumps(tags_list),
                        stars=info["stars"],
                        language=info["language"],
                    )

                except Exception as e:
                    logger.warning(f"[github] 拉取 README 失败 ({title}): {e}")
                    # 降级：至少保留基本信息
                    return CrawledItem(
                        title=title,
                        source="github",
                        source_url=info["source_url"],
                        description=info["description"],
                        raw_content=_build_fallback_content(info),
                        tags=json.dumps([info["language"]] if info["language"] else []),
                        stars=info["stars"],
                        language=info["language"],
                    )

        tasks = [fetch_readme(c) for c in candidates[:20]]  # 最多 20 个
        results = await asyncio.gather(*tasks)

        items = [r for r in results if r is not None]
        logger.info(f"[github] 最终获得 {len(items)} 条含 README 的仓库")
        return items


def _build_fallback_content(info: dict) -> str:
    """构建无 README 时的降级内容"""
    return (
        f"# {info['title']}\n\n"
        f"{info['description']}\n\n"
        f"Language: {info['language'] or 'N/A'}\n"
        f"Stars: {info['stars'] or 'N/A'} | Today: {info['today_stars']}\n"
        f"URL: {info['source_url']}"
    )
