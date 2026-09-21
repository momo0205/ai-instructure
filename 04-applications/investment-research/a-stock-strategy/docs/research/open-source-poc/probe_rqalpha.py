"""Check the default engine startup without downloading an external market bundle."""
import json
from pathlib import Path
import rqalpha
from rqalpha import run_func

root = Path(__file__).parent / "rqalpha-output"
root.mkdir(exist_ok=True)
def init(context):
    context.symbol = "588000.XSHG"

def handle_bar(context, bars):
    # Reaching the handler would prove the default data path is usable.
    context.seen_bar = True

try:
    result = run_func(init=init, handle_bar=handle_bar, config={
        "base": {"start_date": "2024-01-02", "end_date": "2024-01-31",
                 "accounts": {"stock": 100000}, "frequency": "1d",
                 "data_bundle_path": str(root / "missing-bundle"), "rqdatac_uri": "disabled"},
        "extra": {"log_level": "error"},
        "mod": {"sys_analyser": {"enabled": True, "plot": False}},
    })
    outcome = {"version": rqalpha.__version__, "result_available": result is not None,
               "note": "This probe intentionally supplies no external bundle or custom data source."}
except Exception as exc:
    outcome = {"version": rqalpha.__version__, "result_available": False,
               "exception_type": type(exc).__name__, "message": str(exc)}
(root / "result.json").write_text(json.dumps(outcome, indent=2))
print(json.dumps(outcome, indent=2))
