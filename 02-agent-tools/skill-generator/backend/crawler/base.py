"""
爬虫基类
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
import httpx
import logging

logger = logging.getLogger(__name__)


@dataclass
class CrawledItem:
    """爬取结果项"""
    title: str
    source: str
    source_url: str
    description: str = ""
    raw_content: str = ""
    tags: Optional[str] = None
    stars: Optional[int] = None
    language: Optional[str] = None


class BaseCrawler(ABC):
    """爬虫抽象基类"""

    source_name: str = "unknown"

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "skill-generator/1.0 (https://github.com/skill-generator)"
            },
            follow_redirects=True,
        )

    async def close(self):
        await self.client.aclose()

    @abstractmethod
    async def crawl(self) -> list[CrawledItem]:
        """执行爬取，返回结果列表"""
        ...

    async def safe_crawl(self) -> list[CrawledItem]:
        """安全执行爬取，捕获异常"""
        try:
            items = await self.crawl()
            logger.info(f"[{self.source_name}] 爬取完成，获得 {len(items)} 条结果")
            return items
        except Exception as e:
            logger.error(f"[{self.source_name}] 爬取失败: {e}")
            return []
        finally:
            await self.close()
