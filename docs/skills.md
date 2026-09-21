# 工程工作流与约束来源

## 本轮实际使用

已读取 `addyosmani/agent-skills` 的 README 与 using-agent-skills、spec-driven-development、planning-and-task-breakdown、api-and-interface-design、test-driven-development、frontend-ui-engineering、git-workflow-and-versioning 的 SKILL.md。读取时的上游提交：`dc27a9c2e13721158157632de61b4106c6c2a2a1`。

已读取 `lennney/stop-that-shit` 的 README 与 `skills/stop-that-shit/SKILL.md`。对应技能文件 blob：`a98a87d73ceccd7137f392cb0e97221e0a0f983c`；上游 README 当时提供 `0.2.2` 安装示例。

这里的“使用”指将已读取工作流用于本轮设计、实现和验收。**没有在当前执行环境安装 Codex/Claude Guard hooks，也不宣称具有机器强制拦截效果。** 仓库不修改使用者全局配置。

## 工作流到交付证据

| 工作流 | 落地位置 |
| --- | --- |
| Spec / capability map | docs/architecture.md：模块、依赖、数据与权限不变量，先于业务代码创建 |
| Planning | tasks/plan.md、tasks/todo.md：范围、验证点、进度 |
| Contract first | server/contracts.py、server/responses.py、/openapi.json、docs/api.md |
| TDD | tests/：最初私域详情测试因 404≠401 失败；实现后通过。MCP 先验证缺失模块，再实现 |
| UI engineering | web/ 与 mini/；沿用提供的原型视觉，保留真实错误/空态/权限状态 |
| Git workflow | 架构、服务、MCP、客户端、验证与交付分批提交；feature 分支，PR 人工审阅 |
| Stop That Shit | CONSTRAINTS.md：单体、现成依赖、明确范围、保留鉴权与事务，不添加投机扩展 |

用户已授权架构、开发和推送；并没有额外逐阶段人工签字。本轮架构选型是已披露的实施假设，PR 是下一次人工评审门禁，不伪造“人工已批准”。

## 后续会话的使用方法

先读根目录 AGENTS.md 与未完成任务，再从以下上游工作流中选择匹配阶段。已经有可验证实现的行为，不要无理由重写。外部 skills 未安装时，应说明状态，不得把文档引用称为已安装插件。

- Agent Skills：https://github.com/addyosmani/agent-skills/tree/dc27a9c2e13721158157632de61b4106c6c2a2a1
- Stop That Shit：https://github.com/lennney/stop-that-shit
- Stop That Shit skill：https://github.com/lennney/stop-that-shit/blob/main/skills/stop-that-shit/SKILL.md

## 实现参考与验证范围

- FastAPI 测试：https://fastapi.tiangolo.com/tutorial/testing/
- FastAPI 依赖：https://fastapi.tiangolo.com/tutorial/dependencies/
- SQLite 事务/备份：https://docs.python.org/3/library/sqlite3.html
- MCP stdio：https://modelcontextprotocol.io/specification/2025-06-18/basic/transports
- MCP tools：https://modelcontextprotocol.io/specification/2025-06-18/server/tools
- QQ 登录接口：https://q.qq.com/wiki/develop/miniprogram/server/open_port/port_login.html
- 微信登录接口：https://developers.weixin.qq.com/miniprogram/dev/OpenApiDoc/user-login/code2Session.html

微信官方页面在本次检索中未能完整获取；QQ 页面亦出现超时。身份适配器的成功、失败与账号隔离已有本地测试，**真实平台响应、开发者工具编译、真机网络与审核仍未验证**。本地构建生成文件不等于平台验收通过。
