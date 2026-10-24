#!/usr/bin/env python3
"""
跨 Agent 记忆系统 — Mem0 嵌入式 CLI
用法:
  python .memory/mem.py add "完成的事情..."
  python .memory/mem.py search "关键词"
  python .memory/mem.py list
  python .memory/mem.py reset
"""

import os
import re
import sys

MEMORY_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, MEMORY_DIR)

try:
    from config import CONFIG
    from mem0 import Memory
    MEM0_AVAILABLE = True
except ImportError as e:
    MEM0_AVAILABLE = False
    IMPORT_ERROR = str(e)

_memory = None

# mem0 >= 2.0 起，实体参数不能再作为顶层关键字传给 search/get_all/get，
# 必须放进 filters；add/delete_all 仍接受顶层 user_id。
USER_ID = "agent"
_FILTER = {"user_id": USER_ID}

_CJK = re.compile(r"[\u4e00-\u9fff]")


def _english_query(text: str) -> str:
    """嵌入模型 all-MiniLM-L6-v2 只认英文，中文查询向量化后与英文记忆几乎不相似
    （实测相似度 0.08 < mem0 默认阈值 0.1，会直接返回“无匹配”）。
    记忆本身由 LLM 抽取成英文，所以这里把中文查询译成英文再检索；失败则原样返回。
    """
    if not _CJK.search(text):
        return text
    try:
        from openai import OpenAI

        cfg = CONFIG["llm"]["config"]
        client = OpenAI(api_key=cfg["api_key"], base_url=cfg["openai_base_url"])
        resp = client.chat.completions.create(
            model=cfg["model"],
            messages=[
                {
                    "role": "system",
                    "content": "Translate the user's search query into a short English "
                    "search phrase. Output the translation only, no quotes, no explanation.",
                },
                {"role": "user", "content": text},
            ],
            temperature=0,
            max_tokens=120,
        )
        translated = (resp.choices[0].message.content or "").strip()
        return translated or text
    except Exception:
        return text


def _check_deps():
    if not MEM0_AVAILABLE:
        print(f"依赖未安装: {IMPORT_ERROR}")
        print("\n请运行:")
        print("  pip3 install mem0ai sentence-transformers qdrant-client")
        print("\n并确保 DEEPSEEK_API_KEY 已设置（echo DEEPSEEK_API_KEY=sk-xxxx > .env）")
        sys.exit(1)


def _get_memory():
    global _memory
    if _memory is None:
        _memory = Memory.from_config(CONFIG)
    return _memory


def add(text: str):
    _check_deps()
    m = _get_memory()
    result = m.add(text, user_id=USER_ID)
    results = result.get("results", []) if isinstance(result, dict) else (result or [])
    for r in results:
        mem_text = r.get("memory", "") if isinstance(r, dict) else str(r)
        if mem_text:
            print(f"  ✓ {mem_text}")
    print(f"\n已添加 {len(results)} 条记忆")


def search(query: str, limit: int = 10):
    _check_deps()
    m = _get_memory()
    q = _english_query(query)
    if q != query:
        print(f"（中文查询已译为英文检索：{q}）")
    results = m.search(q, top_k=limit, filters=_FILTER)
    if isinstance(results, dict):
        results = results.get("results", [])
    if not results:
        print("无匹配记忆")
        return
    for i, r in enumerate(results):
        mem = r.get("memory", str(r)) if isinstance(r, dict) else str(r)
        score = r.get("score", 0) if isinstance(r, dict) else 0
        print(f"{i+1}. [{score:.2f}] {mem}")


def list_all():
    _check_deps()
    m = _get_memory()
    results = m.get_all(filters=_FILTER, top_k=100)
    if isinstance(results, dict):
        results = results.get("results", [])
    if not results:
        print("暂无记忆")
        return
    print(f"共 {len(results)} 条记忆:\n")
    for i, r in enumerate(results):
        mem = r.get("memory", str(r)) if isinstance(r, dict) else str(r)
        print(f"{i+1}. {mem}")


def reset():
    _check_deps()
    m = _get_memory()
    m.delete_all(user_id=USER_ID)
    print("已清空全部记忆")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "add":
        text = sys.argv[2] if len(sys.argv) > 2 else sys.stdin.read().strip()
        if not text:
            print("用法: python .memory/mem.py add '记忆内容...'")
            sys.exit(1)
        add(text)
    elif cmd == "search":
        query = sys.argv[2] if len(sys.argv) > 2 else sys.stdin.read().strip()
        if not query:
            print("用法: python .memory/mem.py search '搜索关键词'")
            sys.exit(1)
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        search(query, limit)
    elif cmd == "list":
        list_all()
    elif cmd == "reset":
        reset()
    else:
        print(f"未知命令: {cmd}")
        print(__doc__)
        sys.exit(1)
