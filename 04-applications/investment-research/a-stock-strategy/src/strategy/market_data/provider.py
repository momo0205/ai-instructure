"""行情提供方边界；任务队列和数据集发布不依赖具体供应商。"""
from pathlib import Path
import hashlib
import json
import re
from typing import Protocol
from urllib.request import Request, urlopen

from strategy.market_data.catalog import VERIFIED_ETFS, validate_symbol
from strategy.market_data.tencent import download_market


class MarketDataProvider(Protocol):
    """下载需在 output_dir 写入 market.csv 和 market_manifest.json。

    清单声明真实来源、复权方式和内容哈希；raw_dir 如存在须位于下载目录。
    发布仓库负责验证日期覆盖和清单，提供方不得修改基线数据。
    """

    def resolve(self, symbol: str) -> dict:
        ...

    def download(self, start: str, end: str, output_dir: Path,
                 symbols=None, adjustment='none'):
        ...


class TencentMarketDataProvider:
    """保留现有腾讯报价解析和日线下载格式；opener 可替换以离线验证。"""

    def __init__(self, opener=None):
        self._opener = opener or urlopen

    def resolve(self, symbol: str) -> dict:
        validate_symbol(symbol)
        key = symbol[-2:].lower()+symbol[:6]
        request = Request('https://qt.gtimg.cn/q='+key, headers={'User-Agent': 'Mozilla/5.0'})
        with self._opener(request, timeout=15) as response:
            raw = response.read().decode('gbk')
        match = re.search(r'v_'+key+r'="([^"]+)"', raw)
        fields = match.group(1).split('~') if match else []
        if len(fields) < 4 or fields[2] != symbol[:6] or not fields[1].strip():
            raise ValueError('数据源未确认该证券代码，请检查代码或稍后重试')
        kind = 'etf' if symbol in VERIFIED_ETFS or 'ETF' in fields[1].upper() else 'stock' if symbol[0] in '036' else 'unknown'
        return dict(symbol=symbol, name=fields[1].strip(), kind=kind)

    def download(self, start, end, output_dir, symbols=None, adjustment='none'):
        return download_market(start, end, output_dir, symbols=symbols, adjustment=adjustment)


class CallableMarketDataProvider:
    """兼容 DownloadManager 原有 downloader/resolver 函数注入约定。"""

    def __init__(self, downloader, resolver):
        self._downloader = downloader
        self._resolver = resolver

    def resolve(self, symbol: str) -> dict:
        return self._resolver(symbol)

    def download(self, start, end, output_dir, symbols=None, adjustment='none'):
        result = self._downloader(start, end, output_dir, symbols=symbols, adjustment=adjustment)
        # 旧函数未要求完整清单：仅在兼容适配器补本地证据，并明确记录复权假设。
        # 新提供方直接遵守严格合同；仓库不对未知来源猜测复权。
        output = Path(output_dir)
        path = output/'market_manifest.json'
        if path.is_file() and (output/'market.csv').is_file():
            manifest = json.loads(path.read_text())
            if 'adjustment' not in manifest:
                manifest['adjustment'] = adjustment
                manifest.setdefault('warnings', []).append('旧下载函数未声明复权；按调用参数假设，未经供应商清单验证。')
            manifest.setdefault('source', 'legacy-callable')
            manifest.setdefault('market_sha256', hashlib.sha256((output/'market.csv').read_bytes()).hexdigest())
            if manifest.get('raw_dir') and 'raw_sha256' not in manifest:
                raw = Path(manifest['raw_dir']).resolve()
                if not raw.is_dir() or not raw.is_relative_to(output.resolve()):
                    raise ValueError('原始响应目录必须位于本次下载目录内')
                manifest['raw_sha256'] = {str(p.relative_to(raw)): hashlib.sha256(p.read_bytes()).hexdigest()
                                          for p in raw.rglob('*') if p.is_file() and p.resolve().is_relative_to(raw)}
            path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
        return result
