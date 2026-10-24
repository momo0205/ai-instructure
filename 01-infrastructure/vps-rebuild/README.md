# VPS 重建与网站部署

从重装系统到代理可用、站点上线的完整链路，含可复现的探测脚本与页面自检。

## 文件

| 路径 | 内容 |
|---|---|
| `VPS重建与网站部署一步步教程.html` | 主教程：重装 → SSH → Caddy → 站点 |
| `FlClash与VPS代理部署实测教程.html` | sing-box / Mihomo 订阅与分流实测 |
| `VPS日常登录与维护手册.html` | 日常运维、证书续期、故障处理 |
| `lab/flclash_probe.py` | 订阅解析与路由探测脚本 |
| `lab/test_flclash_probe.py` | 上面脚本的单元测试 |
| `lab/results-2026-10-09.json` | 一次实测的原始结果 |
| `tests/guide.test.cjs` | 教程 HTML 里的命令/配置自检（node:test） |
| `后续工作清单-2026-10-13.md` | 当时未完成事项 |

## 怎么跑

```bash
# 页面自检（需要 Node 18+）
node --test 01-infrastructure/vps-rebuild/tests/guide.test.cjs

# 探测脚本测试
cd 01-infrastructure/vps-rebuild/lab
python3 -m pytest test_flclash_probe.py -q
```

## 注意

- 教程含真实 IP / 域名 / 证书路径，仓库保持私有。
- `lab/` 只是实验台，不是生产代码；跑之前先看 `results-*.json` 里的对照数据。
