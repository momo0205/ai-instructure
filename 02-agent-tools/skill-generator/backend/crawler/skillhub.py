"""
Stack Overflow Blog 爬虫（替代原 SkillHub 爬虫）

Stack Overflow Blog 是什么：
  Stack Overflow 官方技术博客，发布工程实践、职业发展、技术趋势等深度文章。
  内容质量极高，作者均为资深工程师，天然适合提炼为 Skill。
  https://stackoverflow.blog/feed/

保留的内容类型：
  - 工程实践类文章（how-to, architecture, best practices）
  - 工具/语言深度介绍
  
过滤的内容类型：
  - podcast（播客节目，没有可读文字内容）
  - 纯商业/招聘类文章
"""
import re
import json
import logging
from xml.etree import ElementTree as ET
from .base import BaseCrawler, CrawledItem

logger = logging.getLogger(__name__)

# SO Blog 的 RSS 命名空间
DC_NS = "http://purl.org/dc/elements/1.1/"
CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"

# 过滤播客和非技术内容
EXCLUDE_CATEGORIES = {"podcast", "bulletin", "announcements", "stackoverflow-news"}
EXCLUDE_TITLE_HINTS = [
    "podcast", "episode", "listen now", "survey says",
    "stack overflow is hiring", "stack overflow for teams",
]

# 只保留技术类文章
TECH_CATEGORIES = {
    "engineering", "open-source", "ai", "ml", "performance",
    "security", "devops", "javascript", "python", "rust", "go",
    "cloud", "databases", "architecture", "tools", "se-tech",
    "tutorial", "how-to", "best-practices", "tips",
}


class SkillHubCrawler(BaseCrawler):
    """
    Stack Overflow Blog 爬虫
    （原 SkillHub 爬虫的替代实现，source_name 保持 skillhub 以兼容前端显示）
    """

    source_name = "skillhub"
    FEED_URL = "https://stackoverflow.blog/feed/"

    async def crawl(self) -> list[CrawledItem]:
        resp = await self.client.get(
            self.FEED_URL,
            headers={"User-Agent": "skill-generator/1.0 RSS reader"},
        )
        resp.raise_for_status()

        root = ET.fromstring(resp.text)
        raw_items = root.findall(".//item")

        logger.info(f"[skillhub/SO Blog] RSS 获得 {len(raw_items)} 条文章")

        items = []
        for raw in raw_items:
            # 标题
            title_el = raw.find("title")
            title = (title_el.text or "").strip() if title_el is not None else ""
            if not title:
                continue

            # 链接
            link_el = raw.find("link")
            source_url = (link_el.text or "").strip() if link_el is not None else ""
            if not source_url:
                continue

            # 分类标签
            categories = [
                (c.text or "").strip().lower()
                for c in raw.findall("category")
                if c.text
            ]

            # 过滤播客和非技术内容
            title_lower = title.lower()
            if any(hint in title_lower for hint in EXCLUDE_TITLE_HINTS):
                logger.debug(f"[skillhub] 播客/噪音过滤: {title}")
                continue

            if any(cat in EXCLUDE_CATEGORIES for cat in categories):
                logger.debug(f"[skillhub] 分类过滤({categories}): {title}")
                continue

            # 优先保留技术类文章（categories 有交集，或没有 categories 时放行）
            if categories and not any(cat in TECH_CATEGORIES for cat in categories):
                logger.debug(f"[skillhub] 非技术分类过滤({categories}): {title}")
                continue

            # 描述
            desc_el = raw.find("description")
            description = _clean_desc(desc_el.text or "" if desc_el is not None else "")

            # 作者
            creator_el = raw.find(f"{{{DC_NS}}}creator")
            author = (creator_el.text or "").strip() if creator_el is not None else ""

            # 发布日期
            pubdate_el = raw.find("pubDate")
            pub_date = (pubdate_el.text or "").strip() if pubdate_el is not None else ""

            # raw_content：能给 AI 提炼的素材
            raw_content = (
                f"# {title}\n\n"
                f"{description}\n\n"
                f"来源：Stack Overflow Blog\n"
                f"作者：{author}\n"
                f"发布时间：{pub_date}\n"
                f"分类：{', '.join(categories)}\n"
                f"原始链接：{source_url}"
            )

            logger.info(f"[skillhub] ✅ {title[:60]}")
            items.append(CrawledItem(
                title=title,
                source="skillhub",
                source_url=source_url,
                description=description[:200] if description else title,
                raw_content=raw_content,
                tags=json.dumps(categories[:5]) if categories else None,
            ))

        logger.info(f"[skillhub/SO Blog] 最终获得 {len(items)} 条技术文章")
        return items[:20]


def _clean_desc(text: str) -> str:
    """清理描述文字中的 HTML 标签"""
    text = re.sub(r"<[^>]+>", "", text)
    text = (text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
            .replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " "))
    return text.strip()
