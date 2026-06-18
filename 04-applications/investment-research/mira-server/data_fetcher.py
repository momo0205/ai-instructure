"""
a-stock-data 核心数据获取函数
从 a-stock-data/SKILL.md V3.2.2 提取，用于 Mira API 服务端
"""

import time
import random
import urllib.request
import requests
from pathlib import Path
from typing import Optional, Union

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# ── 东财限流封装（来自 SKILL.md） ──

_EM_SESSION = None
_EM_LAST_CALL = 0.0
_EM_MIN_INTERVAL = 1.0  # 秒


def _em_get_session():
    global _EM_SESSION
    if _EM_SESSION is None:
        _EM_SESSION = requests.Session()
        _EM_SESSION.headers.update({
            "User-Agent": UA,
            "Referer": "https://data.eastmoney.com/",
        })
    return _EM_SESSION


def em_get(url: str, params: Optional[dict] = None, headers: Optional[dict] = None,
           timeout: int = 10) -> requests.Response:
    """
    东财统一 GET 入口，内置串行限流（≥1s + 随机抖动）。
    """
    global _EM_LAST_CALL
    elapsed = time.time() - _EM_LAST_CALL
    if elapsed < _EM_MIN_INTERVAL:
        time.sleep(_EM_MIN_INTERVAL - elapsed + random.uniform(0, 0.5))
    s = _em_get_session()
    merged_headers = {}
    if headers:
        merged_headers.update(headers)
    r = s.get(url, params=params, headers=merged_headers, timeout=timeout)
    _EM_LAST_CALL = time.time()
    return r


# ── 股票代码前缀 ──

def get_prefix(code: str) -> str:
    """返回 'sh' / 'sz' / 'bj'"""
    if code.startswith(("6", "9")):
        return "sh"
    elif code.startswith("8"):
        return "bj"
    else:
        return "sz"


# ── 腾讯财经行情（PE/PB/市值/价格） ──

def tencent_quote(codes: list[str]) -> dict[str, dict]:
    """
    批量拉取腾讯财经实时行情。不封 IP。
    codes: 如 ["600519", "000001"]
    返回: {code: {name, price, pe_ttm, pb, mcap_yi, ...}}
    """
    prefixed = []
    for c in codes:
        pfx = get_prefix(c)
        prefixed.append(f"{pfx}{c}")

    url = "https://qt.gtimg.cn/q=" + ",".join(prefixed)
    req = urllib.request.Request(url)
    req.add_header("User-Agent", UA)
    resp = urllib.request.urlopen(req, timeout=10)
    data = resp.read().decode("gbk")

    result = {}
    for line in data.strip().split(";"):
        if not line.strip() or "=" not in line or '"' not in line:
            continue
        key = line.split("=")[0].split("_")[-1]
        vals = line.split('"')[1].split("~")
        if len(vals) < 53:
            continue
        code = key[2:]
        result[code] = {
            "name": vals[1],
            "price": float(vals[3]) if vals[3] else 0,
            "last_close": float(vals[4]) if vals[4] else 0,
            "open": float(vals[5]) if vals[5] else 0,
            "change_amt": float(vals[31]) if vals[31] else 0,
            "change_pct": float(vals[32]) if vals[32] else 0,
            "high": float(vals[33]) if vals[33] else 0,
            "low": float(vals[34]) if vals[34] else 0,
            "amount_wan": float(vals[37]) if vals[37] else 0,
            "turnover_pct": float(vals[38]) if vals[38] else 0,
            "pe_ttm": float(vals[39]) if vals[39] else 0,
            "amplitude_pct": float(vals[43]) if vals[43] else 0,
            "mcap_yi": float(vals[44]) if vals[44] else 0,
            "float_mcap_yi": float(vals[45]) if vals[45] else 0,
            "pb": float(vals[46]) if vals[46] else 0,
            "limit_up": float(vals[47]) if vals[47] else 0,
            "limit_down": float(vals[48]) if vals[48] else 0,
            "vol_ratio": float(vals[49]) if vals[49] else 0,
            "pe_static": float(vals[52]) if vals[52] else 0,
        }
    return result


# ── 东财个股基本面 ──

def eastmoney_stock_info(code: str) -> dict:
    """东财个股基本面信息（行业/总股本/流通股/市值/上市日期）"""
    market_code = 1 if code.startswith("6") else 0
    url = "https://push2.eastmoney.com/api/qt/stock/get"
    params = {
        "fltt": "2", "invt": "2",
        "fields": "f57,f58,f84,f85,f127,f116,f117,f189,f43",
        "secid": f"{market_code}.{code}",
    }
    r = em_get(url, params=params, timeout=10)
    d = r.json().get("data", {})
    return {
        "code": d.get("f57", ""),
        "name": d.get("f58", ""),
        "industry": d.get("f127", ""),
        "total_shares": d.get("f84", 0),
        "float_shares": d.get("f85", 0),
        "mcap": d.get("f116", 0),
        "float_mcap": d.get("f117", 0),
        "list_date": str(d.get("f189", "")),
        "price": d.get("f43", 0),
    }


# ── 新浪财报三表 ──

def sina_financial_report(code: str, report_type: str = "lrb", num: int = 8) -> list[dict]:
    """
    新浪财报三表。
    report_type: "fzb"(资产负债表) / "lrb"(利润表) / "llb"(现金流量表)
    num: 取最近 N 期
    """
    prefix = get_prefix(code)
    paper_code = f"{prefix}{code}"
    url = "https://quotes.sina.cn/cn/api/openapi.php/CompanyFinanceService.getFinanceReport2022"
    params = {
        "paperCode": paper_code,
        "source": report_type,
        "type": "0",
        "page": "1",
        "num": str(num),
    }
    r = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=15)
    report_list = r.json().get("result", {}).get("data", {}).get("report_list", {}) or {}

    rows = []
    for period in sorted(report_list.keys(), reverse=True)[:num]:
        obj = report_list[period]
        rec = {"报告期": f"{period[:4]}-{period[4:6]}-{period[6:8]}"}
        for it in obj.get("data", []) or []:
            title = it.get("item_title", "")
            if not title or it.get("item_value") is None:
                continue
            rec[title] = it.get("item_value", "")
            if it.get("item_tongbi"):
                rec[f"{title}_同比"] = it.get("item_tongbi")
        rows.append(rec)
    return rows


# ── 综合数据获取（给 API 用） ──

def fetch_stock_data(code: str) -> dict:
    """
    获取一只 A 股的核心数据，整合腾讯行情 + 东财基本面 + 新浪利润表。
    返回 dict，可直接序列化为 JSON。
    """
    result = {"code": code, "error": None}

    # 腾讯行情
    try:
        quote = tencent_quote([code])
        if code in quote:
            result["quote"] = quote[code]
        else:
            result["error"] = f"腾讯行情未返回 {code}"
    except Exception as e:
        result["error"] = f"腾讯行情: {e}"

    # 东财基本面
    try:
        info = eastmoney_stock_info(code)
        if info.get("name"):
            result["info"] = info
    except Exception:
        pass  # 非关键

    # 新浪利润表（最近 4 期）
    try:
        lrb = sina_financial_report(code, "lrb", 4)
        if lrb:
            result["income_statement"] = lrb
    except Exception:
        pass  # 非关键

    return result