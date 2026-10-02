# 2026-10-02 VPS 与网站重建上下文恢复

## 本轮范围

用户希望从服务器初始化开始重新搭建个人代理，并把工作区中的部分网站部署到该服务器。本轮完成历史资料检索与迁移范围初步盘点，尚未确定使用旧 VPS 或新 VPS，未连接服务器、重装系统、安装服务、发布网站或修改 DNS。

工作区执行 `git pull --ff-only`，返回 `Already up to date.`。工作区原有其它项目的未提交改动不属于本轮。

## 旧 VPS 资料

事实来源：

- `01-infrastructure/vpn-relay/ColoCrossing翻墙节点部署手册.html`
- `01-infrastructure/vps-quick-access/VPS快速访问手册.html`
- `01-infrastructure/vpn-relay/VPN中转站完整部署手册.html`

历史文档记录 ColoCrossing 洛杉矶套餐：1 vCPU、1GB RAM、30GB SSD、40TB 月流量、1Gbps 带宽，历史价格为 $10.99/年。该价格、续费情况和实际资源未在本轮向商家核实。

旧部署使用 3X-UI 管理 VLESS + Reality / Vision 节点。快速访问手册保存了具体 IP、面板地址和订阅路径，本记录不重复这些连接细节或凭据。旧端口记录为：SSH 22、节点 TCP 443、面板 18080、订阅 18081、证书 HTTP 验证 80。

系统选择建议曾写为 Debian 12 或 Ubuntu 22.04；没有证据确认旧服务器当前实际系统。服务器在线状态、登录权限、当前入站配置和需要保留的数据均尚待核对。

旧资料中的差异需要在重建时处理：

1. ColoCrossing 手册部分段落使用默认面板端口 2053，实际快速访问记录使用 18080，HTTP/HTTPS 说明也前后不一致。
2. ColoCrossing 手册使用 Reality 目标 `www.microsoft.com`；另一份手册记录过握手故障，改用 `dl.google.com`，并要求核对 Min Client Ver、SNI、Short ID 和 Spider X。旧故障记录不能替代对新版本和客户端的核验。
3. 旧代理节点占用 TCP 443，网站 HTTPS 入口需要先规划共存方式。

## 网站与应用盘点

| 对象 | 本轮证据 | 迁移前需要处理 |
| --- | --- | --- |
| Agent 工程笔记 | 独立仓库位于工作区旁的 `agent-engineering-notes`；README、package.json、Vite 配置显示 React/Vinext 和 Cloudflare Worker 构建 | 核对生产运行方式、构建产物、域名切换与回滚 |
| 金融学习站 | `04-applications/investment-research/finance-ironmao/` 存在独立仓库；有 Vinext/Worker 配置，`next.config.ts` 仍有 `output: 'export'` | 统一构建模式并验证 VPS 生产部署；不能直接把现有启动命令当成生产方案 |
| 论文精读页面 | `03-research/paper-deep-dive/index.html` 与配套内容存在 | 检查内容路径、依赖资源以及拟公开的文件范围 |
| A 股研究工作台 | `a-stock-strategy/README.md` 记载服务监听 `127.0.0.1:8765`，任务使用 SQLite 和独立状态目录 | 远程身份认证、HTTPS、数据与任务状态持久化、行情源连通性、资源容量 |
| Mira 服务、GridBot、Agent Evidence Lab | 工作区存在项目；GridBot 已有 Dockerfile/Compose | 用户确认部署范围后逐项目盘点，避免将所有项目自动加入首轮迁移 |

2026-10-02 已有金融站恢复记录说明：当时 Agent 工程笔记通过 Sites 部署且 HTTPS 返回 200，金融站部署失败且未绑定目标域名。以上为该记录的历史观察，本轮没有重新验证现网状态。

现有本机 SSH 配置的 `ironmao` 别名指向 `ssh.ironmao.win` 并配置了 ProxyCommand；MacBook 服务器手册也记录该域名。不能据此将该别名认定为 ColoCrossing VPS 的直接 SSH 入口。

## 后续指导顺序

1. 确定服务器：沿用旧 VPS、购买新 VPS，或先比较方案；核实套餐、系统、访问权限和保留数据。
2. 初始化：备份需保留的数据，再处理重装、系统更新、管理用户、SSH 密钥与防火墙；确认新的 SSH 会话能登录后再收紧登录方式。
3. 恢复代理：确定与网站的端口分配，安装服务，生成新凭据，逐个验证实际客户端。
4. 网站迁移：先验证一个最小网站，再逐站迁移；为后台应用设置认证，构建和运行各项目的正式产物。
5. 运维：落实重启恢复、证书续期、日志、异机备份与恢复验证；最后逐个切换域名并保留回滚路径。

备选部署路径待用户讨论：一台服务器承载代理和网站；两台服务器分别承载代理与网站；先用旧 VPS 恢复代理和小型页面，再根据后端负载决定扩容或迁移。尚未形成已批准设计。

参考官方资料：

- [Caddy 反向代理与 HTTPS](https://caddyserver.com/docs/quick-starts/reverse-proxy)：域名入口通常使用 80/443，可统一代理后端 HTTP 服务。
- [3X-UI 安装说明](https://github.com/MHSanaei/3x-ui/wiki/Installation)：实施前以当前官方版本为准核对安装步骤。
- [Docker 防火墙说明](https://docs.docker.com/engine/network/packet-filtering-firewalls/)：容器发布端口与主机防火墙的交互需要按实际部署核验。

## 记忆同步

按工作区 SOP 执行两次 Mem0 查询及一次回写，均在配置初始化时因缺少 `DEEPSEEK_API_KEY` 失败。没有修改凭据配置或安装额外依赖。本文件作为本次可同步的恢复记录。
