import os
from pathlib import Path

MEMORY_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = MEMORY_DIR.parent


def _load_env():
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


_load_env()

DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

if not DEEPSEEK_KEY:
    raise RuntimeError(
        "DEEPSEEK_API_KEY 未设置。请创建项目根目录的 .env 文件:\n"
        '  echo DEEPSEEK_API_KEY=sk-xxxx > .env\n'
        "或导出环境变量:\n"
        "  export DEEPSEEK_API_KEY=sk-xxxx"
    )

CONFIG = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "ai-workspace-memory",
            "path": str(MEMORY_DIR / "qdrant"),
            "embedding_model_dims": 384,
            "on_disk": True,
        },
    },
    "llm": {
        "provider": "openai",
        "config": {
            "api_key": DEEPSEEK_KEY,
            "model": "deepseek-flash",
            "openai_base_url": "https://api.deepseek.com/v1",
            "temperature": 0.1,
            "max_tokens": 1000,
        },
    },
    "embedder": {
        "provider": "huggingface",
        "config": {
            "model": "sentence-transformers/all-MiniLM-L6-v2",
        },
    },
    "history_db_path": str(MEMORY_DIR / "history.db"),
    "version": "v1.1",
}
