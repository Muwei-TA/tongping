# 同频 Tongping

**面向校园社团的私域作品、知识与活动空间。**

v0.1 提供可运行的后端、浏览器联调界面、微信/QQ 原生页面源码，以及只读 MCP。不是只有静态原型；投稿、成员、审核、报名和换届均写入 SQLite。**尚未上架，不应直接开放给真实学生使用。**

## 快速运行

本次验证环境为 Python 3.13、Node.js 22。先创建 Python 虚拟环境并安装依赖：

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell 则使用：.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m server --demo
```

打开 **http://127.0.0.1:8000**。数据库默认 `data/tongping.sqlite`，重启不会清空。演示身份：林杳（成员）、陈序（社长）、周周（成员/候选继任者）、新同学（待入社）、夏禾（其他社团）。种子数据全部虚构。

`--demo` 只允许绑定本机。生产默认关闭演示登录，也拒绝使用带演示标记的数据库。不要把 demo 服务暴露到互联网。

## 本版能做什么

| 能力 | 实现 |
| --- | --- |
| 私域身份 | 微信/QQ code 交换适配器、可撤销会话；登录不等于入社 |
| 社团成员 | 查看公开介绍、同意社规、申请、社长审批 |
| 内容 | 作品/知识/提问/闲聊，单张图片、明确反馈目标、私域搜索、我的投稿 |
| 审核 | 帖子与反馈默认待审；作者可查进度，社长通过/退回并提供理由 |
| 活动 | 社长创建、成员报名、满额候补、取消后 FIFO 递补、活动取消 |
| 换届 | 社长发起、继任者本人确认、旧权限撤销，48 小时有效 |
| MCP | 四个只读工具，沿用同一后端身份和社团权限 |

首版没有公开广场、即时聊天、支付、学分、签到、完整消息中心、点赞收藏、视频上传、知识版本、举报申诉、跨平台账号绑定和原帖编辑重送审。退回内容可按说明另投新稿。界面不把未完成能力伪装成可用功能。

## 原生小程序

共用 8 页源代码：动态、社团与入社、发布、内容与反馈、活动列表、活动详情、社长工作台、账号与交接。

```bash
python scripts/build_mini.py
```

产物位于 `build/wechat/` 与 `build/qq/`，分别导入对应开发者工具，并填写自己的 AppID。脚本转换模板指令与扩展名，**不是平台编译器**。本轮没有微信/QQ 开发者工具及真机验证记录。

开发时 `127.0.0.1` 指设备自身；真机必须使用可达的测试 HTTPS 域名或受控开发隧道，不能直接沿用电脑的回环地址。正式构建示例：

```bash
python scripts/build_mini.py --target wechat --wechat-appid YOUR_APP_ID --api-base https://api.example.com --production
python scripts/build_mini.py --target qq --qq-appid YOUR_QQ_APP_ID --api-base https://api.example.com --production
```

由后端环境变量提供 `WECHAT_APP_ID`、`WECHAT_APP_SECRET`、`QQ_APP_ID`、`QQ_APP_SECRET`，密钥绝不进入小程序包。`.env.example` 只作为变量说明，应用不隐式加载 `.env`。平台需要分别配置 request/uploadFile/downloadFile 合法域名、隐私授权与平台要求的前置流程。没有凭据会返回 503，不会回退成演示账号。

### 开通真实试点社团

先关闭 demo、使用空数据库，完成真实宿主登录取得 `/api/v1/me` 的内部用户 ID。运营人员核实身份后执行：

```bash
python -m server.manage --db data/real.sqlite --owner USER_ID --name 动画研习社 --summary 一起创作的空间 --rules 尊重原创并保护成员隐私
TONGPING_ENV=production TONGPING_DB=data/real.sqlite uvicorn server.app:create_app --factory --host 127.0.0.1 --port 8000
```

上述环境变量写法适用于 POSIX shell；PowerShell 用 `$env:TONGPING_ENV='production'` 等分别设置。公网入口须由受控 HTTPS 反向代理提供，限制请求体、连接与请求速率，并按实际运营需求配置日志保留、治理和删除流程。此版本不是生产上线许可。

## 只读 MCP

```bash
# 在项目目录、已激活的 Python 环境中运行；令牌必须来自本人登录。
export TONGPING_API_URL=http://127.0.0.1:8000
export TONGPING_TOKEN=YOUR_SESSION_TOKEN
python -m server.mcp
```

工具为 `list_clubs`、`list_posts`、`get_post`、`list_events`。只支持明确声明的 MCP 2025-06-18 stdio 子集，不提供 Agent 代投稿、代审批或任意数据库访问。令牌 8 小时过期；只把内容接入社团允许的可信 Agent。完整宿主配置与参数见 [API/MCP 契约](docs/api.md)。

## 开发与验证

```bash
python -m pytest -q
python scripts/build_mini.py
python scripts/check.py
python -m playwright install chromium
python scripts/e2e.py
```

存在系统 Chromium 时会自动选择，也可 `--browser /path/to/chromium`。本次环境禁止浏览器 URL 导航，因此实际运行 `python scripts/e2e.py --bridge`：从同一 UI 源码离线渲染，fetch 通过 Python 桥接真实临时 HTTP 服务。它覆盖 UI 与后端交互，但**不等同于浏览器原生网络链路或小程序真机验证**。不修改浏览器策略。

CI 使用 GitHub Actions 执行测试、原生包生成、静态检查和原生浏览器 HTTP 工作流，并保留构建产物 7 天。CI 配置已提交不代表远端执行已成功；以具体运行记录为准。

## 结构与规则

```text
server/     HTTP 路由、输入/输出契约、按业务分开的服务、SQLite 连接/迁移、MCP
web/        无框架浏览器联调 UI：传输 / 页面加载 / 展示 / 交互分离
mini/       原生微信/QQ 共用页面，平台传输适配器
scripts/    构建、静态检查、浏览器验证、备份
tests/     API / SQLite / MCP / 源码构建 / 备份测试
docs/      架构、接口、技能来源、验收与发布限制
tasks/     开发计划与进度
```

选用模块化单体：连接文件没有业务规则；路由不写 SQL；业务服务使用参数化 SQL 和有明确边界的事务；MCP 只走鉴权 HTTP，不旁路读库。不引入 Redis、微服务、消息队列和没有消费者的通用框架。

工作流来自本轮读取的 `addyosmani/agent-skills`，范围与复杂度约束来自 `lennney/stop-that-shit`。本环境使用 **skill 文本约束**，未安装或声称启用 Guard hooks。具体证据与上游引用见 [skills](docs/skills.md)。后续 Agent 从 [AGENTS.md](AGENTS.md) 开始。

## 文档与交付边界

[架构与页面范围](docs/architecture.md) · [API/MCP](docs/api.md) · [验收报告](docs/verification.md) · [上线门禁](docs/release-gates.md)

数据库含私域内容、成员和会话摘要，请限制操作系统访问权限。备份命令：

```bash
python scripts/backup.py --db data/tongping.sqlite --out backups/tongping-YYYYMMDD.sqlite
```

备份使用 SQLite backup API，包括已提交 WAL 数据，不覆盖现有文件。附件也在同一数据库内。备份同样含私域信息，不能上传到公开仓库。
