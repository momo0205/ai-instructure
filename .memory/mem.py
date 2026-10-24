#!/usr/bin/env python3
"""
跨 Agent 记忆系统 — Mem0 嵌入式 CLI

记忆分两层：
  .memory/ledger.jsonl   真相源，随 git 同步，纯文本可读可 diff
  .memory/qdrant/        向量索引，gitignore，可用 rebuild 从账本重建

用法:
  python3 .memory/mem.py add "完成的事情..."
  python3 .memory/mem.py search "关键词"
  python3 .memory/mem.py list
  python3 .memory/mem.py export    # 把现有索引导出到账本
  python3 .memory/mem.py rebuild   # 从账本重建索引（换机器后执行）
  python3 .memory/mem.py reset     # 清空索引（不动账本）
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

MEMORY_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, MEMORY_DIR)

# mem0 默认会在 ~/.mem0 下建配置与迁移目录。固定在仓库内，既避免污染 HOME，
# 也让 DSH 这类"只允许写工作区"的沙箱能够正常运行。
os.environ.setdefault("MEM0_DIR", os.path.join(MEMORY_DIR, ".cache"))

# 记忆的真相源：只追加的 JSONL，随 git 同步；向量库只是可重建的索引。
LEDGER = os.path.join(MEMORY_DIR, "ledger.jsonl")

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


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _ledger_append(text: str):
    """把原始记忆写入只追加账本。即使 mem0 / API 不可用也要先落盘。"""
    rec = {"ts": _now(), "text": text}
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def _ledger_read():
    if not os.path.exists(LEDGER):
        return []
    out = []
    with open(LEDGER, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _keyword_hits(query: str, limit: int):
    """无 API / 无 mem0 时的降级检索：在账本里做关键词或二元组匹配。"""
    q = query.strip().lower()
    grams = {q} if not _CJK.search(q) else {q[i : i + 2] for i in range(len(q) - 1)}
    scored = []
    for rec in _ledger_read():
        low = rec.get("text", "").lower()
        score = sum(1 for g in grams if g and g in low)
        if score:
            scored.append((score, rec))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:limit]]


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
    # 先落账本：账本是真相源，索引失败也不丢记忆
    _ledger_append(text)
    if not MEM0_AVAILABLE:
        print(f"  ✓ 已写入账本（mem0 不可用：{IMPORT_ERROR}）")
        print("    索引未更新，稍后可用: python3 .memory/mem.py rebuild")
        return
    try:
        m = _get_memory()
        result = m.add(text, user_id=USER_ID)
    except Exception as e:
        print(f"  ✓ 已写入账本，但索引更新失败：{e}")
        print("    稍后可用: python3 .memory/mem.py rebuild")
        return
    results = result.get("results", []) if isinstance(result, dict) else (result or [])
    for r in results:
        mem_text = r.get("memory", "") if isinstance(r, dict) else str(r)
        if mem_text:
            print(f"  ✓ {mem_text}")
    print(f"\n已写入账本，索引新增 {len(results)} 条事实")


def _print_hits(results):
    for i, r in enumerate(results):
        mem = r.get("memory") or r.get("text", "")
        score = r.get("score", 0)
        if score:
            print(f"{i+1}. [{score:.2f}] {mem}")
        else:
            print(f"{i+1}. {mem}")


def search(query: str, limit: int = 10):
    if MEM0_AVAILABLE:
        try:
            m = _get_memory()
            q = _english_query(query)
            if q != query:
                print(f"（中文查询已译为英文检索：{q}）")
            results = m.search(q, top_k=limit, filters=_FILTER)
            if isinstance(results, dict):
                results = results.get("results", [])
            if results:
                _print_hits(results)
                return
        except Exception as e:
            print(f"（索引检索失败，降级为账本检索：{e}）")
    hits = _keyword_hits(query, limit)
    if not hits:
        print("无匹配记忆")
        return
    _print_hits(hits)


def list_all():
    entries = _ledger_read()
    if not entries:
        print("暂无记忆")
        return
    print(f"共 {len(entries)} 条记忆（账本）:\n")
    for i, e in enumerate(entries):
        print(f"{i+1}. [{e.get('ts', '')[:10]}] {e.get('text', '')}")


def rebuild():
    entries = _ledger_read()
    if not entries:
        print("账本为空，无需重建")
        return
    _check_deps()
    m = _get_memory()
    try:
        m.delete_all(user_id=USER_ID)
    except Exception as e:
        print(f"（清空旧索引失败，将直接追加：{e}）")
    for e in entries:
        m.add(e.get("text", ""), user_id=USER_ID)
    print(f"已从账本重建索引，共 {len(entries)} 条")


def export():
    _check_deps()
    m = _get_memory()
    results = m.get_all(filters=_FILTER, top_k=1000)
    if isinstance(results, dict):
        results = results.get("results", [])
    seen = {e.get("text", "") for e in _ledger_read()}
    n = 0
    for r in results:
        text = r.get("memory", "") if isinstance(r, dict) else str(r)
        if text and text not in seen:
            _ledger_append(text)
            seen.add(text)
            n += 1
    print(f"已导出 {n} 条到账本（账本共 {len(seen)} 条）")


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
    elif cmd == "export":
        export()
    elif cmd == "rebuild":
        rebuild()
    elif cmd == "reset":
        reset()
    else:
        print(f"未知命令: {cmd}")
        print(__doc__)
        sys.exit(1)
