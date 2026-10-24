#!/usr/bin/env python3
"""MiraRunner — Mira 投研协议自动化执行引擎

用法：
    from mira_runner import MiraRunner
    runner = MiraRunner()
    result = runner.run("600519", depth="standard")
    # result 包含 memo, evidence_log, case_notes, routing, manifest

依赖：requests + DeepSeek API key（环境变量 DEEPSEEK_API_KEY）
"""

import json
import os
import re
import time
from datetime import date
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── 配置 ──────────────────────────────────────────────
MIRA_ROOT = Path(__file__).resolve().parent.parent
CASES_DIR = MIRA_ROOT / "cases"
PROTOCOL_DIR = MIRA_ROOT
DATA_SKILL_PATH = MIRA_ROOT.parent / "a-stock-data" / "SKILL.md"
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = "deepseek-chat"  # 或 deepseek-reasoner

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


# ── 数据拉取 ──────────────────────────────────────────
def _get_prefix(code: str) -> str:
    if code.startswith(("6", "9")):
        return "sh"
    return "sz"


def _fetch_tencent(code: str) -> dict:
    """腾讯财经实时行情。"""
    import urllib.request
    url = f"https://qt.gtimg.cn/q={_get_prefix(code)}{code}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = resp.read().decode("gbk")
    for line in data.strip().split(";"):
        if "=" not in line or '"' not in line:
            continue
        vals = line.split('"')[1].split("~")
        if len(vals) < 53:
            continue
        return {
            "name": vals[1],
            "price": float(vals[3]) if vals[3] else 0,
            "pe_ttm": float(vals[39]) if vals[39] else 0,
            "pb": float(vals[46]) if vals[46] else 0,
            "mcap_yi": float(vals[44]) if vals[44] else 0,
            "turnover_pct": float(vals[38]) if vals[38] else 0,
            "change_pct": float(vals[32]) if vals[32] else 0,
        }
    return {}


def _fetch_ths_consensus(code: str) -> dict:
    """同花顺一致预期。"""
    import urllib.request
    url = f"https://basic.10jqka.com.cn/new/{code}/worth.html"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://basic.10jqka.com.cn/"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read().decode("gbk")

    # 提取 EPS 预测
    eps_match = re.search(r'预测每股收益.*?(\[\[.*?\]\])', raw, re.DOTALL)
    np_match = re.search(r'预测净利润.*?(\[\[.*?\]\])', raw, re.DOTALL)
    rev_match = re.search(r'营业总收入.*?(\[\[.*?\]\])', raw, re.DOTALL)

    result = {"eps_history": [], "np_history": [], "rev_history": [], "forecast_count": 0}

    if eps_match:
        items = json.loads(f"[{eps_match.group(1)}]")
        result["eps_history"] = items
        for item in items:
            if len(item) >= 4 and item[3] == "YC":
                result["forecast_count"] = max(result["forecast_count"], 1)

    if np_match:
        result["np_history"] = json.loads(f"[{np_match.group(1)}]")

    if rev_match:
        result["rev_history"] = json.loads(f"[{rev_match.group(1)}]")

    return result


def _fetch_sina_financials(code: str) -> dict:
    """新浪三表（最近 3 期）。"""
    import urllib.request

    results = {}
    prefix = _get_prefix(code)
    paper_code = f"{prefix}{code}"

    for report_type, label in [("lrb", "利润表"), ("fzb", "资产负债表"), ("llb", "现金流量表")]:
        url = "https://quotes.sina.cn/cn/api/openapi.php/CompanyFinanceService.getFinanceReport2022"
        params = f"paperCode={paper_code}&source={report_type}&type=0&page=1&num=3"
        full_url = f"{url}?{params}"
        req = urllib.request.Request(full_url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
            rl = raw.get("result", {}).get("data", {}).get("report_list", {}) or {}
            items = {}
            for period in sorted(rl.keys(), reverse=True)[:3]:
                obj = rl[period]
                date_str = f"{period[:4]}-{period[4:6]}-{period[6:8]}"
                period_items = {}
                for it in obj.get("data", []) or []:
                    title = it.get("item_title", "")
                    value = it.get("item_value")
                    if title and value:
                        period_items[title] = value
                items[date_str] = period_items
            results[label] = items
        except Exception as e:
            results[label] = {"error": str(e)}

    return results


def _fetch_margin(code: str) -> dict:
    """东财融资融券。"""
    import urllib.request
    url = (
        "https://datacenter-web.eastmoney.com/api/data/v1/get"
        f"?reportName=RPTA_WEB_RZRQ_GGMX&columns=ALL"
        f"&filter=(SCODE%3D%22{code}%22)&pageNumber=1&pageSize=3"
        "&sortColumns=DATE&sortTypes=-1&source=WEB&client=WEB"
    )
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://data.eastmoney.com/"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = json.loads(resp.read().decode("utf-8"))
    data = raw.get("result", {}).get("data", [])
    if not data:
        return {}
    latest = data[0]
    return {
        "rzye": latest.get("RZYE", 0),       # 融资余额
        "rzmre": latest.get("RZMRE", 0),      # 融资买入额
        "rqye": latest.get("RQYE", 0),        # 融券余额
        "date": str(latest.get("DATE", ""))[:10],
    }


def pull_all_data(code: str) -> dict:
    """并行拉取所有 HTTP 数据源。"""
    results = {}
    fetchers = {
        "tencent": lambda: _fetch_tencent(code),
        "ths_consensus": lambda: _fetch_ths_consensus(code),
        "sina_financials": lambda: _fetch_sina_financials(code),
        "margin": lambda: _fetch_margin(code),
    }

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fn): name for name, fn in fetchers.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as e:
                results[name] = {"error": str(e)}

    return results


# ── 协议加载 ──────────────────────────────────────────
def load_protocol() -> str:
    """加载 Mira 核心协议文件，返回拼接后的 prompt 系统指令。"""
    files = [
        "MIRA.md",
        "OPERATING_CONTRACT.md",
        "loops/research-loop.md",
        "data/claim-taxonomy.md",
        "data/evidence-posture-taxonomy.md",
        "data/output-surface-matrix.md",
        "data/controlled-vocabulary.md",
    ]
    parts = []
    for f in files:
        path = PROTOCOL_DIR / f
        if path.exists():
            content = path.read_text()
            # 只取前 2000 字 + 关键表格，避免 prompt 过长
            if len(content) > 3000:
                content = content[:2000] + "\n... (truncated)\n"
            parts.append(f"## {f}\n\n{content}")
    return "\n\n".join(parts)


# ── Prompt 拼装 ───────────────────────────────────────
def build_prompt(code: str, data: dict, depth: str = "standard") -> str:
    """拼装完整的研究 prompt。"""
    name = data.get("tencent", {}).get("name", code)

    prompt = f"""你是 Mira 投研协议执行引擎。

## 任务
对 A 股 {code}（{name}）执行首次研究，深度={depth}。

## 协议
{load_protocol()}

## 数据
{json.dumps(data, ensure_ascii=False, indent=2, default=str)[:15000]}

## 输出要求
请输出以下内容，用明确的标记分隔：

### MEMO
完整的 investment-memo.md 内容（Markdown 格式），包含：
- 元数据字段（market/date/depth/task_mode 等）
- Decision Header 表格
- Core Conclusion
- Bull Case / Bear Case
- Key Debate
- Valuation And Expectation Quant（含数值表格）
- Technical Market Pricing Context
- Actionability Bridge
- Evidence Quality
- Major Risks
- Tracking Metrics
- Must Refresh If

### EVIDENCE_LOG
CSV 格式的 evidence-log.csv，表头为:
source_id,claim_area,claim_type,claim_text,source_speaker,verification_status,authority_level,source_date,as_of_date,url_or_path,used_by_agent,used_by_skill,confidence,upstream_sources,notes,evidence_category,freshness_status,conflict_status,treatment,readiness_impact,source_language,translation_basis

### CASE_NOTES
case-notes.md 内容（Markdown 格式）

### ROUTING
routing.json 内容（JSON 格式）

### MANIFEST
research-package-manifest.json 内容（JSON 格式）

请严格按照 Mira 协议的受控词汇表填写所有枚举字段。
"""
    return prompt


# ── DeepSeek 调用 ─────────────────────────────────────
def call_deepseek(prompt: str, depth: str = "standard") -> str:
    """调用 DeepSeek API，返回完整响应文本。"""
    import requests

    if not API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY 环境变量未设置")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    system_prompt = "你是一个严谨的投资研究 AI。严格遵循 Mira 投研协议的受控词汇表。事实/推断/判断必须分离。所有枚举字段使用协议定义的 token。"

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 8192,
    }

    resp = requests.post(API_URL, headers=headers, json=payload, timeout=180)
    resp.raise_for_status()
    result = resp.json()
    return result["choices"][0]["message"]["content"]


# ── 结果解析 ──────────────────────────────────────────
def parse_response(response: str) -> dict:
    """从 AI 响应中提取各部分的文件内容。"""
    sections = {
        "memo": "",
        "evidence_log": "",
        "case_notes": "",
        "routing": "",
        "manifest": "",
    }

    current_section = None
    current_content = []

    for line in response.split("\n"):
        if "### MEMO" in line:
            if current_section:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = "memo"
            current_content = []
        elif "### EVIDENCE_LOG" in line:
            if current_section:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = "evidence_log"
            current_content = []
        elif "### CASE_NOTES" in line:
            if current_section:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = "case_notes"
            current_content = []
        elif "### ROUTING" in line:
            if current_section:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = "routing"
            current_content = []
        elif "### MANIFEST" in line:
            if current_section:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = "manifest"
            current_content = []
        elif current_section:
            current_content.append(line)

    if current_section:
        sections[current_section] = "\n".join(current_content).strip()

    # 清理 Markdown 代码块标记
    for key in ["evidence_log", "routing", "manifest"]:
        content = sections[key]
        content = re.sub(r'^```\w*\n?', '', content)
        content = re.sub(r'\n?```$', '', content)
        sections[key] = content.strip()

    return sections


# ── 文件写入 ──────────────────────────────────────────
def save_research(code: str, sections: dict, date_str: str | None = None) -> Path:
    """将研究结果写入 cases/ 目录。"""
    if date_str is None:
        date_str = date.today().strftime("%Y-%m")

    case_dir = CASES_DIR / f"{code}-{date_str}"
    case_dir.mkdir(parents=True, exist_ok=True)

    file_map = {
        "investment-memo.md": sections.get("memo", ""),
        "evidence-log.csv": sections.get("evidence_log", ""),
        "case-notes.md": sections.get("case_notes", ""),
        "routing.json": sections.get("routing", ""),
        "research-package-manifest.json": sections.get("manifest", ""),
    }

    for filename, content in file_map.items():
        if content:
            (case_dir / filename).write_text(content)

    return case_dir


# ── 自检 ──────────────────────────────────────────────
def validate_case(case_dir: Path) -> tuple[bool, str]:
    """运行 validate_repo.py 自检。"""
    import subprocess
    result = subprocess.run(
        ["python3", str(PROTOCOL_DIR / "scripts" / "validate_repo.py"), str(case_dir)],
        capture_output=True, text=True, timeout=30,
        cwd=str(PROTOCOL_DIR),
    )
    return result.returncode == 0, result.stdout


# ── 主入口 ────────────────────────────────────────────
class MiraRunner:
    def __init__(self, max_retries: int = 2):
        self.max_retries = max_retries

    def run(self, code: str, depth: str = "standard", date_str: str | None = None) -> dict:
        """执行完整研究流程。"""
        print(f"[MiraRunner] 开始研究 {code}（深度={depth}）")

        # 1. 拉数据
        print("  1/5 拉取数据...")
        data = pull_all_data(code)

        name = data.get("tencent", {}).get("name", code)
        print(f"     {code} {name}")

        # 2. 拼 prompt
        print("  2/5 拼装 prompt...")
        prompt = build_prompt(code, data, depth)
        print(f"     prompt 长度: {len(prompt)} 字符")

        # 3. 调 DeepSeek（含重试）
        for attempt in range(self.max_retries + 1):
            print(f"  3/5 调 DeepSeek API（尝试 {attempt + 1}/{self.max_retries + 1}）...")
            try:
                response = call_deepseek(prompt, depth)
                break
            except Exception as e:
                if attempt == self.max_retries:
                    return {"error": f"DeepSeek API 调用失败: {e}"}
                print(f"     失败: {e}，{5}s 后重试...")
                time.sleep(5)

        # 4. 解析 + 写入
        print("  4/5 解析结果并写入...")
        sections = parse_response(response)
        case_dir = save_research(code, sections, date_str)
        print(f"     写入: {case_dir}")

        # 5. 自检
        print("  5/5 运行自检...")
        ok, msg = validate_case(case_dir)
        if not ok:
            print(f"     ⚠️ 自检未通过:\n{msg[:500]}")

        # 改进：如果自检未通过，将错误反馈给 AI 重新生成
        # 这里先做一轮基础 retry
        if not ok and self.max_retries > 0:
            print("     → 将错误反馈给 AI 重修...")
            fix_prompt = f"以下是 validate_repo.py 的错误报告。请修正所有错误并只输出修正后的部分：\n\n{msg}"
            try:
                fix_response = call_deepseek(fix_prompt, depth)
                fix_sections = parse_response(fix_response)
                for k, v in fix_sections.items():
                    if v:
                        sections[k] = v
                case_dir = save_research(code, sections, date_str)
                ok2, msg2 = validate_case(case_dir)
                ok = ok2
                msg = msg2
            except Exception:
                pass

        print(f"  完成! {'✅ 通过' if ok else '⚠️ 自检未通过'}")
        if not ok:
            print(f"  {msg[:300]}")

        return {
            "case_dir": str(case_dir),
            "validation_passed": ok,
            "validation_output": msg,
            "files": [p.name for p in case_dir.iterdir()],
        }


# ── CLI ────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python mira_runner.py <股票代码> [depth]")
        sys.exit(1)

    code = sys.argv[1]
    depth = sys.argv[2] if len(sys.argv) > 2 else "standard"
    runner = MiraRunner()
    result = runner.run(code, depth)
    print(json.dumps(result, ensure_ascii=False, indent=2))
