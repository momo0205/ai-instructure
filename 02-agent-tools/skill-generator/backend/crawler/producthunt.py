"""
Product Hunt 爬虫
使用官方 Atom RSS Feed（无需 API Token）
https://www.producthunt.com/feed

Product Hunt 是什么：
  每天精选当日最受关注的产品/工具发布，以开发者工具、AI 产品、SaaS 为主。
  对我们的价值：帮助发现「值得生成 Skill 的新工具」，Skill 内容聚焦在「这个工具怎么用」。
"""
import re
import json
import logging
from xml.etree import ElementTree as ET
from .base import BaseCrawler, CrawledItem

logger = logging.getLogger(__name__)

ATOM_NS = "http://www.w3.org/2005/Atom"

# 过滤非技术类产品（PH 上有很多营销/设计/生活类）
TECH_CATEGORY_HINTS = [
    "developer", "api", "cli", "open source", "code", "devtool",
    "ai", "llm", "ml", "automation", "workflow", "github", "saas",
    "cloud", "database", "terminal", "python", "javascript", "typescript",
    "deploy", "monitoring", "productivity", "engineering", "security",
    "framework", "library", "sdk", "platform", "integration", "plugin",
    "extension", "backend", "frontend", "infra", "server", "agent",
]

NOISE_HINTS = [
    "dating", "social media", "health", "fitness", "diet", "music",
    "photo", "video editor", "e-commerce shop", "wedding", "recipe",
    "travel", "fashion", "beauty",
]


class ProductHuntCrawler(BaseCrawler):
    """Product Hunt 爬虫（官方 Atom RSS Feed）"""

    source_name = "producthunt"
    FEED_URL = "https://www.producthunt.com/feed"

    async def crawl(self) -> list[CrawledItem]:
        resp = await self.client.get(
            self.FEED_URL,
            headers={"User-Agent": "skill-generator/1.0 RSS reader"},
        )
        resp.raise_for_status()

        root = ET.fromstring(resp.text)
        ns = {"atom": ATOM_NS}
        entries = root.findall("atom:entry", ns)

        logger.info(f"[producthunt] RSS 获得 {len(entries)} 条产品")

        items = []
        for entry in entries:
            # 标题
            title_el = entry.find("atom:title", ns)
            title = (title_el.text or "").strip() if title_el is not None else ""
            if not title:
                continue

            # 链接（在 link 标签的 href 属性里）
            link_el = entry.find("atom:link", ns)
            source_url = ""
            if link_el is not None:
                source_url = link_el.get("href", "")
            if not source_url:
                continue

            # 内容（HTML，需要清理）
            content_el = entry.find("atom:content", ns)
            raw_html = (content_el.text or "") if content_el is not None else ""
            description = _strip_html(raw_html).strip()

            # 发布时间
            published_el = entry.find("atom:published", ns)
            published = (published_el.text or "").strip() if published_el is not None else ""

            # 质量筛选：只保留技术类产品
            combined = (title + " " + description).lower()

            # 过滤明显的非技术产品
            if any(noise in combined for noise in NOISE_HINTS):
                logger.debug(f"[producthunt] 噪音过滤: {title}")
                continue

            # 不强制要求技术关键词（PH 上技术产品很多，宽松过滤即可）
            # 只过滤明显的噪音

            # raw_content：标题 + 描述 + 元信息
            raw_content = (
                f"# {title}\n\n"
                f"{description}\n\n"
                f"来源：Product Hunt\n"
                f"原始链接：{source_url}\n"
                f"发布时间：{published}"
            )

            logger.info(f"[producthunt] ✅ {title[:60]}")
            items.append(CrawledItem(
                title=title,
                source="producthunt",
                source_url=source_url,
                description=description[:200] if description else title,
                raw_content=raw_content,
                tags=json.dumps([]),
            ))

        logger.info(f"[producthunt] 最终获得 {len(items)} 条产品")
        return items[:20]


def _strip_html(html: str) -> str:
    """清理 HTML 标签，保留文字内容"""
    # 移除 script/style
    html = re.sub(r"<(script|style)[^>]*>.*?</(script|style)>", "", html, flags=re.DOTALL)
    # 换行符处理
    html = re.sub(r"<br\s*/?>|<p[^>]*>|</p>|<li[^>]*>", "\n", html)
    # 移除所有其他标签
    html = re.sub(r"<[^>]+>", "", html)
    # 解码 HTML 实体
    html = (html.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
            .replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " "))
    # 清理多余空白
    html = re.sub(r"\n{3,}", "\n\n", html)
    return html.strip()
