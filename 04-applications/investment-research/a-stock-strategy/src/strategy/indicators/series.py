"""Pure daily series calculations. Rows are already aligned to one calendar."""
import math
from numbers import Real


def _valid(value, *, zero=False):
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    try:
        number = float(value)
    except (OverflowError, ValueError):
        return None
    return number if math.isfinite(number) and (number >= 0 if zero else number > 0) else None


def _result(keys, values=None, available=0, reason=''):
    return dict(values=dict(zip(keys, values if values is not None else [None] * len(keys))),
                available=available, reason=reason)


def calculate_series(rows: list[dict], instances: list[dict]) -> dict[str, list[dict]]:
    """One value per input calendar position, including missing rows."""
    output = {}
    for instance in instances:
        kind = instance['id']
        window = instance['parameters']['window']
        field = 'volume' if kind == 'volume_sma' else 'close'
        values = [_valid(row.get(field), zero=field == 'volume') for row in rows]
        keys = ('middle','upper','lower') if kind == 'bollinger' else ('value',)
        produced = []
        streak = 0
        ema = None
        alpha = 2 / (window + 1)
        for position, value in enumerate(values):
            streak = streak + 1 if value is not None else 0
            available = min(streak, window)
            if value is None:
                ema = None
                produced.append(_result(keys, available=0, reason='invalid_'+field))
                continue
            if streak < window and (kind != 'ema' or ema is None):
                produced.append(_result(keys, available=available, reason='insufficient_history'))
                continue
            if kind == 'ema':
                if ema is None:
                    ema = math.fsum(item / window for item in values[position-window+1:position+1])
                else:
                    ema = alpha * value + (1 - alpha) * ema
                computed = (ema,)
            else:
                sample = values[position-window+1:position+1]
                mean = math.fsum(item / window for item in sample)
                if kind == 'bollinger':
                    deviation = math.hypot(*(item-mean for item in sample)) / math.sqrt(window)
                    offset = instance['parameters']['multiplier'] * deviation
                    computed = (mean, mean+offset, mean-offset)
                else:
                    computed = (mean,)
            if all(math.isfinite(item) for item in computed):
                produced.append(_result(keys, computed, available=available))
            else:
                produced.append(_result(keys, available=available, reason='nonfinite_result'))
        output[instance['instance_id']] = produced
    return output
