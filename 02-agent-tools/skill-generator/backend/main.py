"""
skill-generator 后端主入口
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from database import init_db
from scheduler import init_scheduler
from api.skills import router as skills_router
from api.jobs import router as jobs_router

# 日志配置
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动
    logger.info(f"🚀 {settings.APP_NAME} 启动中...")
    init_db()
    logger.info("✅ 数据库初始化完成")
    init_scheduler()
    logger.info("✅ 调度器初始化完成")
    yield
    # 关闭
    logger.info("🛑 应用关闭")


app = FastAPI(
    title="Skill Generator API",
    description="定时爬取互联网实用技能，并自动生成中文文档",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Demo 阶段允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(skills_router)
app.include_router(jobs_router)


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "scheduler_enabled": settings.SCHEDULER_ENABLED,
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.OPENAI_MODEL,
    }


@app.post("/api/test-llm")
async def test_llm():
    """测试 LLM 连接（诊断用）"""
    import httpx, traceback
    from doc_generator.prompts import SYSTEM_PROMPT, DOC_GENERATION_PROMPT
    url = f"{settings.OPENAI_BASE_URL.rstrip('/')}/chat/completions"
    # 用真实的文档生成 prompt 测试
    prompt = DOC_GENERATION_PROMPT.format(
        title="Test Skill",
        source="GitHub Trending",
        source_url="https://github.com/test",
        raw_content="A test skill for debugging. Stars: 100. Language: Python.",
    )
    try:
        transport = httpx.AsyncHTTPTransport(retries=0)
        async with httpx.AsyncClient(
            transport=transport,
            timeout=httpx.Timeout(connect=10.0, read=90.0, write=10.0, pool=5.0),
        ) as client:
            resp = await client.post(
                url,
                json={"model": settings.OPENAI_MODEL, "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ], "max_tokens": 2000},
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}", "Content-Type": "application/json"},
            )
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return {"status": resp.status_code, "ok": True, "doc_length": len(content), "preview": content[:200]}
    except Exception as e:
        tb = traceback.format_exc()
        return {"error": type(e).__name__, "detail": str(e), "traceback": tb[-800:]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
