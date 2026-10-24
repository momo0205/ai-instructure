# mira-server — Mira HTTP API

给 Flutter 客户端和 PWA 用的后端：报告浏览、即席查询、AI 分析。

## 跑起来

```bash
cd 04-applications/investment-research/mira-server
export DEEPSEEK_API_KEY=sk-...     # 或写在仓库根 .env
./start.sh
```

服务监听 `localhost:8080`，默认只对本机开放。

## 结构

```
mira-server/
├── server.py        # FastAPI 应用与路由
├── data_fetcher.py  # 行情抓取（腾讯/东财等）
├── reports/         # 生成的报告与索引
├── requirements.txt
└── start.sh         # 装依赖 + 启动
```

## 接口

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/reports` | 报告列表 |
| GET | `/reports/{id}` | 报告详情 |
| POST | `/query` | 即席查询（走 LLM） |

## 注意

- 没有 `DEEPSEEK_API_KEY` 时服务能起，但 AI 分析接口会失败。
- `reports/` 里是生成物，体积会涨；清理由 `mira-automation/scripts/auto_cleaner.py` 负责。
- 只用 Python 标准库 + FastAPI，没有数据库；数据都在 `reports/` 目录里。
