"""
SkillHub Club (www.skillhub.club) 爬虫

skillhub.club 是什么：
  全球最大的 AI Agent Skill 市集，收录 3.5万+ 个为 Claude Code、Cursor、Gemini CLI 等 AI Agent
  设计的 Skill 包。每个 Skill 都有真实的 SKILL.md（包含触发场景、操作步骤、代码示例），
  由社区贡献并经 AI 多维度评分（S/A/B/C 级）。

爬取策略：
  1. 从 /skills 列表页抓取 Skill 详情页链接（页面 SSR 渲染）
  2. 并发访问每个详情页，提取 SKILL.md 全文（在 <pre> 标签中）
  3. raw_content = 真实的 SKILL.md，是 AI Skill 最高质量的素材

双模式（优先 API，降级为页面爬取）：
  - 有 SKILLHUB_CLUB_API_KEY 配置时：调用官方 API（更稳定，支持搜索排序）
  - 无 API Key 时：爬取页面（免费，仅能获取首页展示的热门 Skills）
"""
import asyncio
import json
import logging
import re
from bs4 import BeautifulSoup
from .base import BaseCrawler, CrawledItem

logger = logging.getLogger(__name__)

BASE_URL = "https://www.skillhub.club"
LIST_URL = f"{BASE_URL}/skills"
API_CATALOG_URL = f"{BASE_URL}/api/v1/skills/catalog"

CONCURRENCY = 3
MAX_SKILLS = 20


class SkillHubClubCrawler(BaseCrawler):
    """
    SkillHub Club 爬虫
    爬取真实 AI Skill（SKILL.md 内容），这是「完全可用的 Skill」的最佳来源
    """

    source_name = "skillhub_club"

    def __init__(self, api_key: str = ""):
        super().__init__()
        self.api_key = api_key
        # 设置浏览器 UA，避免被识别为爬虫
        self.client.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        })

    async def crawl(self) -> list[CrawledItem]:
        if self.api_key:
            return await self._crawl_via_api()
        else:
            return await self._crawl_via_page()

    # ─────────────────────────────────────────────────────────────────
    # 模式 A：有 API Key，走官方 API
    # ─────────────────────────────────────────────────────────────────
    async def _crawl_via_api(self) -> list[CrawledItem]:
        """使用官方 API 获取高评分 Skills 列表，再抓取详情页 SKILL.md"""
        logger.info("[skillhub_club] 使用 API Key 模式")
        resp = await self.client.get(
            API_CATALOG_URL,
            params={"limit": MAX_SKILLS, "sort": "score"},
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        resp.raise_for_status()
        data = resp.json()

        # API 返回格式：{ skills: [...], total: N }
        skills_list = data.get("skills") or data.get("items") or []
        logger.info(f"[skillhub_club] API 返回 {len(skills_list)} 条")

        semaphore = asyncio.Semaphore(CONCURRENCY)
        tasks = [
            self._fetch_skill_detail(
                slug=s.get("slug", "") or s.get("id", ""),
                meta=s,
                semaphore=semaphore,
            )
            for s in skills_list
            if s.get("slug") or s.get("id")
        ]
        results = await asyncio.gather(*tasks)
        items = [r for r in results if r]
        logger.info(f"[skillhub_club] 最终获得 {len(items)} 条 Skill")
        return items

    # ─────────────────────────────────────────────────────────────────
    # 模式 B：无 API Key，爬取页面
    # ─────────────────────────────────────────────────────────────────
    async def _crawl_via_page(self) -> list[CrawledItem]:
        """从列表页提取 Skill 链接，再并发抓取详情页"""
        logger.info("[skillhub_club] 无 API Key，使用页面爬取模式")

        resp = await self.client.get(LIST_URL)
        resp.raise_for_status()

        # 从 HTML 中提取 /skills/{slug} 链接
        # slug 格式：{owner}-{repo}-{skill-name}（至少含2个短横线）
        slugs = list(dict.fromkeys(
            re.findall(r'href="(/skills/[a-zA-Z0-9][a-zA-Z0-9\-]{4,})"', resp.text)
        ))
        # 过滤导航类链接（/skills/kol、/skills/hot 等）
        slugs = [s for s in slugs if s.count("-") >= 2]

        logger.info(f"[skillhub_club] 列表页发现 {len(slugs)} 个 Skill 链接")

        if not slugs:
            logger.warning("[skillhub_club] 未发现 Skill 链接，页面可能已变更结构")
            return []

        semaphore = asyncio.Semaphore(CONCURRENCY)
        tasks = [
            self._fetch_skill_detail(
                slug=slug.removeprefix("/skills/"),
                semaphore=semaphore,
            )
            for slug in slugs[:MAX_SKILLS]
        ]
        results = await asyncio.gather(*tasks)
        items = [r for r in results if r]
        logger.info(f"[skillhub_club] 最终获得 {len(items)} 条 Skill")
        return items

    # ─────────────────────────────────────────────────────────────────
    # 核心：抓取一个 Skill 详情页
    # ─────────────────────────────────────────────────────────────────
    async def _fetch_skill_detail(
        self,
        slug: str,
        meta: dict | None = None,
        semaphore: asyncio.Semaphore | None = None,
    ) -> CrawledItem | None:
        url = f"{BASE_URL}/skills/{slug}"
        ctx = semaphore or asyncio.Semaphore(1)
        async with ctx:
            try:
                resp = await self.client.get(url)
                resp.raise_for_status()
                return self._parse_skill_page(resp.text, url, meta)
            except Exception as e:
                logger.warning(f"[skillhub_club] 抓取失败 {slug}: {e}")
                return None

    def _parse_skill_page(
        self,
        html: str,
        url: str,
        meta: dict | None = None,
    ) -> CrawledItem | None:
        """从详情页 HTML 提取 Skill 信息"""
        soup = BeautifulSoup(html, "html.parser")

        # ── 1. 标题（h1）
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
        if not title and meta:
            title = meta.get("name") or meta.get("title") or ""
        if not title:
            return None

        # ── 2. 描述（meta description 最完整，含评分和目标用户）
        meta_desc_el = soup.find("meta", {"name": "description"})
        description = meta_desc_el.get("content", "") if meta_desc_el else ""
        if not description and meta:
            description = meta.get("description", "")

        # ── 3. SKILL.md 内容（<pre> 标签中，找包含 frontmatter 的那个）
        skill_md_content = ""
        for pre in soup.find_all("pre"):
            text = pre.get_text()
            # SKILL.md frontmatter 以 "---" 开头，且含 name: 和 description:
            if text.strip().startswith("---") and "description:" in text:
                skill_md_content = text.strip()
                break

        # ── 4. 评分（从 meta description 或 Schema 中提取）
        score_text = ""
        schema_scripts = soup.find_all("script", {"type": "application/ld+json"})
        stars_int = None
        for s in schema_scripts:
            try:
                d = json.loads(s.string or "")
                if isinstance(d, dict) and d.get("@type") == "SoftwareApplication":
                    rating = d.get("aggregateRating", {})
                    if rating:
                        score_text = str(rating.get("ratingValue", ""))
                    # stars/download count
                    interact = d.get("interactionStatistic", [])
                    for stat in (interact if isinstance(interact, list) else [interact]):
                        if "UserDownload" in str(stat.get("interactionType", "")) or \
                           "UserLike" in str(stat.get("interactionType", "")):
                            try:
                                stars_int = int(stat.get("userInteractionCount", 0))
                            except (ValueError, TypeError):
                                pass
            except Exception:
                pass

        # ── 5. 标签（从 category 或 tags 区域）
        tags = []
        if meta:
            tags = meta.get("tags") or meta.get("categories") or []
        # 尝试从 Schema 提取 category
        for s in schema_scripts:
            try:
                d = json.loads(s.string or "")
                if isinstance(d, dict) and d.get("@type") == "SoftwareApplication":
                    cat = d.get("applicationCategory", "")
                    if cat and cat not in tags:
                        tags.append(cat)
            except Exception:
                pass

        # ── 6. 组装 raw_content
        # SKILL.md 内容是最高质量的素材：真实的触发场景、操作步骤、代码示例
        if skill_md_content:
            raw_content = (
                f"# {title}\n\n"
                f"{description}\n\n"
                f"---\n\n"
                f"## SKILL.md 内容\n\n"
                f"{skill_md_content}\n\n"
                f"来源：SkillHub Club\n"
                f"原始链接：{url}"
            )
        else:
            # 没有 SKILL.md（可能页面结构变化），降级为描述
            raw_content = (
                f"# {title}\n\n"
                f"{description}\n\n"
                f"来源：SkillHub Club\n"
                f"原始链接：{url}"
            )
            logger.debug(f"[skillhub_club] 未找到 SKILL.md 内容: {title}")

        logger.info(
            f"[skillhub_club] ✅ {title[:50]} "
            f"(raw={len(raw_content)}字符, skill_md={len(skill_md_content)}字符)"
        )
        return CrawledItem(
            title=title,
            source="skillhub_club",
            source_url=url,
            description=description[:300] if description else title,
            raw_content=raw_content,
            tags=json.dumps(tags) if tags else None,
            stars=stars_int,
        )
