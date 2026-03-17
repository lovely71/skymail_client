# Release Notes v0.1.0

## 中文

这是项目的首个公开版本，重点是提供一个纯 Python、零第三方依赖的 SkyMail 收件桥接层。

### 亮点

- 支持随机邮箱生成
- 支持查询指定收件地址的邮件
- 支持长轮询等待新邮件
- 提供验证码提取示例脚本
- 内置浏览器风格请求头，改善部分 Cloudflare 环境下的兼容性
- README 已整理为适合 GitHub 发布的中英双语版本

### 适合谁

- 需要给测试系统接一个临时邮箱能力的团队
- 想收取注册验证码、登录验证码、通知邮件的自动化脚本
- 希望统一封装 SkyMail 登录与轮询逻辑的后端服务

### 注意事项

- 需要一个具有足够查询权限的 SkyMail 账号
- 如果目标站点不允许未创建收件人收信，则随机邮箱模式不可用
- 如果目标站点对 API 开启了更严格的 Cloudflare WAF，仍需服务端规则放行

## English

This is the first public release of the project. It provides a pure-Python, zero-third-party-dependency inbox bridge for SkyMail deployments.

### Highlights

- Random inbox generation
- Message listing for a specific inbox
- Long-poll waiting for new messages
- Example script for verification-code retrieval
- Browser-like headers for improved compatibility with some Cloudflare-protected deployments
- GitHub-ready bilingual documentation

### Best For

- Teams that need disposable inboxes in test environments
- Automation that collects signup or login verification emails
- Backend services that want to centralize SkyMail login and polling logic

### Notes

- A SkyMail account with sufficient query permissions is required
- Random inbox mode depends on the target deployment accepting mail for unprovisioned recipients
- Stricter Cloudflare WAF policies still need to be handled by the site owner
