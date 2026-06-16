"""
AI 文档/Skill 生成器 - 直接使用 httpx 调用 LLM
"""
import asyncio
import logging
import httpx
from datetime import datetime
from config import settings
from .prompts import (
    SYSTEM_PROMPT,
    DOC_GENERATION_PROMPT,
    SKILL_SYSTEM_PROMPT,
    SKILL_GENERATION_PROMPT,
    SOURCE_NAME_MAP,
)

logger = logging.getLogger(__name__)


async def _call_llm(prompt: str, system_prompt: str | None = None) -> str:
    """
    直接用 httpx 调用 OpenAI 兼容 API。
    - 每次请求创建新的 AsyncClient，避免 uvloop 下连接池冲突
    - stream=False 避免 uvloop 下 chunked 响应读取 ReadError
    """
    base_url = (settings.OPENAI_BASE_URL or "https://api.openai.com/v1").rstrip("/")
    url = f"{base_url}/chat/completions"

    payload = {
        "model": settings.OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt or SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 2000,
        "stream": False,  # 明确禁用流式响应
    }
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    transport = httpx.AsyncHTTPTransport(retries=1)
    async with httpx.AsyncClient(
        transport=transport,
        timeout=httpx.Timeout(connect=10.0, read=90.0, write=10.0, pool=10.0),
    ) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"] or ""


async def generate_doc_direct(title: str, source: str, source_url: str, raw_content: str) -> str:
    """生成介绍性文档（给人读的，展示在详情页）"""
    source_display = SOURCE_NAME_MAP.get(source, source)
    prompt = DOC_GENERATION_PROMPT.format(
        title=title,
        source=source_display,
        source_url=source_url,
        raw_content=raw_content,
    )
    doc = await _call_llm(prompt)
    logger.info(f"[DocGenerator] ✅ doc: {title[:40]}")
    return doc


async def generate_skill_instructions(
    title: str, source: str, source_url: str, raw_content: str
) -> str:
    """
    生成 Skill 操作指南（给 AI Agent 执行用的，下载时生成）。
    与 generate_doc_direct 的区别：
      - doc = 介绍性文章，告诉「是什么」
      - skill = Agent 指令集，告诉「怎么做」
    """
    source_display = SOURCE_NAME_MAP.get(source, source)
    prompt = SKILL_GENERATION_PROMPT.format(
        title=title,
        source=source_display,
        source_url=source_url,
        raw_content=raw_content,
    )
    skill_md = await _call_llm(prompt, system_prompt=SKILL_SYSTEM_PROMPT)
    logger.info(f"[SkillGenerator] ✅ skill: {title[:40]}")
    return skill_md


class DocGenerator:
    """批量文档生成器（供调度器使用，带 Semaphore 并发控制）"""

    def __init__(self):
        self.model = settings.OPENAI_MODEL
        logger.info(f"[DocGenerator] 模型: {self.model} | {settings.OPENAI_BASE_URL}")

    async def batch_generate(self, skills: list[dict]) -> list[dict]:
        """批量生成文档，使用 Semaphore 控制并发"""
        sem = asyncio.Semaphore(settings.DOC_GEN_CONCURRENCY)

        async def _gen(skill: dict) -> dict:
            async with sem:
                try:
                    doc = await generate_doc_direct(
                        title=skill["title"],
                        source=skill["source"],
                        source_url=skill["source_url"],
                        raw_content=skill["raw_content"],
                    )
                    return {"id": skill["id"], "doc_markdown": doc, "generated_at": datetime.now(), "ok": True}
                except Exception as e:
                    logger.error(f"[DocGenerator] ❌ {skill['title'][:30]}: {e}")
                    return {"id": skill["id"], "doc_markdown": None, "generated_at": datetime.now(), "ok": False}

        results = await asyncio.gather(*[_gen(s) for s in skills])
        return list(results)
