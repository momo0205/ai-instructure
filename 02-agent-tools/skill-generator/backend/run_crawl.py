"""
完整爬取 + DeepSeek 文档生成脚本
独立运行，不经过 uvicorn/uvloop，避免 httpcore 连接池问题
用法：python run_crawl.py
"""
import asyncio
import logging
import os
import sys
from datetime import datetime

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from openai import AsyncOpenAI
from sqlmodel import Session, select
from database import engine, init_db
from models import Skill, CrawlJob
from config import settings
from doc_generator.prompts import SYSTEM_PROMPT, DOC_GENERATION_PROMPT, SOURCE_NAME_MAP
from crawler.github_trending import GitHubTrendingCrawler
from crawler.hackernews import HackerNewsCrawler
from crawler.devto import DevtoCrawler
from crawler.producthunt import ProductHuntCrawler
from crawler.skillhub import SkillHubCrawler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)
# 静默 SQLAlchemy 输出
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


async def generate_doc(client: AsyncOpenAI, sem: asyncio.Semaphore, skill: dict) -> dict:
    source_display = SOURCE_NAME_MAP.get(skill["source"], skill["source"])
    prompt = DOC_GENERATION_PROMPT.format(
        title=skill["title"],
        source=source_display,
        source_url=skill["source_url"],
        raw_content=skill["raw_content"],
    )
    async with sem:
        try:
            resp = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=2000,
            )
            doc = resp.choices[0].message.content or ""
            logger.info(f"  ✅ [{skill['source']:12s}] {skill['title'][:45]}")
            return {"id": skill["id"], "doc": doc, "ok": True}
        except Exception as e:
            logger.error(f"  ❌ [{skill['source']:12s}] {skill['title'][:45]} => {e}")
            return {"id": skill["id"], "doc": None, "ok": False}


async def main():
    if not settings.OPENAI_API_KEY:
        logger.error("未配置 OPENAI_API_KEY，请检查 backend/.env")
        sys.exit(1)

    init_db()
    key = settings.OPENAI_API_KEY
    logger.info(f"模型: {settings.OPENAI_MODEL} | Base URL: {settings.OPENAI_BASE_URL}")
    logger.info(f"API Key: {key[:8]}...{key[-4:]}\n")

    # ── 步骤 1：并发爬取 ──────────────────────────────
    logger.info("【Step 1】启动爬虫...")
    crawlers = []
    if settings.CRAWL_GITHUB_ENABLED:    crawlers.append(GitHubTrendingCrawler())
    if settings.CRAWL_HACKERNEWS_ENABLED: crawlers.append(HackerNewsCrawler())
    if settings.CRAWL_DEVTO_ENABLED:     crawlers.append(DevtoCrawler())
    if settings.CRAWL_PRODUCTHUNT_ENABLED: crawlers.append(ProductHuntCrawler())
    if settings.CRAWL_SKILLHUB_ENABLED:  crawlers.append(SkillHubCrawler())

    results = await asyncio.gather(*[c.safe_crawl() for c in crawlers], return_exceptions=True)

    all_items = []
    for r in results:
        if isinstance(r, list):
            all_items.extend(r)

    logger.info(f"爬取完成，共获得 {len(all_items)} 条原始数据")

    # ── 步骤 2：去重写库 ──────────────────────────────
    logger.info("\n【Step 2】去重并写入数据库...")
    saved_skill_ids = []
    with Session(engine) as session:
        for item in all_items:
            existing = session.exec(
                select(Skill).where(Skill.source_url == item.source_url)
            ).first()
            if existing:
                continue
            skill = Skill(
                title=item.title,
                source=item.source,
                source_url=item.source_url,
                description=item.description,
                raw_content=item.raw_content,
                tags=item.tags,
                stars=item.stars,
                language=item.language,
                crawled_at=datetime.now(),
            )
            session.add(skill)
            try:
                session.commit()
                session.refresh(skill)
                saved_skill_ids.append(skill.id)
            except Exception:
                session.rollback()

    logger.info(f"新增 {len(saved_skill_ids)} 条技能")

    if not saved_skill_ids:
        logger.info("没有新技能需要生成文档")
        return

    # ── 步骤 3：DeepSeek 批量生成文档 ──────────────────
    logger.info(f"\n【Step 3】调用 DeepSeek 生成文档（并发: {settings.DOC_GEN_CONCURRENCY}）...")
    client = AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
    )
    sem = asyncio.Semaphore(settings.DOC_GEN_CONCURRENCY)

    # 重新从 DB 读取（避免 DetachedInstanceError）
    with Session(engine) as session:
        skills_data = []
        for sid in saved_skill_ids:
            s = session.get(Skill, sid)
            if s:
                skills_data.append({
                    "id": s.id, "title": s.title, "source": s.source,
                    "source_url": s.source_url, "raw_content": s.raw_content,
                })

    doc_results = await asyncio.gather(*[generate_doc(client, sem, s) for s in skills_data])
    await client.close()

    # ── 步骤 4：写回文档 ──────────────────────────────
    logger.info("\n【Step 4】写回文档...")
    success, fail = 0, 0
    with Session(engine) as session:
        for r in doc_results:
            if r["ok"] and r["doc"]:
                skill = session.get(Skill, r["id"])
                if skill:
                    skill.doc_markdown = r["doc"]
                    skill.doc_generated_at = datetime.now()
                    skill.is_doc_ready = True
                    session.add(skill)
                    success += 1
            else:
                fail += 1
        session.commit()

    logger.info(f"\n{'='*55}")
    logger.info(f"全部完成！✅ 文档生成成功: {success}  ❌ 失败: {fail}")
    logger.info(f"现在可以访问 http://localhost:5173 查看效果")


if __name__ == "__main__":
    asyncio.run(main())
