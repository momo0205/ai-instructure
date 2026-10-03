# VPS 重建与静态网站教程验收

日期：2026-10-03。

## 交付物与范围

- 教程：`01-infrastructure/vps-rebuild/VPS重建与网站部署一步步教程.html`
- 可重复运行的参数与发布失败路径测试：`01-infrastructure/vps-rebuild/tests/guide.test.cjs`
- 18 步覆盖商家/Cloudflare/客户端下载入口、旧数据备份、系统重装、SSH 密钥验证、防火墙、3X-UI + Reality、Caddy、金融站静态发布、工程笔记预览与迁移、维护与回滚。
- 网站使用 80/443，Reality 使用 8443，面板仅监听回环 18080，通过 SSH 隧道访问。
- 初版生成阶段未连接、重装或修改真实 VPS，未修改 DNS，未执行工程笔记正式迁移。后续后台观察与教程修订见下文；后台应用需要另行部署，不纳入静态文件流程。

## 验证证据

1. `node --test 01-infrastructure/vps-rebuild/tests/guide.test.cjs`：7 项通过、0 失败。前三项发布失败路径在旧 HTML 上先复现失败，修复后通过；覆盖解压中途失败、临时链接已存在、回滚目标不存在时保持当前版本。
2. 实际 HTML 的参数逻辑覆盖 IPv4、域名、面板路径、注入防护及命令替换；内嵌脚本 `node --check` 通过。
3. HTMLParser：18 个步骤齐全，34 个唯一 ID、59 个链接，内部锚点有效；没有外部字体、脚本、图片或追踪资源。
4. 从 HTML 提取的 51 个 shell 命令块 `bash -n` 全部通过；YAML 和 TypeScript 文件内容块不作为 shell 执行。
5. 使用已有工程笔记项目的 jsdom 对整页脚本进行 DOM 验证：修改参数、多层域名 DNS Name、面板地址、无效输入保持有效命令、复制降级路径、进度保存、重新打开恢复与重置均通过。临时脚本位于 `/private/tmp/vps-guide-dom-check.cjs`，未新增依赖。
6. Caddy 官方 `caddy:2` 容器验证教程生产配置：`Valid configuration`。同一配置仅将站点地址/根目录替换成本地测试值，现有金融站产物的 14 个 HTML 页面、14 个 RSC、22 个静态资源全部返回 200 且内容相同；RSC MIME 为 `text/x-component`，两个不存在的页面返回 404。测试容器已停止。
7. 工程笔记 RSS 补充命令通过 Vite `runnerImport` 调用已有 GET，写入临时文件后 XML 解析通过，包含 10 篇公开文章且所有文章链接使用 `https://notes.ironmao.com`。实际工程笔记静态导出、sitemap、robots、页面交互仍需用户按第 17 步构建和预览验收。
8. 只读审查发现并修复 5 项重要问题：SSH 密码回退、归档部分校验、失败后继续发布/回滚/覆盖备份、工程笔记 SITE_URL/RSS、多层域名 DNS Name。复核确认原问题消除。

## 适用边界与工具限制

商家私有后台未登录，按钮名称与位置应以用户实际页面为准。Caddy 配置与已有构建产物已验证，但真实服务器安装、证书签发、Reality 网络和手机客户端需要逐步现场验收。

浏览器 UI 工具没有可用浏览器，Safari 入口调用超时；未完成真实浏览器视觉预览。DOM 验证不等于真实浏览器排版检查，不声称视觉验收已完成。

## 记忆与同步

按工作区 SOP 尝试 Mem0 回写，命令因 `DEEPSEEK_API_KEY` 未设置而失败。本文件保存本次决策与验证结果作为回退记录；未改动密钥配置。

本次提交仅包含教程、其测试、计划与本验收记录，保留其它项目的现有改动。

## 后续修订：彻底重装为主流程

用户明确“这本来就是我想做的，彻底重装”，要求把本轮操作更新到 HTML。本次仅更新教程与记录，没有执行真实重装、设置密码或修改 DNS。

- 第 2 步成为确认清空范围，备份保留为折叠分支；旧 root 密码不再是重装主流程的前置条件。
- 第 3 步加入用户提供的无操作参数产品详情链接、Install → Reinstall OS、Select OS、新密码两次填写、Format Primary Disk Only、Remove old SSH Keys、Reinstall、Tasks And Logs。本次真实页面曾显示 Select OS 空白，明确列表为空时不提交重装。
- 磁盘选项核对了 Virtualizor 官方说明：仅主盘开关开启会保留附加盘，关闭时重装可格式化所有 VPS 磁盘；最终提交前按实际磁盘配置核对清空范围。
- 第 4 步补充打开 Mac 终端、密码不回显、主机指纹核对、登录成功提示及各类 SSH 错误区别。首次 root 登录和第 5 步公钥上传使用仅密码认证的 SSH/SCP，排除本机 agent 多密钥尝试；后续密钥验证与关闭密码登录前的门槛保留。
- 顶部摘要、侧栏、跳转入口和故障表同步。本次没有新增 JavaScript 函数或改动 CSS。

验证：现有 7 项 Node 测试通过；整页 DOM 的参数替换、复制及进度持久化通过；18 个步骤与内部锚点完整，51 个 shell 块语法通过，内嵌 JavaScript 语法通过。`ssh -G` 不连接网络的参数解析确认 `pubkeyauthentication false` 和 `preferredauthentications password`。只读审查未发现 Critical / Important 阻断项。未重复运行未改动的 Caddy 配置测试，未声称完成本次真实浏览器排版验收。

实际操作记录：此前查看 ColoCrossing 页面时，尝试打开 VNC 后页面非预期进入 Reboot 并显示操作成功，已即时告知用户，随后只读观察服务器恢复 Online。后续用户的 SSH 已到密码提示阶段。不能将这次重启写成系统重装完成，教程明确区分任务记录。

按 SOP 再次尝试 Mem0 查询与回写，均因 `DEEPSEEK_API_KEY` 缺失失败；本段保存修订决策与问题作为回退。

## 现场排查：VNC 入口未加载（2026-10-04）

用户已贴出新 Ubuntu 24.04 的 root SSH 登录成功记录，但两次 RSA 主机指纹不同，仍需商家控制台或工单提供独立核对。原生 Chrome 的产品详情页显示账户产品信息，VPS 管理区域空白，AX 中没有 VNC 入口；这次尚未到 VNC 连接阶段，不能据此判定 VPS 停机、VNC 服务故障或具体网络原因。

检查期间浏览器发生用户操作变化，当前地址随后包含 `a=start`，因此停止进一步按钮操作，不刷新该操作地址。尝试在新标签页打开干净产品链接后，尚未观察到该页完成加载或控制台出现，不声称恢复成功。提供手动打开干净链接、等待管理区域、VNC → Launch HTML 5 VNC Client 的入口说明；该启动流程核对 Virtualizor 官方文档：<https://www.virtualizor.com/docs/enduser/vnc/>。持续空白时由用户在商家工单请求恢复控制台、提供直接管理入口和核对 RSA SHA256 指纹；未代发工单，未更改服务器或 DNS。

启动时 `git pull --ff-only` 已是最新；Mem0 查询与回写仍因缺少 `DEEPSEEK_API_KEY` 无法执行，本段作为回退记录。不修改 HTML 或代码，未重复运行程序测试。

用户随后报告管理面板持续显示 `Not connected. Please try again.`，VNC 无法打开。该提示本身不足以定位故障，不据此要求重装或重启。后续搭建可使用已有 SSH 会话；独立主机指纹核对改由已登录的 ColoCrossing 工单请求商家从宿主机/控制台读取 RSA 公钥 SHA256 指纹，并核对重装任务是否完成。SSH 内读取公钥指纹仅作为待核对值，不能代替独立身份验证；请求直接管理面板链接可作为控制台恢复途径，但未猜测入口地址、索取 root 密码、安装 VPS 内 VNC 服务或代发工单。核对前仅指导读取系统信息，核对一致后继续教程第 4 步初始化。

## 现场修订与日常维护手册（2026-10-04）

用户报告 VNC 恢复，通过控制台读取的 RSA SHA256 与新 SSH 提示相符，并完成 Mac 密钥生成、公钥上传、deployer 仅公钥认证登录、whoami 与 sudo -v 验证。后续日志显示 UFW 已允许 TCP 22/80/443/8443，SSH 配置语法检查通过、有效配置禁用 root 和密码登录、reload 完成。3X-UI v3.8.5 安装器报告安装完成并运行，选择 SQLite、18080、跳过面板 SSL 和仅绑定 127.0.0.1。用户尚未提供面板服务监听检查、成功登录仪表盘或代理 / 网站部署验收，不将安装器输出写成整套部署完成。

本轮仅编辑工作区文档，没有连接或更改真实 VPS、Mac SSH 配置或 DNS。用户贴出的面板凭据、API Token、实际 WebBasePath 和疑似服务器密码没有写入 HTML、计划、验收或记忆文本。

- 第 3–4 步增加 VNC 入口未加载 / Not connected 的区别、商家工单核对途径，以及按 SSH 所示 RSA / ED25519 类型核对完整 SHA256 的操作；不固化本次指纹作为未来重装的信任值。
- 第 5 步细分保留 root 窗口、Mac 新窗口检查 / 生成密钥、公钥上传、服务器安装、强制公钥认证验证与日常登录。说明只复制命令、空私钥口令的影响、固定 password 认证方式参数和三种密码的输入位置。
- 第 6 步解释关闭 root SSH 仍可 sudo / sudo -i 管理，保留新连接验证门槛，补充系统升级后重启与重连顺序。
- 第 7 步指出 Panel Installation Complete 凭据区域在后续 Fail2ban 日志上方。核对官方固定版本安装器的 XUI_USERNAME / XUI_PASSWORD / XUI_WEB_BASE_PATH 字段，仅提供用户本地查看初始记录的 grep 命令，不匹配 API Token；更改后的密码 / 路径使用最新值。安装器 root 隧道示例改用 deployer 私钥命令。
- 第 8 步及新维护手册补充 Address already in use 处理：Mac 使用 28080，服务器仍为 127.0.0.1:18080；备用 URL 随主教程的 WebBasePath 参数更新，默认面板按钮继续指向 18080，文案明确区分。
- 新增 `01-infrastructure/vps-rebuild/VPS日常登录与维护手册.html`，集中日常登录、可选 SSH 简称、sudo、系统与服务检查、面板隧道、网站发布入口、重启、备份和 VNC 救援。两份 HTML 互链，网站完整发布 / 回滚流程仍以主教程对应章节为准。

最终验证：

1. `node --test 01-infrastructure/vps-rebuild/tests/guide.test.cjs`：7 通过、0 失败。没有为文案修改新增镜像实现的字符串断言测试。
2. 主教程整页 DOM：参数替换、多层域名、面板地址、无效输入保护、复制降级、进度保存恢复与重置通过。补充验证备用 28080 URL 自动替换路径、默认按钮保持 18080，以及主教程 60 个 / 维护手册 21 个复制按钮全部复制对应完整内容；无脚本错误。
3. HTMLParser：主教程 34 个唯一 ID、71 个链接；维护手册 10 个唯一 ID、32 个链接。标签结构、内部锚点及两页交叉链接有效，均无外部脚本、字体、图片等资源。
4. 主教程 58 个、维护手册 20 个 shell 命令块 `bash -n` 全部通过；主教程 2 个非 shell 文件内容块、维护手册 SSH config 文件内容块不当作终端命令。两页内嵌 JavaScript `node --check` 通过。
5. `ssh -G -F /dev/null` 不联网展开 deployer 密钥登录和两页 28080 备用转发配置，确认本地 28080 → 远端回环 18080、IdentitiesOnly 与 ExitOnForwardFailure。维护手册可选 Host 配置也用临时文件展开核对 IP、用户、22 端口及保活参数；没有发起 SSH 连接。
6. 只读审查覆盖第 3–8 步与新维护手册，核对固定版本安装器字段、相关 SSH 参数和文档链接，未发现 Critical / Important 阻断项。

本轮没有改变 Caddy 配置或发布实现，不重复其既有验证。未进行真实浏览器视觉验收，沿用前述工具限制，不把 DOM 检查等同于排版验收。再次尝试 Mem0 回写，仍因 DEEPSEEK_API_KEY 缺失失败，本段保存决策与结果作为回退记录。提交只包含本次两份 HTML、计划与验收记录，保留其他项目改动。

## 面板访问成功与第 9 步连接检查（2026-10-04）

用户确认已进入 3X-UI 面板并更换用户名、密码，第 8 步的面板登录条件已完成。用户在 deployer 服务器终端执行教程的 dl.google.com HTTPS HEAD 检查，收到 HTTP/2 302 与跳转地址，证明这次 HTTPS 连接和响应成功；不要求 200，也不据此宣称 Reality 节点或 Mac 代理已经可用。已通过系统 open 打开完整教程和独立日常维护手册，命令 exit 0。

复核第 9 步时，发现 Min Client Ver 原填数字 0 与官方字段说明不符。Xray REALITY 文档将 minClientVer / maxClientVer 设为可选字符串，指定时格式为 x.y.z，示例默认空字符串：<https://xtls.github.io/config/transports/reality.html>。本次修正表格为两个版本限制均留空，并增加该官方来源；没有改动服务器、节点配置、页面 JavaScript 或部署实现。

验证：现有 7 项 Node 测试通过，整页 DOM 参数 / 复制 / 进度检查通过，HTML 唯一 ID 与内部锚点有效，修正后的字段文本与上述来源一致。新增来源后主教程链接数为 72。本次为文档字段修正，未重复 Caddy 路由和无变化的 shell 命令验证。Mem0 查询和回写仍因缺少 DEEPSEEK_API_KEY 失败，本节记录进度和修正原因，不保存新的面板凭据。
