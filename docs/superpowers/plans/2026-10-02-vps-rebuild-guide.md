# VPS 重建与静态网站部署教程 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 交付一份本地可打开、中文、包含网站入口和逐步命令的 HTML 教程，指导用户重建 ColoCrossing VPS、恢复个人代理并部署内容网站。

**Architecture:** 单文件 HTML，内嵌 CSS 与轻量 JavaScript。完整教程以静态 HTML 保存；JavaScript 只负责替换经过校验的 IP/域名、复制命令和保存步骤进度，不收集密码、私钥或节点凭据。教程默认使用网站 TCP 80/443、Reality TCP 8443、面板回环地址 18080 和 SSH 隧道。

**Tech Stack:** HTML/CSS/JavaScript、Node 原生测试、Python HTML 检查、Caddy 官方容器用于配置和路由验证。

---

### Task 1: 核对并编排教程

**Files:**
- Create: `01-infrastructure/vps-rebuild/VPS重建与网站部署一步步教程.html`

- [x] 核对 ColoCrossing 云后台与基础设施防火墙、3X-UI 当前稳定版、Caddy 官方安装方法、Cloudflare DNS 页面、Clash Verge 与 Mihomo Reality 配置。
- [x] 编写连续流程：成本与准备 → 旧数据备份 → 控制台重装 → SSH 初始化 → 管理用户与密钥 → 防火墙与 SSH → 代理面板与客户端 → Caddy → 金融站构建上传 → DNS/HTTPS → 验证/更新/备份 → 第二站迁移。
- [x] 每一步标注执行地点、操作入口、成功条件与出错后的检查路径。提供重装前数据备份、SSH 主机指纹核对、密钥验证后再关闭密码登录的顺序。
- [x] 工程笔记迁移使用独立预览域名先验证，正式域名切换前保留旧记录；A 股后端单列后续工作，不将静态网站步骤当成后端部署步骤。

### Task 2: 制作页面与交互

**Files:**
- Create: same HTML
- Test: `01-infrastructure/vps-rebuild/tests/guide.test.cjs`

- [x] 先运行参数与命令生成验收，确认教程尚未生成时测试失败；覆盖 IPv4 范围、域名与路径校验、命令插入防护及参数替换。
- [x] 实现内嵌 `parseSettings` / `renderTemplate`，所有生成内容使用 `textContent`，不使用用户输入生成 HTML；无 JavaScript 时仍可读默认教程。
- [x] 实现侧栏目录、响应式排版、命令复制、步骤勾选和打印样式；本地存储异常时继续提供正常阅读与复制。
- [x] 页面不加载外部字体、脚本或追踪资源；外部链接打开新标签，来源列在对应章节与页尾。

### Task 3: 验证、审查与同步

**Files:**
- Create: `docs/superpowers/acceptance-2026-10-03-vps-rebuild-guide.md`
- Modify: this plan to record completed work

- [x] 运行 Node 参数验收、HTML 标记/锚点/模板扫描、内嵌脚本语法检查。
- [x] 用 Caddy 容器核对教程中的静态站配置，对现有金融站产物验证首页、课程深链接、RSC 文件、缺失页面与资源响应；不连接或修改用户 VPS。
- [x] 申请一次范围明确的只读代码审查，修复有实际影响的问题。
- [x] 本地视觉预览若工具不可用，记录具体限制，不声称已完成视觉检查。
- [x] 按 `verification-before-completion` 留下验证记录；按工作区 SOP 尝试 Mem0 回写，只有本次文件进入提交与同步，不包含其它项目的改动。

验收证据与工具限制见 `docs/superpowers/acceptance-2026-10-03-vps-rebuild-guide.md`。

### Task 4: 将用户明确选择的彻底重装写入教程（2026-10-03）

用户已明确要求彻底重装，并要求把本轮实际后台操作和 SSH 登录问题更新到 HTML；本任务只修改教程，不执行重装或设置密码。

**Files:**
- Modify: `01-infrastructure/vps-rebuild/VPS重建与网站部署一步步教程.html`
- Modify: `docs/superpowers/acceptance-2026-10-03-vps-rebuild-guide.md`

- [x] 将第 2 步改为确认清空范围，旧服务器备份放入可选折叠分支；明确无需旧 root 密码，电脑工作区不受影响。
- [x] 第 3 步写明真实详情页、Install → Reinstall OS、Select OS、新密码两次填写、Remove old SSH Keys、Reinstall 和 Tasks And Logs。系统列表空白时停止提交，不将其认定为已选系统；新密码和最终提交由用户自行完成。
- [x] 第 4 步使用 `ssh -o PubkeyAuthentication=no -o PreferredAuthentications=password root@23.94.184.3`，说明 Mac 终端、密码无回显、成功提示，以及认证失败/连接拒绝/指纹变化的不同检查路径。
- [x] 执行现有 7 项测试、DOM 交互检查、HTML 锚点和命令语法检查；只读复核改动，记录实际 UI 观察与此前非预期重启，不声称已重装；提交并同步本次文件。

### Task 5: 将第 4–5 步的现场问题写回教程（2026-10-04）

用户已完成 SSH 密钥步骤，要求判断并更新 HTML。沿用已经确定的单文件、18 步设计；本次修订限定为第 3–5 步说明与对应故障表，不新增 JavaScript 功能、部署流程或服务器操作。

**Files:**
- Modify: `01-infrastructure/vps-rebuild/VPS重建与网站部署一步步教程.html`
- Modify: this plan and `docs/superpowers/acceptance-2026-10-03-vps-rebuild-guide.md`

- [x] 第 4 步按 SSH 提示的主机密钥类型分别给出 RSA / ED25519 的 VNC 读取命令，明确比较完整 SHA256 字符串、位数与备注不参与核对；不将本次指纹写成未来重装的信任值。补充 VNC 未连接时的商家工单核对路径，核对后日常使用 SSH。
- [x] 第 5 步解释密钥登录和 deployer 的目的，明确保留 root 窗口并用 ⌘N 开 Mac 本地窗口，执行 `echo "$HOME"` 区分 `/Users/...` 与 `/root`。两份密钥都不存在才生成，保持公钥上传、服务器安装和验证的连续顺序。
- [x] 说明 root 密码 / deployer 密码 / 密钥口令的输入位置；`PreferredAuthentications=password` 是固定认证方式，密码只在交互提示输入。空口令可继续，说明文件保护差异，并给出 Mac 本地 `ssh-keygen -p -f "$HOME/.ssh/ironmao_vps"` 为同一私钥补口令的可选操作。
- [x] 保留登录与 sudo 成功后才关闭 root / 密码登录的门槛；对应故障表补充本地/服务器窗口混淆和 SCP 参数误填。文案编辑不新增镜像实现的字符串断言测试，运行已有 `node --test 01-infrastructure/vps-rebuild/tests/guide.test.cjs`、整页 DOM 验证、所有命令块 `bash -n`、HTML 锚点与内嵌脚本语法检查，并以 `ssh -G` 不联网检查认证选项。
- [x] 只读复核改动，按实际结果记录验证与用户确认的进度；尝试 Mem0 回写，只提交并推送本次教程与记录。

### Task 6: 单独提供日常登录与维护手册（2026-10-04）

用户关心关闭 root SSH 后的部署便利性，并要求维护一份以后可查的操作文档。采用与现有教程配套的独立 HTML：保留完整重建教程，同时提供较短的日常操作入口；不自动修改 Mac SSH 配置或真实服务器。核心设计是登录 deployer → 普通操作直接执行 → 管理操作 sudo / sudo -i，关闭 root SSH 不删除 root 账号。服务命令按完成相应安装后的条件使用。

**Files:**
- Create: `01-infrastructure/vps-rebuild/VPS日常登录与维护手册.html`
- Modify: rebuild HTML links / step 6 explanation, this plan, acceptance record

- [x] 手册包含当前 IP、deployer 登录命令、可选 SSH 简称配置、sudo / sudo -i 与 exit 的区别、服务检查和重启、SSH 面板隧道、网站发布与回滚及备份入口。密码 / 私钥 / WebBasePath 不写入文档，未来部署任务以完整教程对应步骤为准。
- [x] 补充系统升级后的重启与密钥重连、常见 SSH 故障与 VNC 救援入口；只列必要的只读检查和已安装服务的维护命令，不将 root SSH 关闭描述成删除 root 或失去管理权限。
- [x] 两份 HTML 互相链接；检查链接、静态资源、复制功能与命令语法，运行完整教程现有检查；只读复核、记录并同步。

### Task 7: 补充安装凭据位置与隧道账号说明（2026-10-04）

用户继续安装并贴出日志：UFW 规则与 SSH 配置检查已执行，3X-UI v3.8.5 的凭据显示在 Panel Installation Complete 区域，后续 Fail2ban 日志将其顶到上方。只记录字段位置和验证进度，不保存或重复用户名、密码、实际 WebBasePath、API Token 或疑似 root 密码。

- [x] 第 7 步明确凭据区域的位置，说明安装器的 root SSH 示例应替换为第 8 步的 deployer 隧道命令。
- [x] 核对官方固定版本的安装器字段，为忘记安装输出时提供 `sudo grep -E '^XUI_(USERNAME|PASSWORD|WEB_BASE_PATH)=' /etc/x-ui/install-result.env`，只在用户自己电脑查看。注明初始记录与后续改密不同，API Token 不纳入查看命令。
- [x] 将面板回环绑定、凭据查看与完整教程入口加入维护手册，并继续进行文档验证与只读复核。

- [x] 两份 HTML 补充可直接复制的 28080 备用 SSH 隧道与对应浏览器地址，远端仍为回环 18080；说明默认打开按钮使用 18080，备用地址路径随主教程参数更新。
