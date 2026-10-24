# GridBot — 加密货币网格交易机器人

Python + FastAPI + CCXT + APScheduler，支持 OKX，带 Docker 部署与风险限额。

> 状态：**暂停**。代码完整但未在实盘长期运行，交易相关改动请先在 OKX 模拟盘验证。

## 结构

```
gridbot/
├── main.py            # 入口：调度器 + FastAPI
├── api/               # HTTP 接口
├── core/              # 网格逻辑与风控
├── ai/                # 策略/参数辅助
├── config/            # 配置加载
├── data/              # 本地数据
├── tests/             # pytest
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## 怎么跑（本地）

```bash
cd 04-applications/gridbot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp gridbot/.env.example .env      # 填 OKX_API_KEY / OKX_SECRET / OKX_PASSWORD
python main.py
```

## 怎么跑（Docker）

```bash
cd 04-applications/gridbot
docker compose up -d
```

## 测试

```bash
cd 04-applications/gridbot
python -m pytest tests -q
```

## 注意

- `.env` 不入库；`OKX_SANDBOX=true` 时走模拟盘。
- `MAX_INVESTMENT_PER_GRID_USDT` 等风控参数在 `.env` 里，默认值偏保守。
- 交易代码没有 CI 覆盖，改动后请务必补测试。
