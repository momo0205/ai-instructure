# 数据源与开源项目核验（2026-09-05 至 2026-09-06）

## 现有代码评估

原项目已有离线CSV、固定标的、横截面特征排名、下一交易日开盘撮合、成本、指标、报告和可选LLM解释。基线70项测试通过，但测试固定了错误需求：把“4000家下跌”解释为“指数点位≥4000”，且只要求指数收益<0，没有 -1% 阈值。

旧 CLI 也未串起固定/动态的基准对比；旧百度 `000001` 缓存是十几元股票价格，并非上证指数。仅跑通旧测试或旧报告不能证明该策略有效。

本次改为单独市场广度输入与统一信号函数；新版配置明确 ≥4000家及≤-1%，对比报告记录触发、成本、输入哈希、数据缺失和成交时点。旧配置保留为兼容实验，并在 CLI 中提示其不是目标策略。

## 免费数据源

| 项目 | 可用性与权限 | 用于本任务的结论 |
|---|---|---|
| [AKShare](https://akshare.akfamily.xyz/data/stock/stock.html) | 开源、无需统一Token；具体接口取决于上游网站 | 股票/ETF/指数行情可作候选来源；不能因包免费就保证接口稳定 |
| [乐咕涨跌家数实现](https://raw.githubusercontent.com/akfamily/akshare/main/akshare/stock_feature/stock_market_legu.py) | `stock_market_activity_legu` 只抓当前页面，无历史日期参数；文档口径为沪深 | 不能把当前快照作为历史广度；本次乐咕返回403/错误页 |
| [Tushare权限表](https://tushare.pro/document/1?doc_id=290) | 120积分、0元/年档：50次/分钟、8000次/日，仅非复权股票日线 | 推荐按日期抓 `daily` 合成历史广度；需个人Token和实际账号权限验证 |
| [Tushare daily](https://tushare.pro/document/2?doc_id=27) | 全市场股票日线、单次最多6000条；停牌期间不提供记录 | 使用供应商pct_chg而非未复权相邻收盘比；分页、日期、重复、交易所覆盖必须核验 |
| [Tushare ETF daily](https://tushare.pro/document/2?doc_id=127) | 当前文档要求5000积分 | 不把股票免费日线权限误说成免费ETF权限 |
| [BaoStock官方包](https://pypi.org/project/baostock/) | 免费，示例无凭据登录，历史日线含pctChg和交易状态 | 未核验北交所和退市历史完整性，暂不作为沪深北广度保证 |
| [mootdx](https://raw.githubusercontent.com/mootdx/mootdx/master/mootdx/quotes.py) | 通达信在线接口，无Token，股票列表仅沪深；bar分页 | 没有免费服务稳定性承诺，不能直接宣称覆盖沪深北 |

通达信实测4台7709服务器，1台连接成功、3台超时。连通节点对本次指数协议请求仅返回2字节状态数据，未获得有效K线。官方 [pytdx指数响应解析](https://raw.githubusercontent.com/rainx/pytdx/master/pytdx/parser/get_index_bars.py) 虽有 up_count/down_count 字段，但本次没有成功获得可以验证口径的历史广度。

因此本次只能交付下载/导入能力及演示报告，不能输出可信真实历史胜率或收益。Tushare下载器的自动测试使用模拟API响应；未持有用户Token进行真实下载。即使API返回成功，也需核对北交所、退市证券、空交易日和覆盖数量。

## 开源框架能否直接用

| 框架 | 适用方向 | 是否能直接解决此需求 |
|---|---|---|
| [RQAlpha](https://github.com/ricequant/rqalpha) | A股、多资产事件回测 | 可扩展，但仍需自行接历史广度与编写触发/选股策略 |
| [Backtrader](https://github.com/mementum/backtrader) | 多数据源、自带CSV策略回测 | 可用，A股交易规则与市场广度需要自定义 |
| [VeighNa](https://github.com/vnpy/vnpy) | 交易系统、组合策略与接口 | 后续实盘平台可评估；当前固定日频策略引入成本偏高 |

当前建议沿用已有轻量框架，先解决信号和数据正确性。替换框架并不能补上历史广度，也不能自动回答策略是否有效。

## ETF执行口径

上交所说明股票ETF为T+1，最低交易单位100份：[ETF常见问题](https://www.sse.com.cn/assortment/fund/etf/question/)。ETF二级市场不征印花税的说明可见 [上证50ETF交易问答](https://www.sse.com.cn/assortment/fund/etf/home/c/c_20151111_4011009.shtml)。本MVP配置印花税为0，佣金和滑点仍需按实际调整。

全天市场广度在收盘后才确定，所以当前实现 D 收盘确认、D+1 开盘买、D+2 开盘卖。它是可复现的日线近似实验；验证 D 日尾盘买入需要另备分钟级历史信号。
