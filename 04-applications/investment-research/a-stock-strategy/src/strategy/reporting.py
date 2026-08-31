"""Stable, local report serialization for backtest results."""
from __future__ import annotations

import base64
import csv
import json
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .backtest import BacktestResult
from .evaluation import Metrics
from .llm import BacktestReport, detached, get_llm_provider


@dataclass(frozen=True)
class ReportPaths:
    trades: Path
    equity: Path
    summary: Path
    report: Path

    @property
    def trades_csv(self) -> Path: return self.trades
    @property
    def equity_csv(self) -> Path: return self.equity
    @property
    def summary_json(self) -> Path: return self.summary
    @property
    def report_png(self) -> Path: return self.report

    def __iter__(self):
        return iter((self.trades, self.equity, self.summary, self.report))


def _jsonable(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if is_dataclass(value):
        return {k: _jsonable(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def write_report(result: BacktestResult, metrics: Metrics, output_dir: str | Path,
                 metadata: dict[str, Any] | None = None, *, llm_provider: Any | None = None,
                 recommendation: Any | None = None) -> ReportPaths:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    trades_path, equity_path, summary_path, report_path = (out / n for n in ("trades.csv", "equity.csv", "summary.json", "report.png"))

    trade_fields = ["signal_date", "entry_date", "exit_date", "symbol", "quantity", "entry_price", "exit_price", "fees", "pnl", "exit_reason"]
    with trades_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=trade_fields)
        writer.writeheader()
        for trade in result.trades:
            writer.writerow({field: _jsonable(getattr(trade, field)) for field in trade_fields})

    equity_fields = ["date", "cash", "position_value", "equity", "drawdown"]
    with equity_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=equity_fields)
        writer.writeheader()
        for point in result.equity:
            writer.writerow({field: _jsonable(getattr(point, field)) for field in equity_fields})

    provider = get_llm_provider() if llm_provider is None else llm_provider
    provider_enabled = bool(getattr(provider, "enabled", llm_provider is not None))
    llm_meta = {"enabled": provider_enabled,
                "status": "enabled" if provider_enabled else "disabled",
                "provider": getattr(provider, "name", provider.__class__.__name__),
                "prompt_summary": "explain deterministic results without changing them",
                "generated_at": datetime.now(timezone.utc).isoformat()}
    if getattr(provider, "model", None):
        llm_meta["model"] = provider.model
    llm_errors: list[str] = []
    # LLM is an optional explanation boundary: network/provider failures are
    # metadata warnings and never interrupt deterministic artifact creation.
    if recommendation is not None and provider_enabled:
        try:
            explanation = provider.explain_recommendation(detached(recommendation))
            if explanation:
                llm_meta["recommendation"] = str(explanation)
        except Exception as exc:
            llm_errors.append(f"llm recommendation unavailable: {exc}")
    if provider_enabled:
        try:
            detached_report = detached(BacktestReport(list(result.trades), list(result.equity), metrics, list(result.warnings)))
            summary_text = provider.summarize_backtest(detached_report)
            if summary_text:
                llm_meta["summary"] = str(summary_text)
        except Exception as exc:
            llm_errors.append(f"llm summary unavailable: {exc}")
    if llm_errors:
        llm_meta["status"] = "error"
        llm_meta["error"] = "; ".join(llm_errors)
    meta = dict(metadata or {})
    # Provider state and generated explanations are authoritative; callers
    # cannot make an enabled provider appear disabled through metadata.
    meta["llm"] = llm_meta
    dates = [p.date for p in result.equity]
    meta.setdefault("data_range", {"start": min(dates).isoformat(), "end": max(dates).isoformat()} if dates else {"start": None, "end": None})
    meta.setdefault("source", meta.get("data_source", "unknown"))
    meta.setdefault("data_source", meta["source"])
    meta.setdefault("adjustment", meta.get("adjustment_basis", "unknown"))
    meta.setdefault("costs", {})
    meta.setdefault("generated_at", datetime.now(timezone.utc).isoformat())
    meta.setdefault("range", meta["data_range"])
    chart_warning = _write_chart(result, report_path)
    report_warnings = list(result.warnings) + ([chart_warning] if chart_warning else []) + llm_errors
    caller_warnings = list(meta.get("warnings", []))
    report_warnings = caller_warnings + [warning for warning in report_warnings if warning not in caller_warnings]
    meta["warnings"] = report_warnings
    summary = {"metadata": _jsonable(meta), "metrics": _jsonable(metrics), "warnings": report_warnings,
               # Keep the key metadata visible to simple consumers as well as
               # under the namespaced metadata object.
               "data_source": meta["data_source"], "data_range": _jsonable(meta["data_range"]),
               "adjustment": meta["adjustment"], "adjustment_basis": meta["adjustment"],
               "costs": _jsonable(meta["costs"]), "generated_at": meta["generated_at"]}
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return ReportPaths(trades_path, equity_path, summary_path, report_path)


def _write_chart(result: BacktestResult, path: Path) -> str | None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(3, 1, figsize=(9, 8), sharex=False)
        days = [point.date for point in result.equity]
        axes[0].plot(days, [point.equity for point in result.equity], color="#2563eb")
        axes[0].set_ylabel("Equity")
        axes[1].fill_between(days, [point.drawdown for point in result.equity], 0, color="#dc2626", alpha=.3)
        axes[1].set_ylabel("Drawdown")
        years = {}
        for point in result.equity:
            years.setdefault(point.date.year, []).append(point.equity)
        if len(years) > 1:
            labels = sorted(years)
            returns = [values[-1] / values[0] - 1 if values[0] else 0 for values in (years[y] for y in labels)]
            axes[2].bar([str(y) for y in labels], returns, color="#16a34a")
            axes[2].set_ylabel("Yearly return")
        else:
            axes[2].set_visible(False)
        axes[0].grid(alpha=.2); axes[1].grid(alpha=.2)
        fig.tight_layout(); fig.savefig(path, dpi=120); plt.close(fig)
        return None
    except Exception:
        # Keep the artifact contract but make the missing optional dependency
        # explicit to callers and in summary metadata.
        path.write_bytes(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="))
        return "report chart unavailable: matplotlib is not installed"
