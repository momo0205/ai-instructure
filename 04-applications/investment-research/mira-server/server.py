"""
Mira API 服务端
监听 localhost:8080
支持: Flutter App (REST 报告浏览器) + PWA (即席查询)
"""

import os
import json
import logging
import uuid
from datetime import datetime, date
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response
from pydantic import BaseModel
from openai import OpenAI

from data_fetcher import fetch_stock_data, tencent_quote

# ── 日志 ──
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mira-server")

# ── FastAPI ──
app = FastAPI(title="Mira API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── 持久化 ──
BASE_DIR = Path(__file__).parent
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)
REPORTS_INDEX = REPORTS_DIR / "index.json"


def _load_index() -> dict:
    """加载报告索引。结构: {service_id: [Report, ...]}"""
    if REPORTS_INDEX.exists():
        return json.loads(REPORTS_INDEX.read_text())
    return {}


def _save_index(index: dict):
    REPORTS_INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2))


def _save_report(service_id: str, report: dict, content: str):
    """保存报告内容和索引"""
    index = _load_index()
    svc_reports = index.get(service_id, [])
    # 避免重复
    svc_reports = [r for r in svc_reports if r["id"] != report["id"]]
    svc_reports.insert(0, report)
    index[service_id] = svc_reports[:50]  # 最多保留 50 条
    _save_index(index)
    # 保存 Markdown
    (REPORTS_DIR / f"{report['id']}.md").write_text(content)


# ── 预定义服务列表 ──

SERVICES = [
    {
        "id": "research",
        "name": "Mira 投研",
        "description": "A股个股深度研究，含实时行情、财务数据、AI 分析",
        "report_count": 0,
    },
    {
        "id": "briefing",
        "name": "市场简报",
        "description": "每日市场快照，核心指数、关键变动、driver map",
        "report_count": 0,
    },
    {
        "id": "industry",
        "name": "行业分析",
        "description": "行业/产业链分析，公司映射、阶段判断",
        "report_count": 0,
    },
]


def _update_service_counts():
    """同步报告数量到服务列表"""
    index = _load_index()
    for svc in SERVICES:
        svc["report_count"] = len(index.get(svc["id"], []))


def _service_reports(service_id: str) -> list[dict]:
    """返回某服务的报告列表"""
    index = _load_index()
    return index.get(service_id, [])


def _report_content(service_id: str, report_id: str) -> Optional[str]:
    """读取报告 Markdown 内容"""
    path = REPORTS_DIR / f"{report_id}.md"
    if path.exists():
        return path.read_text()
    return None


def _extract_summary(md: str, max_len: int = 120) -> str:
    """从 Markdown 提取摘要（取第一个有意义段落）"""
    for line in md.split("\n"):
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and len(stripped) > 10:
            return stripped[:max_len] + ("..." if len(stripped) > max_len else "")
    return md[:max_len]


def _generate_report_id(ticker: str = "", prefix: str = "report") -> str:
    """生成唯一报告 ID"""
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    short = uuid.uuid4().hex[:6]
    if ticker:
        return f"{ticker}-{ts}-{short}"
    return f"{prefix}-{ts}-{short}"


# ── DeepSeek 客户端 ──
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY")
if not DEEPSEEK_KEY:
    log.warning("DEEPSEEK_API_KEY not set — AI analysis disabled")
    deepseek = None
else:
    deepseek = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")


MIRA_SYSTEM_PROMPT = """你是 Mira 投研系统的 AI 引擎。你以严谨的研究操作员身份工作。

## 核心规则
1. 输出分三层：**事实**（数据可验证）、**推断**（基于事实的逻辑推理）、**判断**（含主观置信度）
2. 每条事实必须标注数据来源
3. 输出末尾必须包含 `stale_after`（何时过期）和 `must_refresh_if`（什么事件触发刷新）
4. 永远使用 Markdown 格式输出

## 研究深度
- quick_map：核心判断 + 来源标注 + 关键缺口 + 刷新条件
- standard：完整研究包（投资备忘录 + 证据日志 + 预期映射）
- deep_dive：在 standard 基础上加更完整证据路径

## 输出结构（quick_map）
```markdown
# {股票名称}（{代码}）Quick Map
**行情快照**：...
## 核心判断
## 事实 vs 推断
## 数据来源
## Source Gap（关键信息缺口）
## 估值快照
## 关键反转条件
## 下一步
```

## 输出结构（standard）
在 quick_map 基础上增加：分业务线分析、盈利预测敏感性、完整 evidence log 表格。

## 重要约束
- 你输出的是研究辅助，不是投资建议
- 对不确定的事情明确标注 `uncertain`
- 中文回复
"""

# ═══════════════════════════════════════════════
# Flutter REST API（报告浏览器）
# ═══════════════════════════════════════════════

@app.get("/api/services")
async def api_services():
    """返回服务列表"""
    _update_service_counts()
    return SERVICES


@app.get("/api/services/{service_id}/reports")
async def api_reports(service_id: str):
    """返回某服务的报告列表"""
    if service_id not in [s["id"] for s in SERVICES]:
        raise HTTPException(404, f"Unknown service: {service_id}")
    return _service_reports(service_id)


@app.get("/api/services/{service_id}/reports/{report_id}")
async def api_report_content(service_id: str, report_id: str):
    """返回报告 Markdown 内容"""
    if service_id not in [s["id"] for s in SERVICES]:
        raise HTTPException(404, f"Unknown service: {service_id}")
    content = _report_content(service_id, report_id)
    if content is None:
        raise HTTPException(404, f"Report not found: {report_id}")
    return Response(content=content, media_type="text/plain; charset=utf-8")


# ═══════════════════════════════════════════════
# PWA 即席查询 API（触发研究 + 返回 Markdown）
# ═══════════════════════════════════════════════

@app.get("/health")
async def health():
    return {"status": "ok", "deepseek": DEEPSEEK_KEY is not None}


class ResearchRequest(BaseModel):
    ticker: str = "600519"
    depth: str = "standard"
    market: str = "A 股"


class BriefingRequest(BaseModel):
    market: str = "沪深两市"


class IndustryRequest(BaseModel):
    concept: str = "人工智能"
    market: str = "A 股"


class TriggerRequest(BaseModel):
    """触发新研究并保存报告"""
    ticker: str = "600519"
    market: str = "A 股"


@app.post("/research")
async def research(req: ResearchRequest):
    """个股研究（PWA 即席查询，同时保存为报告）"""
    log.info(f"/research ticker={req.ticker} depth={req.depth}")
    stock_data = fetch_stock_data(req.ticker)
    if stock_data.get("error") and not stock_data.get("quote"):
        raise HTTPException(500, f"数据获取失败: {stock_data['error']}")
    if deepseek:
        markdown = await _ai_analyze("research", req, stock_data)
    else:
        markdown = _format_data_only("research", req, stock_data)

    # 保存为报告（给 Flutter 看）
    quote = stock_data.get("quote", {})
    name = quote.get("name", req.ticker)
    report_id = _generate_report_id(req.ticker)
    _save_report("research", {
        "id": report_id,
        "title": f"{name}({req.ticker})",
        "date": date.today().isoformat(),
        "tags": ["A股", req.depth],
        "summary": _extract_summary(markdown),
    }, markdown)
    return {"markdown": markdown, "report_id": report_id}


@app.post("/briefing")
async def briefing(req: BriefingRequest):
    """市场简报"""
    log.info(f"/briefing market={req.market}")
    index_codes = ["000001", "000300", "399006"]
    try:
        index_data = tencent_quote(index_codes)
    except Exception as e:
        index_data = {"error": str(e)}
    if deepseek:
        markdown = await _ai_analyze("briefing", req, index_data)
    else:
        markdown = _format_data_only("briefing", req, index_data)

    # 保存报告
    report_id = _generate_report_id(prefix="briefing")
    _save_report("briefing", {
        "id": report_id,
        "title": f"市场简报 - {date.today().isoformat()}",
        "date": date.today().isoformat(),
        "tags": ["市场", req.market],
        "summary": _extract_summary(markdown),
    }, markdown)
    return {"markdown": markdown, "report_id": report_id}


@app.post("/industry")
async def industry(req: IndustryRequest):
    """行业分析"""
    log.info(f"/industry concept={req.concept}")
    if deepseek:
        markdown = await _ai_analyze("industry", req, None)
    else:
        markdown = f"# {req.concept} 行业分析\n\n> DeepSeek API 未配置。\n\n**stale_after**: -\n**must_refresh_if**: -"

    report_id = _generate_report_id(prefix=req.concept[:6])
    _save_report("industry", {
        "id": report_id,
        "title": f"{req.concept} - {date.today().isoformat()}",
        "date": date.today().isoformat(),
        "tags": ["行业", req.concept, req.market],
        "summary": _extract_summary(markdown),
    }, markdown)
    return {"markdown": markdown, "report_id": report_id}


# ═══════════════════════════════════════════════
# 触发新研究（给 Flutter 或 cron 用）
# ═══════════════════════════════════════════════

class TriggerResearchRequest(BaseModel):
    service: str = "research"  # research / briefing / industry
    ticker: str = "600519"
    market: str = "A 股"
    depth: str = "standard"
    concept: str = ""


@app.post("/api/trigger")
async def api_trigger(req: TriggerResearchRequest):
    """触发新研究并返回 report_id（用于 cron / 手动触发）"""
    if req.service == "research":
        r = ResearchRequest(ticker=req.ticker, depth=req.depth, market=req.market)
        result = await research(r)
    elif req.service == "briefing":
        r = BriefingRequest(market=req.market)
        result = await briefing(r)
    elif req.service == "industry":
        r = IndustryRequest(concept=req.concept or "人工智能", market=req.market)
        result = await industry(r)
    else:
        raise HTTPException(400, f"Unknown service: {req.service}")
    return {"report_id": result["report_id"], "status": "ok"}
# ── 请求模型 ──

class ResearchRequest(BaseModel):
    ticker: str = "600519"
    depth: str = "standard"          # quick_map / standard / deep_dive
    market: str = "A 股"

class BriefingRequest(BaseModel):
    market: str = "沪深两市"

class IndustryRequest(BaseModel):
    concept: str = "人工智能"
    market: str = "A 股"


# ── 端点 ──

@app.get("/health")
async def health():
    return {"status": "ok", "deepseek": DEEPSEEK_KEY is not None}


@app.post("/research")
async def research(req: ResearchRequest):
    """
    个股研究端点。获取实时数据 + AI 分析。
    """
    log.info(f"/research ticker={req.ticker} depth={req.depth} market={req.market}")

    # 1. 获取实时数据
    stock_data = fetch_stock_data(req.ticker)
    if stock_data.get("error") and not stock_data.get("quote"):
        raise HTTPException(500, f"数据获取失败: {stock_data['error']}")

    # 2. 如果 DeepSeek 可用，调 AI 分析
    if deepseek:
        markdown = await _ai_analyze("research", req, stock_data)
    else:
        markdown = _format_data_only("research", req, stock_data)

    return {"markdown": markdown}


@app.post("/briefing")
async def briefing(req: BriefingRequest):
    """
    市场简报端点。
    """
    log.info(f"/briefing market={req.market}")

    # 获取核心指数数据
    index_codes = ["000001", "000300", "399006"]  # 上证、沪深300、创业板
    try:
        index_data = tencent_quote(index_codes)
    except Exception as e:
        index_data = {"error": str(e)}

    if deepseek:
        markdown = await _ai_analyze("briefing", req, index_data)
    else:
        markdown = _format_data_only("briefing", req, index_data)

    return {"markdown": markdown}


@app.post("/industry")
async def industry(req: IndustryRequest):
    """
    行业/概念分析端点。
    """
    log.info(f"/industry concept={req.concept} market={req.market}")

    if deepseek:
        markdown = await _ai_analyze("industry", req, None)
    else:
        markdown = f"# {req.concept} 行业分析\n\n> DeepSeek API 未配置，无法生成 AI 分析。请设置 DEEPSEEK_API_KEY。\n\n**stale_after**: 数据更新后\n**must_refresh_if**: -"

    return {"markdown": markdown}


# ── AI 分析核心 ──

async def _ai_analyze(task_type: str, req, data) -> str:
    """调用 DeepSeek API 执行 Mira 协议分析"""
    if task_type == "research":
        user_prompt = _build_research_prompt(req, data)
    elif task_type == "briefing":
        user_prompt = _build_briefing_prompt(req, data)
    elif task_type == "industry":
        user_prompt = _build_industry_prompt(req, data)
    else:
        user_prompt = ""

    try:
        resp = deepseek.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": MIRA_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=4096,
        )
        return resp.choices[0].message.content
    except Exception as e:
        log.error(f"DeepSeek API error: {e}")
        return f"# AI 分析失败\n\n错误: {e}\n\n**原始数据**:\n```json\n{json.dumps(data, ensure_ascii=False, indent=2, default=str)[:3000]}\n```\n\n**stale_after**: 重试后\n**must_refresh_if**: API 恢复"


def _build_research_prompt(req: ResearchRequest, data: dict) -> str:
    """构建个股研究 prompt"""
    quote = data.get("quote", {})
    info = data.get("info", {})
    income = data.get("income_statement", [])

    return f"""研究任务: 个股研究
股票代码: {req.ticker}
股票名称: {quote.get('name', info.get('name', '未知'))}
市场范围: {req.market}
输出深度: {req.depth}

## 实时行情数据
- 当前价: {quote.get('price', 'N/A')} 元
- 涨跌幅: {quote.get('change_pct', 'N/A')}%
- PE(TTM): {quote.get('pe_ttm', 'N/A')}
- PB: {quote.get('pb', 'N/A')}
- 总市值: {quote.get('mcap_yi', 'N/A')} 亿
- 流通市值: {quote.get('float_mcap_yi', 'N/A')} 亿
- 成交额: {quote.get('amount_wan', 'N/A')} 万
- 换手率: {quote.get('turnover_pct', 'N/A')}%
- 今开: {quote.get('open', 'N/A')}
- 最高: {quote.get('high', 'N/A')}
- 最低: {quote.get('low', 'N/A')}

## 基本面信息
- 行业: {info.get('industry', '未知')}
- 总股本: {info.get('total_shares', 'N/A')} 股
- 流通股: {info.get('float_shares', 'N/A')} 股

## 最近利润表
```json
{json.dumps(income, ensure_ascii=False, indent=2, default=str)}
```

数据来源: 腾讯财经(行情) + 东财push2(基本面) + 新浪财经(财报)

请按 Mira {req.depth} 深度输出研究分析。"""


def _build_briefing_prompt(req: BriefingRequest, data: dict) -> str:
    """构建市场简报 prompt"""
    return f"""研究任务: 市场简报
市场范围: {req.market}

## 核心指数实时数据
```json
{json.dumps(data, ensure_ascii=False, indent=2, default=str)}
```

数据来源: 腾讯财经 HTTP

请输出一份 standard 深度的市场简报，包含: 市场快照、关键变动、driver map、事件日历、source notes 和 research escalation queue。
"""


def _build_industry_prompt(req: IndustryRequest, data=None) -> str:
    """构建行业分析 prompt"""
    return f"""研究任务: 行业/概念分析
概念/行业: {req.concept}
市场范围: {req.market}

请按 Mira standard 深度输出行业分析，包含:
1. 产业链地图
2. 关键公司映射
3. 当前阶段判断（渗透率/竞争格局/政策）
4. 估值锚点
5. 股票研究 handoff 列表

数据来源: 公开信息检索
"""


def _format_data_only(task_type: str, req, data) -> str:
    """当 DeepSeek 不可用时的纯数据输出"""
    return f"""# {req.ticker if hasattr(req, 'ticker') else req.market} - 数据快照

> ⚠️ DeepSeek API 未配置，仅输出原始数据。

```json
{json.dumps(data, ensure_ascii=False, indent=2, default=str)[:5000]}
```

**stale_after**: 数据更新后
**must_refresh_if**: -
"""


# ── 启动 ──
if __name__ == "__main__":
    import uvicorn
    log.info("Starting Mira API server on :8080")
    uvicorn.run(app, host="0.0.0.0", port=8080)