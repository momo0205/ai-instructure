"""
skill-generator 数据模型
"""
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class Skill(SQLModel, table=True):
    """技能/工具实体"""

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True, description="技能名称")
    source: str = Field(index=True, description="来源：github/producthunt/hackernews/devto")
    source_url: str = Field(unique=True, description="原始链接（用于去重）")
    description: str = Field(default="", description="原始描述/摘要")
    raw_content: str = Field(default="", description="爬取的原始内容")
    doc_markdown: Optional[str] = Field(default=None, description="AI 生成的中文文档（Markdown）")
    tags: Optional[str] = Field(default=None, description="标签（JSON 数组字符串）")
    stars: Optional[int] = Field(default=None, description="GitHub stars / 点赞数")
    language: Optional[str] = Field(default=None, description="编程语言")
    crawled_at: datetime = Field(default_factory=datetime.now, description="爬取时间")
    doc_generated_at: Optional[datetime] = Field(default=None, description="文档生成时间")
    is_doc_ready: bool = Field(default=False, description="文档是否已生成")


class CrawlJob(SQLModel, table=True):
    """爬取任务记录"""

    id: Optional[int] = Field(default=None, primary_key=True)
    triggered_by: str = Field(description="触发方式：scheduler / manual")
    status: str = Field(default="running", description="状态：running / done / failed")
    total: int = Field(default=0, description="总爬取数")
    success: int = Field(default=0, description="成功数")
    failed: int = Field(default=0, description="失败数")
    started_at: datetime = Field(default_factory=datetime.now, description="开始时间")
    finished_at: Optional[datetime] = Field(default=None, description="结束时间")
    error_msg: Optional[str] = Field(default=None, description="错误信息")


# --- Pydantic 响应模型 ---

class SkillListItem(SQLModel):
    """技能列表项（不含完整文档内容）"""
    id: int
    title: str
    source: str
    source_url: str
    description: str
    tags: Optional[str] = None
    stars: Optional[int] = None
    language: Optional[str] = None
    crawled_at: datetime
    is_doc_ready: bool


class SkillDetail(SQLModel):
    """技能详情（含完整文档）"""
    id: int
    title: str
    source: str
    source_url: str
    description: str
    raw_content: str
    doc_markdown: Optional[str] = None
    tags: Optional[str] = None
    stars: Optional[int] = None
    language: Optional[str] = None
    crawled_at: datetime
    doc_generated_at: Optional[datetime] = None
    is_doc_ready: bool


class CrawlJobResponse(SQLModel):
    """爬取任务响应"""
    id: int
    triggered_by: str
    status: str
    total: int
    success: int
    failed: int
    started_at: datetime
    finished_at: Optional[datetime] = None
    error_msg: Optional[str] = None


class PaginatedResponse(SQLModel):
    """分页响应"""
    items: list = []
    total: int = 0
    page: int = 1
    page_size: int = 20
