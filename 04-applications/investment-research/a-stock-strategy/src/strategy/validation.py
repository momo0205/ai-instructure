"""任务与策略共享的有限数值校验。"""
import math


def numeric(value, name, minimum, maximum, integer=False):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not minimum <= value <= maximum or (integer and int(value)!=value):
        raise UserError('INVALID_REQUEST', f'参数 {name} 应为范围内的有限数值；{name}: expected {"integer" if integer else "number"} in [{minimum}, {maximum}]')
    return int(value) if integer else float(value)



class UserError(ValueError):
    """仅用于已审定可公开的业务说明；原始第三方异常不可直接包装为此类型。"""
    def __init__(self, code, message, *, context=None):
        super().__init__(message)
        self.code, self.context = code, context or {}
