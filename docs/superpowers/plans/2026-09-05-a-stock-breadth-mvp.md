# A 股市场广度策略最小版本 Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development for independent reporting and review work; use test-driven-development for each code change.

**Goal:** 修复用户明确的“下跌家数 >=4000 且指数跌幅 >=1%”策略，交付离线回测、候选 ETF 对比及可审计数据入口。

**Architecture:** 保留 Python/CSV 引擎，增加独立每日 breadth CSV，在指数行按日期连接；统一信号函数供回测及推荐使用。严禁将候选池下跌数当全市场广度；缺数据失败或明确跳过，禁止填未来数据。保留显式旧指数点位模式仅用于旧 API 兼容，默认配置使用 breadth 模式。

**Tech Stack:** 现有 Python、pandas、pytest、matplotlib；静态 HTML 报告无服务依赖。

## 决策与验收

- 本次用户需求纠正 2026-08-28 spec 的误解：4000 是股票数量，非指数点位。默认市场代理为上证综指，可配置。
- 暂用既有日线成交时序：D 收盘信号，D+1 开盘买，D+2 开盘卖（持有一个交易日）；不声称等同 D 尾盘策略。用户时点澄清异步进行。
- 默认ETF配置零印花税、100份交易单位、佣金及滑点可配置，报告明确假设。
- 动态选择第一版复用候选 ETF 反转/动量评分，不声称已有行业级下跌分布选股。
- 本仓库是主仓库跟踪目录，并非独立 git；保留无关改动，在 codex/a-stock-breadth-mvp 分支限定路径提交。

## 验收记录（2026-09-06）

- 既有基线70项通过；新增广度、整手成本、数据入口、缺失/陈旧行情、样例身份与比较测试后，全量114项通过。
- `compare --config configs/mvp.toml --output reports/mvp` 已生成HTML、两套报告及逐日触发审计；两种策略各5笔合成示例交易。
- `recommend --config configs/mvp.toml --as-of 2024-02-06` 返回正确固定ETF信号。
- 独立审查发现并修复：广度来源绕过、缺ETF仍报零收益、陈旧ETF导致无效基准；覆盖不足暂停超额收益计算。
- 真实历史广度未取得（缺用户Token；免Token端点实测失败），正确指数/ETF数据组合也未核验。真实历史收益验证仍未完成，已提供下载/CSV入口与真实数据模板。
- Mem0缺DEEPSEEK_API_KEY；以本文件和项目文档保存任务记录。主仓库无法快进拉取，保持独立开发分支，不自动合并main。

### Task 1: 修正市场信号（root）

Files: `src/strategy/{signals,domain,config,backtest,recommendation,cli}.py`, `tests/test_breadth.py`。

- [ ] 先写测试：指数3300点、下跌4000家、指数跌1%必须触发；3999家或跌0.9%不触发；缺失/过期广度不触发；推荐与回测一致。
- [ ] 跑 `.venv/bin/python -m pytest -q tests/test_breadth.py` 观察 RED。
- [ ] 实现 `market_state(frame, day, index_symbol, trigger_level, threshold, min_declining_count=None)`；新增 MarketState.declining_count、回测事件记录；数据入口按日期联结广度。
- [ ] 运行重点测试及现有70项回归测试。

### Task 2: 数据入口（root + independent research）

Files: `src/strategy/breadth.py`, 数据导入测试、示例 CSV、配置。

- [ ] 验证 breadth CSV `date,declining_count,total_count,source`：唯一日期、整数计数、0<=declining<=total；保留来源。
- [ ] 提供原始全市场日线 `trade_date,ts_code,pct_chg` 聚合入口，拒绝重复代码、不明代码和不完整声明；公开数据源权限与免费局限。
- [ ] 实测可用无token历史接口；若受阻，保留可导入真实CSV/用户token入口，清楚区分样例与真实回测。

### Task 3: 对比交付（reporting agent）

Files: 新增 `src/strategy/comparison.py`, `tests/test_comparison.py`。

- [ ] 先写集成测试对比固定ETF、动态候选池，并验证相同数据和成本、每个策略报告、comparison.csv/json、index.html。
- [ ] 实现独立 `compare(config, data, output_dir)`，报告展示样例标识、实际区间、触发数、费用、成交时序、逐笔交易及数据缺口。
- [ ] root 接入 `compare --config ... --output ...`；端到端生成可查看报告。

### Task 4: 验收与文档

- [ ] 更新 README，记录旧实现偏差、数据源和开源项目调查、复制即用命令。
- [ ] 全量 pytest；固定及动态端到端；独立代码审查并修复。
- [ ] 生成最终 artifacts，只提交本任务文件，回写本地任务记录；Mem0缺Key记明，主仓库分叉不自动合并或推送main。
