"""
一次性脚本：用 DeepSeek API 重新生成所有存量文档
独立进程运行，不依赖 FastAPI/uvicorn，避免 uvloop 冲突
用法：python regen_docs.py
"""
import asyncio
import logging
import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from openai import AsyncOpenAI
from sqlmodel import Session, select
from database import engine
from models import Skill
from config import settings
from doc_generator.prompts import SYSTEM_PROMPT, DOC_GENERATION_PROMPT, SOURCE_NAME_MAP
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


async def generate_one(client: AsyncOpenAI, sem: asyncio.Semaphore, skill: dict) -> dict:
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

    key = settings.OPENAI_API_KEY
    logger.info(f"模型: {settings.OPENAI_MODEL}")
    logger.info(f"Base URL: {settings.OPENAI_BASE_URL}")
    logger.info(f"API Key: {key[:8]}...{key[-4:]}")

    # 读取所有技能（全部重新生成，确保文档质量一致）
    with Session(engine) as session:
        all_skills = session.exec(select(Skill)).all()
        skills_data = [
            {
                "id": s.id,
                "title": s.title,
                "source": s.source,
                "source_url": s.source_url,
                "raw_content": s.raw_content,
            }
            for s in all_skills
        ]

    total = len(skills_data)
    logger.info(f"\n共 {total} 条技能需要生成文档，并发数: {settings.DOC_GEN_CONCURRENCY}\n")

    client = AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
    )
    sem = asyncio.Semaphore(settings.DOC_GEN_CONCURRENCY)

    results = await asyncio.gather(*[generate_one(client, sem, s) for s in skills_data])

    # 写回数据库
    success, fail = 0, 0
    with Session(engine) as session:
        for r in results:
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

    await client.close()
    logger.info(f"\n{'='*50}")
    logger.info(f"完成！✅ 成功: {success}  ❌ 失败: {fail}")


if __name__ == "__main__":
    asyncio.run(main())
