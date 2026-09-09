"""任务与策略共享的有限数值校验。"""
import math


def numeric(value, name, minimum, maximum, integer=False):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not minimum <= value <= maximum or (integer and int(value)!=value):
        raise ValueError(f'{name}: expected {"integer" if integer else "number"} in [{minimum}, {maximum}]')
    return int(value) if integer else float(value)

