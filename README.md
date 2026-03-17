# SkyMail Inbox Bridge

[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/github/license/lovely71/skymail_client)](./LICENSE)
[![Last Commit](https://img.shields.io/github/last-commit/lovely71/skymail_client)](https://github.com/lovely71/skymail_client/commits/main)
[![Dependencies](https://img.shields.io/badge/dependencies-standard--library-success)](./src)

中文：一个基于 Python 标准库的 SkyMail 收件桥接服务，用来把 SkyMail 站点封装成更容易集成的随机邮箱与收件 API。  
English: A lightweight Python-only bridge that turns a SkyMail deployment into an easier-to-integrate random inbox and message retrieval API.

## Overview / 项目简介

中文：这个项目适合把现有 SkyMail 站点包装成一个更稳定、更容易被业务系统调用的中间层。  
English: This project wraps an existing SkyMail deployment into a simpler integration layer for backend services.

适用场景 / Typical use cases:

- 中文：注册测试、验证码收集、临时邮箱、自动化集成测试  
  English: Signup testing, verification-code collection, temporary inboxes, and integration testing.
- 中文：内部工具统一接入 SkyMail，而不是每个系统单独处理登录和轮询  
  English: Internal tools that should not implement SkyMail login and polling by themselves.

## Features / 功能特性

- 中文：获取站点公开可用的域名列表  
  English: List publicly available domains from the target SkyMail deployment.
- 中文：生成 `localpart@domain` 形式的随机邮箱地址  
  English: Create random inbox addresses in the `localpart@domain` format.
- 中文：查询某个随机地址收到的邮件  
  English: Read messages delivered to a specific random inbox.
- 中文：长轮询等待新邮件  
  English: Wait for new messages with long polling.
- 中文：内置浏览器风格请求头，兼容部分 Cloudflare 限制  
  English: Sends browser-like headers to improve compatibility with some Cloudflare-protected deployments.
- 中文：纯 Python 标准库实现，无第三方依赖  
  English: Pure Python standard-library implementation with no third-party dependencies.

## How It Works / 工作原理

中文：本项目不依赖 `/api/public/*`，而是用一个已有 SkyMail 账号登录后调用后台接口。  
English: This project does not depend on `/api/public/*`; it logs in with an existing SkyMail account and uses authenticated backend APIs.

主要上游接口 / Main upstream APIs:

- `POST /api/login`
- `GET /api/setting/websiteConfig`
- `GET /api/setting/query`
- `GET /api/allEmail/list`
- `POST /api/email/send`

中文：这样做的好处是把登录、token 刷新、轮询和 Cloudflare 兼容逻辑集中到一个服务里。  
English: This centralizes login, token refresh, polling, and Cloudflare compatibility in one place.

## Requirements / 使用前提

1. 中文：登录账号需要有足够权限，例如 `all-email:query`。  
   English: The login account must have sufficient permissions, such as `all-email:query`.
2. 中文：如果要接收未创建的随机地址邮件，目标站点必须允许未创建收件人接收邮件。  
   English: If you want random unprovisioned inboxes to receive mail, the target deployment must allow delivery to non-created recipients.

## Cloudflare Notes / Cloudflare 说明

中文：部分部署会封禁 Python 默认 `User-Agent`，返回 `Error 1010`。本项目默认发送浏览器风格请求头，以兼容这类站点。  
English: Some deployments block Python's default `User-Agent` and return `Error 1010`. This project sends browser-like headers by default to improve compatibility.

中文：如果站点对 API 路径启用了更严格的 WAF 或 Challenge，则需要服务端放行，客户端代码无法稳定绕过。  
English: If the site owner applies stricter WAF or challenge rules to the API routes, the API paths must be allowed on the server side. Client code cannot reliably bypass that.

## Project Layout / 项目结构

```text
.
|-- .env.example
|-- .gitignore
|-- CHANGELOG.md
|-- RELEASE_NOTES_v0.1.0.md
|-- example_wait_code.py
|-- LICENSE
|-- README.md
`-- src
    |-- client.py
    |-- config.py
    `-- server.py
```

## Quick Start / 快速开始

1. 复制环境变量模板 / Copy the environment template

```powershell
Copy-Item .env.example .env
```

2. 编辑 `.env` / Edit `.env`

```env
HOST=127.0.0.1
PORT=3000
APP_TOKEN=change-me
SKYMAIL_BASE_URL=https://your-skymail.example.com
SKYMAIL_EMAIL=your-login@example.com
SKYMAIL_PASSWORD=your-password
DEFAULT_DOMAIN=example.com
RANDOM_LOCAL_LENGTH=10
DEFAULT_POLL_MS=3000
DEFAULT_WAIT_TIMEOUT_MS=30000
REQUEST_TIMEOUT_SEC=30
```

3. 启动服务 / Start the service

```powershell
python src/server.py
```

4. 健康检查 / Health check

```bash
curl http://127.0.0.1:3000/health
```

## Configuration Table / 环境变量参数表

| Variable | Required | 中文说明 | English Description |
| --- | --- | --- | --- |
| `HOST` | No | 本地服务监听地址 | Bind host for the local bridge service |
| `PORT` | No | 本地服务监听端口 | Bind port for the local bridge service |
| `APP_TOKEN` | Recommended | 本地桥接服务校验用的 `x-api-key` | Shared token expected in `x-api-key` |
| `SKYMAIL_BASE_URL` | Yes | 目标 SkyMail 站点根地址 | Base URL of the target SkyMail deployment |
| `SKYMAIL_EMAIL` | Yes | 用于登录的 SkyMail 邮箱账号 | SkyMail login email used by the bridge |
| `SKYMAIL_PASSWORD` | Yes | 用于登录的 SkyMail 密码 | SkyMail login password used by the bridge |
| `DEFAULT_DOMAIN` | No | 默认用于生成随机邮箱的域名 | Preferred domain for random inbox creation |
| `RANDOM_LOCAL_LENGTH` | No | 随机邮箱前缀长度 | Length of the generated local part |
| `DEFAULT_POLL_MS` | No | 长轮询默认轮询间隔，单位毫秒 | Default polling interval in milliseconds |
| `DEFAULT_WAIT_TIMEOUT_MS` | No | 长轮询默认等待超时，单位毫秒 | Default long-poll timeout in milliseconds |
| `REQUEST_TIMEOUT_SEC` | No | 请求上游 SkyMail 的超时秒数 | Timeout for upstream SkyMail requests in seconds |

## Example Script / 示例脚本

中文：项目自带一个端到端示例脚本 `example_wait_code.py`，可以生成随机邮箱、等待收件、提取验证码。  
English: The repository includes `example_wait_code.py`, an end-to-end demo that creates a random inbox, waits for mail, and extracts likely verification codes.

### CLI Arguments / 命令行参数表

| Argument | Required | 中文说明 | English Description |
| --- | --- | --- | --- |
| `--domain` | No | 指定优先使用的域名，例如 `example.com` | Preferred domain, for example `example.com` |
| `--timeout-ms` | No | 等待新邮件的总超时，毫秒 | Total wait timeout in milliseconds |
| `--poll-ms` | No | 轮询间隔，毫秒 | Polling interval in milliseconds |
| `--self-test` | No | 是否用当前登录账号给随机地址发一封测试信 | Send a self-test email from the logged-in account |
| `--subject` | No | 自测邮件主题 | Custom subject for the self-test email |
| `--local-length` | No | 随机邮箱前缀长度 | Random local-part length |

### Usage / 用法

自测一轮 / Run a self-test:

```powershell
python example_wait_code.py --domain example.com --self-test
```

等待外部系统发信 / Wait for an external sender:

```powershell
python example_wait_code.py --domain example.com --timeout-ms 60000
```

## HTTP API / HTTP 接口

中文：除 `/health` 外，其余接口在设置了 `APP_TOKEN` 时都需要请求头 `x-api-key`。  
English: All endpoints except `/health` require the `x-api-key` header when `APP_TOKEN` is configured.

### Auth Header / 鉴权头

| Header | Required | 中文说明 | English Description |
| --- | --- | --- | --- |
| `x-api-key` | Conditional | 当 `APP_TOKEN` 已配置时必填 | Required when `APP_TOKEN` is configured |

### `GET /health`

中文：返回服务健康状态。  
English: Returns a simple health payload.

| Field | Type | 中文说明 | English Description |
| --- | --- | --- | --- |
| `ok` | boolean | 是否正常 | Health status |
| `service` | string | 服务名称 | Service name |
| `baseUrl` | string | 当前配置的上游地址 | Configured upstream base URL |

### `GET /domains`

中文：返回目标 SkyMail 站点公开暴露的域名列表。  
English: Returns the domain list exposed by the target SkyMail deployment.

| Query Param | Required | 中文说明 | English Description |
| --- | --- | --- | --- |
| None | No | 无参数 | No query parameters |

示例 / Example:

```bash
curl http://127.0.0.1:3000/domains \
  -H "x-api-key: change-me"
```

### `POST /inboxes/random`

中文：生成一个随机邮箱地址。  
English: Creates a random inbox address.

#### Request Body / 请求体参数表

| Field | Type | Required | 中文说明 | English Description |
| --- | --- | --- | --- | --- |
| `domain` | string | No | 指定使用哪个域名 | Preferred domain to use |
| `localLength` | integer | No | 指定本次生成的随机前缀长度 | Local-part length for this request |

#### Response Fields / 返回字段

| Field | Type | 中文说明 | English Description |
| --- | --- | --- | --- |
| `address` | string | 完整邮箱地址 | Full inbox address |
| `localPart` | string | 本地前缀部分 | Local part of the inbox |
| `domain` | string | 实际使用的域名 | Domain that was selected |
| `mode` | string | 当前收件模式 | Current inbox mode |

示例 / Example:

```bash
curl -X POST http://127.0.0.1:3000/inboxes/random \
  -H "Content-Type: application/json" \
  -H "x-api-key: change-me" \
  -d "{\"domain\":\"example.com\",\"localLength\":10}"
```

### `GET /inboxes/:address/messages`

中文：查询某个随机地址当前已收到的邮件。  
English: Returns current known messages for a specific inbox.

#### Query Parameters / 查询参数表

| Param | Type | Required | 中文说明 | English Description |
| --- | --- | --- | --- | --- |
| `limit` | integer | No | 最多返回多少封邮件，默认 `20` | Maximum messages to return, default `20` |
| `mode` | string | No | 查询模式，默认 `noone` | Query mode, default `noone` |

#### Response Fields / 返回字段

| Field | Type | 中文说明 | English Description |
| --- | --- | --- | --- |
| `address` | string | 当前查询的邮箱地址 | Inbox address being queried |
| `total` | integer | 上游返回的总数 | Total count reported by upstream |
| `messages` | array | 过滤后的邮件列表 | Filtered message list |

#### Message Object / 邮件对象字段

| Field | Type | 中文说明 | English Description |
| --- | --- | --- | --- |
| `emailId` | integer | 邮件 ID | Message ID |
| `from` | string | 发件人邮箱 | Sender email |
| `fromName` | string | 发件人名称 | Sender display name |
| `to` | string | 收件地址 | Recipient address |
| `subject` | string | 邮件主题 | Subject |
| `text` | string | 纯文本正文 | Plain-text body |
| `html` | string | HTML 正文 | HTML body |
| `status` | integer | 邮件状态码 | Message status code |
| `createdAt` | string | 创建时间 | Creation timestamp |
| `raw` | object | 上游原始对象 | Raw upstream payload |

示例 / Example:

```bash
curl "http://127.0.0.1:3000/inboxes/demo123%40example.com/messages?limit=20&mode=noone" \
  -H "x-api-key: change-me"
```

### `GET /inboxes/:address/wait`

中文：长轮询直到收到新邮件或超时。  
English: Long-polls until a new message arrives or the timeout is reached.

#### Query Parameters / 查询参数表

| Param | Type | Required | 中文说明 | English Description |
| --- | --- | --- | --- | --- |
| `afterId` | integer | No | 仅等待大于该 ID 的新邮件 | Only wait for messages newer than this ID |
| `timeoutMs` | integer | No | 等待总超时，默认来自配置 | Total wait timeout in milliseconds |
| `pollMs` | integer | No | 轮询间隔，默认来自配置 | Poll interval in milliseconds |

#### Response Fields / 返回字段

| Field | Type | 中文说明 | English Description |
| --- | --- | --- | --- |
| `address` | string | 当前等待的邮箱地址 | Inbox address being watched |
| `afterId` | integer | 等待起始游标 | Starting cursor |
| `messages` | array | 新收到的邮件列表 | Newly received messages |

示例 / Example:

```bash
curl "http://127.0.0.1:3000/inboxes/demo123%40example.com/wait?afterId=0&timeoutMs=30000&pollMs=3000" \
  -H "x-api-key: change-me"
```

## License / 许可证

中文：当前仓库使用 MIT License。  
English: This repository is released under the MIT License.

## Security Recommendations / 安全建议

- 中文：不要提交 `.env` 到仓库  
  English: Do not commit `.env`.
- 中文：尽量使用低权限专用账号  
  English: Prefer a dedicated low-privilege account.
- 中文：开发中使用过的密码建议在发布前轮换  
  English: Rotate any credentials used during development before publishing.
- 中文：除纯本地环境外，建议始终启用 `APP_TOKEN`  
  English: Keep `APP_TOKEN` enabled outside local-only environments.
- 中文：确认目标站点不会暴露超出预期范围的邮件数据  
  English: Review whether the target deployment exposes mail beyond your intended scope.

## Release Notes / 发布说明

- 中文：首个版本说明见 [RELEASE_NOTES_v0.1.0.md](./RELEASE_NOTES_v0.1.0.md)  
  English: The first release notes are available in [RELEASE_NOTES_v0.1.0.md](./RELEASE_NOTES_v0.1.0.md).
- 中文：变更历史见 [CHANGELOG.md](./CHANGELOG.md)  
  English: The changelog is available in [CHANGELOG.md](./CHANGELOG.md).
