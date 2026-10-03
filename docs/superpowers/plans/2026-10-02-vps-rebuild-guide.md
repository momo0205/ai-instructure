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
