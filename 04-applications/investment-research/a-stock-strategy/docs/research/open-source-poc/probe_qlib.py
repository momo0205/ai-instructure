"""Isolated Qlib interface probe; no production configuration is changed."""
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import qlib
from qlib.data import D
from qlib.workflow import R
from qlib.contrib.evaluate import backtest_daily
from qlib.contrib.strategy.signal_strategy import TopkDropoutStrategy

source = Path(sys.argv[1]).resolve()
root = Path(__file__).parent / "qlib-output"
provider = root / "provider"
frame = pd.read_csv(source)
assert not frame.duplicated(["date", "symbol"]).any()
dates = sorted(frame.date.unique())
for directory in ("calendars", "instruments", "features"):
    (provider / directory).mkdir(parents=True, exist_ok=True)
(provider / "calendars/day.txt").write_text("\n".join(dates) + "\n")
instruments = []
for symbol, rows in frame.groupby("symbol"):
    code, exchange = symbol.split(".")
    instrument = exchange.lower() + code
    rows = rows.set_index("date").reindex(dates)
    instruments.append(f"{instrument.upper()}\t{dates[0]}\t{dates[-1]}")
    directory = provider / "features" / instrument
    directory.mkdir(exist_ok=True)
    for field in ("open", "high", "low", "close", "volume"):
        # Qlib binary starts with the calendar offset, followed by float32 values.
        np.r_[0, rows[field].values].astype("<f4").tofile(directory / f"{field}.day.bin")
    # Existing prices are qfq. 1 is a probe placeholder, not verified corporate actions.
    np.r_[0, np.ones(len(dates))].astype("<f4").tofile(directory / "factor.day.bin")
(provider / "instruments/all.txt").write_text("\n".join(instruments) + "\n")
qlib.init(provider_uri=str(provider), region="cn", kernels=1,
          exp_manager={"class": "MLflowExpManager", "module_path": "qlib.workflow.expm",
                       "kwargs": {"uri": f"sqlite:///{root / 'experiments.db'}", "default_exp_name": "compatibility"}})
features = D.features(["SH588000", "SH510300", "SZ159915"],
                      ["$close", "$close/Ref($close, 20)-1"], dates[0], dates[-1])
assert len(features) == 3 * len(dates)
# Verify an actual derived value against pandas, independently of Qlib storage.
expected = frame[frame.symbol == "588000.SH"].sort_values("date").close.pct_change(20).iloc[-1]
actual = features.loc[("SH588000", pd.Timestamp(dates[-1]))].iloc[1]
assert np.isclose(actual, expected, atol=1e-6), (actual, expected)
# Built-in rotation consumes the prior session's score; trading uses next open.
# This probes interoperability, not equivalence with our breadth strategy.
signal = features.iloc[:, 1].dropna().swaplevel().sort_index()
report, positions = backtest_daily(
    start_time="2024-03-01", end_time="2025-12-30",
    strategy=TopkDropoutStrategy(signal=signal, topk=1, n_drop=1),
    account=100000, benchmark="SH510300",
    exchange_kwargs={"deal_price": "open", "open_cost": 0.0003,
                     "close_cost": 0.0003, "min_cost": 5, "limit_threshold": 0.2},
)
assert len(report) > 400 and report["account"].notna().all()
assert report["turnover"].sum() > 0
report.to_csv(root / "backtest.csv")
with R.start(experiment_name="existing_csv_probe"):
    R.log_params(source=str(source), universe_size=3, factor="20-session momentum")
    R.log_metrics(feature_rows=len(features), sessions=len(dates))
    R.save_objects(**{"features.pkl": features})
    R.save_objects(**{"backtest.pkl": report})
    R.log_metrics(backtest_sessions=len(report), final_account=float(report.account.iloc[-1]))
    recorder_id = R.get_recorder().id
recorder = R.get_recorder(recorder_id=recorder_id, experiment_name="existing_csv_probe")
pd.testing.assert_frame_equal(recorder.load_object("features.pkl"), features)
result = {"qlib_version": qlib.__version__, "sessions": len(dates), "feature_rows": len(features),
          "recorder_id": recorder_id, "metrics": recorder.list_metrics(),
          "data_and_factor_verified": True, "artifact_roundtrip_verified": True,
          "builtin_backtest_verified": True,
          "limitations": ["No model training or engine equivalence checked", "qfq factor placeholder; volume units unverified"]}
(root / "result.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
