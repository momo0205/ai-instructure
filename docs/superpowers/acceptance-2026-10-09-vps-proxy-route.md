# VPS / FlClash 代理路线研究与验收 · 2026-10-09

## 用户目标与范围

用户要求广查信息，先趟出能用的路线，再沉淀成 HTML 手动部署；不要求继续使用 3X-UI，代理优先、网站以后处理。本次没有安装或修改真实 VPS、DNS、现有 FlClash 配置、系统代理或 TUN。源代码审查、隔离实验和教程制作均在该任务授权范围内。

## 现场只读核对

2026-10-09 经已核对主机密钥的 deployer 密钥 SSH，只读核对：Ubuntu 24.04.5 amd64、运行内核 6.8.0-31、NTP 已同步，ssh / x-ui / caddy active，sing-box inactive。监听 TCP 22、80、8443、2096；面板仅 127.0.0.1:18080，Caddy admin 127.0.0.1:2019，TCP 443 当时空闲。Xray 26.9.9 / commit52a412d。2096 当前是通配地址监听，不能称为仅回环。没有读取用户私钥内容、面板数据库或订阅凭据。

## 官方来源与选择

- [Mihomo REALITY 文档](https://wiki.metacubex.one/config/proxies/tls/#reality-opts)明确不保证 Xray 26.7.11+ REALITY 兼容；[issue3193](https://github.com/MetaCubeX/mihomo/issues/3193)讨论 ML-KEM 参数，[issue3241](https://github.com/MetaCubeX/mihomo/issues/3241)是问题报告，均不能代替实测。
- [Xray26.3.27稳定发布](https://github.com/XTLS/Xray-core/releases/tag/v26.3.27)提示 REALITY 非443与部分目标的封锁风险；不据此认定用户的8443已经被封。[26.9.9](https://github.com/XTLS/Xray-core/releases/tag/v26.9.9)及26.9.30为预发布。
- [REALITY 官方说明](https://github.com/XTLS/REALITY)要求目标 TLS1.3 / H2，明确举例 dl.google.com。Google HTTP200/302/404都不能单独证明代理认证；未认证连接回落到目标是正常机制。
- [sing-box1.14.2](https://github.com/SagerNet/sing-box/releases/tag/v1.14.2)采用原生 VLESS Vision REALITY 配置；[固定实现](https://github.com/SagerNet/sing-box/blob/v1.14.2/common/tls/reality_server.go)核对 server_name、min_version、short_id 和 private_key。[官方unit](https://github.com/SagerNet/sing-box/blob/v1.14.2/release/config/sing-box.service)使用 sing-box 用户及 CAP_NET_BIND_SERVICE。
- 当前最新 sing-box 已为1.14.3（2026-10-09发布），FlClash 最新0.8.99（10-03发布）；本轮故意固定已测1.14.2与用户已安装0.8.94，不将“最新”作为兼容性依据。
- FlClash0.8.94[运行配置覆盖](https://github.com/chen08209/FlClash/blob/v0.8.94/lib/common/task.dart)和[文件导入](https://github.com/chen08209/FlClash/blob/v0.8.94/lib/models/profile.dart)说明 app会覆盖混合端口/mode/TUN，文件导入会复制为应用自己的 profile。URL 下载经过正在运行的应用代理，先停止内核或选可用配置再导入。
- [CaddyACME挑战](https://caddyserver.com/docs/automatic-https#http-challenge)、[tlsissuer](https://caddyserver.com/docs/caddyfile/directives/tls)：订阅HTTPS8443可使用TCP80的HTTP-01，禁用TLS-ALPN避免占代理443。公网证书仍需用户正确DNS/防火墙现场验收。

选择：sing-box1.14.2直接服务 TCP443，保留 FlClash0.8.94；完整文件先完成握手/传输验收，随后 Caddy HTTPS8443静态订阅。旧 x-ui8443在新443验收前保留，新成功后停止才交出8443。普通HTTPS网站与原生REALITY不能同时直接监听同一IP的TCP443；暂不引入额外SNI路由，网站阶段另行规划。

## 实验与资产

实际使用 /Applications/FlClash.app/Contents/MacOS/FlClashCore，独立 IPC / home、仅 Mac127.0.0.1混合端口28791–28798。服务端为 Ubuntu24.04 linux/amd64 Docker（Mac为arm64，使用amd64模拟），原生容器TCP443映射 Mac127.0.0.1:32443/32543/32643。全新一次性UUID、REALITY密钥和short ID，未使用用户真实节点凭据。真实外网目标 dl.google.com:443；curl显式通过隔离代理，代理组只有实验节点、MATCH规则、没有DIRECT回退，关闭TUN/DNS/外部控制器/提供商。服务端日志记录认证后的目标 www.gstatic.com / speed.cloudflare.com。

资产 SHA256（官方摘要与下载文件一致）：

| 资产 | SHA256 |
|---|---|
| Xray26.3.27 Xray-linux-64.zip | 23cd9af937744d97776ee35ecad4972cf4b2109d1e0fe6be9930467608f7c8ae |
| Xray26.9.9 Xray-linux-64.zip | 1eb9175d0f0a8f8149c9230a7fc5ae66ce332ed20a53155ce61fe62e3f58b7df |
| sing-box1.14.2 Linux amd64 tar.gz | a684484d7477d1437282ee411f4d131d0340aaad60a7868841ebd5d87dd8a0c6 |
| sing-box_1.14.2_linux_amd64.deb | 3a15ee1ee918cb5297ccf7fb4356b31ba85f8a7c01da122c5b3e3aeda0568001 |

矩阵（同一安装的 FlClash0.8.94 内核、Chrome指纹、VLESS Vision；请求最终HTTPS204）：

| 服务端 | support-x25519mlkem768:false | true |
|---|---|---|
| Xray26.3.27 | curl0 / HTTP204 | curl0 / HTTP204 |
| Xray26.9.9 | curl35 / HTTP000；服务端REALITY认证失败 | curl0 / HTTP204 |
| sing-box1.14.2 | curl0 / HTTP204 | curl0 / HTTP204 |

sing-box默认方案还完成1,048,576字节下载，最终HTTP200；重复请求连续3次HTTP204以及第二次1MiB下载均通过。错误UUID和错误公钥两个负例均curl35/HTTP000；说明当前实验成功没有直接绕过节点。每次独立内核退出0，代理监听关闭。首轮九例与后续修正、原样生成配置的复测数字结果保存在 `01-infrastructure/vps-rebuild/lab/results-2026-10-09.json`，不含凭据。

探针后来补充第一参数curl -q，排除用户curlrc改变验证行为；安全测试先失败1项再通过16项，并重新运行主路线正例。该补充后的结果另行加入数字记录。

## 可声称的范围

已证明固定客户端内核和固定服务端能做REALITY认证、VLESS Vision请求及真实HTTPS内容传输。没有声称实际新VPS节点已部署，没有声称FlClash GUI导入/系统代理/TUN/UDP、用户运营商链路、公网ACME已通过。Loopback容器实验无法覆盖国内网络到VPS的干扰、IP封锁或长期可用性；实际443、出口IP、浏览器体验及续签必须由用户按教程验收。

## 文档、安装与路由验证

- 官方 .deb 的 postinst 只运行 systemd-sysusers 和 daemon-reload，不启用/启动服务；真实包内配置为 root:root0644 的 Shadowsocks8080示例，应先替换再启动。备份放配置目录之外，因为unit的 -C 会加载目录内JSON。
- 普通最小 Ubuntu Docker 镜像没有systemd-sysusers，首次包检查明确失败。随后构建带完整systemd/Python/OpenSSL/CA的Ubuntu24.04 amd64镜像，dpkg安装成功，真实用户/组997被创建；root:sing-box0640配置以 runuser -u sing-box执行check成功，版本输出1.14.2。这不是把容器当作真实systemd启动证据。
- Caddy2.11.4真实生产候选配置validate成功（HTTPS8443、ACME disable_tlsalpn_challenge）。隔离TLS路由实验将发行器替换为内部CA，curl信任该临时CA且不使用-k，精确随机路径HTTP/2 200，Content-Type application/yaml、Cache-Control no-store，下载字节与文件一致；错误路径404。没有执行公网ACME或修改DNS。
- 探针18项安全、分帧、绝对超时、失败生命周期和代理请求测试通过；审查修复curlrc与慢分片延长deadline问题，修复后重新取得204与1MiB200成功。

- HTML 中 real-server-generator / caddy-subscription-generator 的 Python heredoc 原样提取并在 Ubuntu24.04 amd64隔离容器执行。配置目录用户检查成功，服务JSON root:sing-box0640、客户端 deployer0600、订阅与片段root:caddy0640、私有状态root0600；节点生成器重跑拒绝轮换且配置哈希不变，订阅重跑保留令牌且只有一条import。
- 按原样生成的服务端配置，以 sing-box 用户运行实际服务；完整客户端YAML经已安装FlClashCore getConfig / validateConfig解析。只将实验节点地址替换为Mac回环映射地址，真实HTTPS204和1MiB200再次通过。进一步按完整生成配置启动独立内核（仅改变混合/DNS监听端口和节点loopback映射），相同传输通过；对example.com TXT查询经配置中的DoH代理取得rcode0 / 两条答案。没有启用系统TUN或系统DNS。
- 原样生成的Caddy主配置和独立片段validate通过；同一生成片段只把实验发行器改为内部CA后，信任该CA的TLS下载内容字节一致，YAML/no-store响应头符合，错误路径404。仍未测试真实公网ACME。
- 三份HTML本地链接、唯一ID与锚点检查通过；新HTML29个Shell块均bash -n成功，Pythonheredoc编译与JS node --check通过；原有教程7项测试通过。
- 独立审查修复：FlClash先停内核/关闭TUN和系统代理再激活、订阅片段使用独立/etc/ironmao-proxy-caddy避免conf.d通配符重复import、专用站目录拒绝无状态覆盖、unit主组表述、回退reload失败恢复磁盘主配置。复审无剩余Critical/Important项。
- 实际Chrome本地文件预览打开成功，首页、实验表与目录排版可读；目录与复制按钮的关联静态核对；未做 GUI 复制点击、移动设备或打印分页验收。
- 真实systemd PID1服务启动、GUI导入配置覆盖、公网DNS/ACME、用户到VPS的运营商链路仍为用户现场验收。

## 记忆与同步

工作区 Mem0 的 DEEPSEEK_API_KEY 尚未配置；不读取或安装秘密。验收记录作为可追溯回退。最终只提交本任务文件，不包含其它子项目改动。

## 最终状态

18项实验工具测试、7项原教程测试、29个Shell块、7个Python heredoc、三份HTML链接与脚本检查均通过。测试容器已全部停止；未停止其它项目容器，所有独立FlClash实验内核退出且监听关闭。Mem0查询与回写均因缺少DEEPSEEK_API_KEY失败，未要求用户补密钥，证据已写入本记录。只同步本任务的3份HTML、实验工具与无凭据结果、计划和验收记录。
