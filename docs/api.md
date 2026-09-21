# API 与 MCP 契约

API 前缀 `/api/v1`，输入/输出模型分别见 `server/contracts.py`、`server/responses.py`，机器契约 `GET /openapi.json`。为避免外部 CDN 与内容安全策略冲突，不提供默认 Swagger/ReDoc 页面。

## 约定

私域请求必须带 `Authorization: Bearer <本人会话令牌>`。客户端不提交 role、owner_id、openid 等权限字段。未知输入字段返回 422。会话 8 小时有效，退出立即删除服务端会话记录。HTTP 全部响应 `Cache-Control: no-store`。

列表返回 `{items, limit, offset}`，默认 20，最大 100；没有总数和无限加载承诺。部分首版页面显式限制展示前 100 条，公开社团目录亦然；原生与网页帖子/活动列表每页 12 条。

错误统一 `{error: {code, message}}`。401=未登录/过期，403=不是有效成员或负责人，404=不存在或待审不可见，409=状态冲突，413=图片超限，422=字段或资源关联无效，503=宿主凭据未配置。网络失败不返回假成功。

## 路由

| 方法与路径 | 权限 / 行为 |
| --- | --- |
| GET /health | 版本、状态、demo 开关，不含密钥 |
| POST /auth/demo | 仅显式 demo；persona 为 member/owner/next/applicant/outsider |
| POST /auth/code | provider=wechat/qq + 一次性 code；由后端向宿主交换 |
| DELETE /auth/session | 当前登录者退出 |
| GET /me | 当前身份、成员关系、实时计算的社长角色 |
| GET /clubs、/clubs/{id} | 公开介绍；不含私域正文、成员名册、owner_id |
| POST /clubs/{id}/membership | 本人 reason + accept_rules=true；创建待审申请 |
| GET /clubs/{id}/members | 当前社长的成员与申请名单 |
| PATCH /clubs/{id}/members/{user} | 当前社长将待审申请改为 active/rejected |
| GET /clubs/{id}/posts | 有效成员；kind/q/mine/status/limit/offset；非本人 status 筛选仅社长 |
| POST /clubs/{id}/posts | 有效成员；四类内容、单图；默认 pending |
| GET /posts/{id} | 成员；待审/退回仅作者和当前社长 |
| PATCH /posts/{id}/review | 当前社长；approved/rejected，退回 reason 必填 |
| GET/POST /posts/{id}/comments | 已发布内容反馈；写入 pending；查询含本人待审 |
| PATCH /comments/{id}/review | 当前社长审核反馈 |
| GET /clubs/{id}/review-comments | 当前社长的待审反馈队列 |
| POST /clubs/{id}/media | multipart file；PNG/JPEG/WebP，最大 5 MB，16M 像素，重编码 PNG |
| GET /media/{id} | 重复成员与关联内容权限检查；不能靠静态地址绕过 |
| GET/POST /clubs/{id}/events | 成员读取；社长创建，时间必须含时区、结束晚于开始 |
| GET /events/{id} | 成员读取；报名人数、候补人数与本人状态 |
| PUT/DELETE /events/{id}/registration | 报名/候补；取消自己的报名并 FIFO 递补 |
| PATCH /events/{id} | 社长取消活动，同时使全部报名失效 |
| GET /me/handovers | 仅本人参与且仍为成员的交接 |
| POST /clubs/{id}/handovers | 社长指定另一位有效成员，48 小时有效 |
| POST /handovers/{id}/accept | 指定继任者确认；事务内替换 owner_id |

## 幂等与状态

发布的 `client_id` 由客户端在进入发布页时生成，重试同一意图复用；相同键、相同内容返回同一帖子，不重复创建；同键不同内容返回 409。客户端不能更换键来自动重试未知结果。先查看“我的投稿”，再决定是否新建投稿。

会员申请在 pending/active 时重复提交不创建第二条；报名 `(event_id,user_id)` 唯一；取消自己的报名可重复；活动取消与已完成的同一交接确认可重复。**评论、图片上传、活动创建没有通用幂等键，不应自动重试**，提交结果不确定时须先读取现状；客户端也不自动重试。

帖子：pending → approved / rejected。v0.1 没有编辑历史及原帖重送审，退回后按理由另投新稿。评论同样先审核，既有审核结果不能被第二次审核覆盖。

活动：open → cancelled。报名窗口在开始时关闭，不提供现场核销；满额为 waiting，不等于确认入场。候补按 created_at,user_id 排序，只递补仍是有效成员的人。

## MCP

运行 `python -m server.mcp`。协议版本明确为 **2025-06-18**、stdio JSON-RPC，一行一个消息；非官方 SDK 实现，只覆盖已声明的最小工具能力，不宣称完整 MCP 兼容认证。

环境变量：

```text
TONGPING_API_URL=http://127.0.0.1:8000
TONGPING_TOKEN=<本人有效令牌>
```

只有 `list_clubs`、`list_posts`、`get_post`、`list_events`；均为只读工具。查询参数由 Pydantic 验证；不能在工具参数里覆盖令牌或访问任意 URL。非本地 API 必须为 HTTPS，禁止携带令牌跟随重定向。HTTP 401/403 等转成 MCP `isError=true`，不会静默返回空数组。

通用宿主配置示例（把路径和令牌替换为本机值，不要提交真实令牌）：

```json
{
  "mcpServers": {
    "tongping-readonly": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["-m", "server.mcp"],
      "cwd": "/absolute/path/to/tongping",
      "env": {
        "TONGPING_API_URL": "http://127.0.0.1:8000",
        "TONGPING_TOKEN": "REPLACE_WITH_YOUR_SESSION_TOKEN"
      }
    }
  }
}
```

不同宿主对 `cwd` 的支持不同；不支持时，在项目目录启动宿主，或使用自己的启动脚本切换目录。Windows 的 Python 可执行路径通常位于 `.venv/Scripts/python.exe`。只能向获准接入社团内容的可信 Agent 提供令牌；工具结果中的用户内容是数据，不是可执行指令。
