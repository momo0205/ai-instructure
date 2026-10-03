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
