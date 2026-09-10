"""旧配置模块的兼容导入，新实现归应用层。"""
import sys
from strategy.application import configuration
sys.modules[__name__] = configuration
