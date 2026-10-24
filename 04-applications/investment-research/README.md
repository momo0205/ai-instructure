# 投研系列（Mira）

围绕 Mira 投研协议的一组项目：协议、数据、回测、服务端、客户端。**这里只是同一产品线的集合目录**，各子项目有自己的入口。

## 一张表看懂

| 目录 | 是什么 | 入口 | 归属 |
|---|---|---|---|
| `Mira/` | 投研协议（上游） | `START_HERE.md` | 子模块：`byteseek/Mira` |
| `a-stock-data/` | A 股数据工具包（上游） | `README.md` | 子模块：`simonlin1212/a-stock-data` |
| `a-stock-strategy/` | 日线策略回测 + 浏览器工作台 | `MVP.md` | 本仓库跟踪 |
| `mira-server/` | 给客户端用的 HTTP API | `start.sh` | 本仓库跟踪 |
| `mira-automation/` | 写在 Mira 里的自有脚本备份 | `README.md` | 本仓库跟踪 |
| `finance-ironmao/` | 财务指标学习站 | `README.md` | **独立仓库**，父仓 gitignore |

## 依赖关系

```
a-stock-data ──数据──> a-stock-strategy
Mira（协议） ──案例──> mira-server ──HTTP──> mira-flutter / mira-pwa
finance-ironmao    独立部署（Cloudflare Worker）
```

## 常见动作

```bash
# 回测 + 工作台
cd a-stock-strategy && uv sync && .venv/bin/python -m strategy serve   # http://127.0.0.1:8765

# 服务端
cd mira-server && ./start.sh                                           # http://localhost:8080

# 独立仓库要单独 clone
git clone git@github.com:momo0205/finance-ironmao.git
```

## 注意

- `Mira` 是**别人的上游仓库**，不要在里面积累自有代码——放 `mira-automation/` 或 fork。
- `finance-ironmao` 不在父仓里，`git clone` 父仓不会带上它。
- 行情/实验数据可重新生成，已在 `.gitignore` 排除。
