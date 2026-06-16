"""
skill-generator 配置模块
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置，支持从 .env 文件或环境变量读取"""

    # --- 应用设置 ---
    APP_NAME: str = "skill-generator"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # --- 数据库 ---
    DATABASE_URL: str = "sqlite:///./data/skills.db"

    # --- LLM API 设置 ---
    # 支持 OpenAI / DeepSeek 等兼容 OpenAI 格式的 API
    # DeepSeek: OPENAI_BASE_URL=https://api.deepseek.com/v1, OPENAI_MODEL=deepseek-chat
    LLM_PROVIDER: str = "deepseek"
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: Optional[str] = None
    OPENAI_MODEL: str = "deepseek-chat"

    # --- 爬虫设置 ---
    CRAWL_GITHUB_ENABLED: bool = True
    CRAWL_HACKERNEWS_ENABLED: bool = True
    CRAWL_DEVTO_ENABLED: bool = True
    CRAWL_PRODUCTHUNT_ENABLED: bool = True
    CRAWL_SKILLHUB_ENABLED: bool = True  # Stack Overflow Blog
    CRAWL_SKILLHUB_CLUB_ENABLED: bool = True  # skillhub.club (AI Skill 市集)
    # SkillHub Club API Key（可选，无则降级为页面爬取）
    # 在 https://www.skillhub.club/account/developer 获取
    SKILLHUB_CLUB_API_KEY: str = ""

    # --- 调度器设置 ---
    SCHEDULER_ENABLED: bool = True
    SCHEDULER_HOUR: int = 8
    SCHEDULER_MINUTE: int = 0
    SCHEDULER_TIMEZONE: str = "Asia/Shanghai"

    # --- 文档生成设置 ---
    DOC_GEN_CONCURRENCY: int = 5  # 并发生成文档数

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
