# 工作台后端

Flask 3、SQLAlchemy、Flask-Migrate，独立数据库与服务端会话。主入口为 `workbench:create_app`，生产入口为 `wsgi:app`。根目录 README 提供安装、初始化与开发启动命令。

应用启动不创建表。首次启动前运行根目录 `pnpm db:upgrade`。测试运行 `pnpm test:backend`，每个用例在临时 SQLite 数据库执行正式迁移，不读取本地 `.env` 中的数据库，也不连接训练营或生产服务。

`requirements.txt` 和 `requirements-dev.txt` 是包含传递依赖、版本及哈希的 Python 3.12 跨平台锁定清单，分别用于运行与测试。更新时在本目录执行：

```sh
uv pip compile requirements.in -o requirements.txt --python 3.12 --generate-hashes --universal
uv pip compile requirements-dev.in -o requirements-dev.txt --python 3.12 --generate-hashes --universal
```

## 本地治理授权

只有完成真实身份准入的本地账号才可授予治理概览权限。此命令不会创建账号、跳过社团资格或赋予工作区成员关系。`issuer` 和 `subject` 必须与身份提供方返回的稳定标识精确一致，不使用邮箱或姓名。

```sh
.venv/bin/flask --app workbench:create_app grant-governance \
  --issuer '<configured-issuer>' --subject '<existing-subject>' --reason '<approval-reference>'
```

附加 `--revoke` 撤销。每次操作写入本地审计记录；已停用账号的既有治理授权仍可撤销。这里仅开放只读的 `governance:view`，不是整套管理后台。

## 身份适配器

默认 `DisabledProvider` 返回未接通状态。`HttpIdentityProvider` 是待训练营实现的新接口消费端，禁止把现有商城票据接口直接填入配置。适配器使用 HTTPS、HTTP Basic 专用客户端认证、PKCE S256、固定回调及用途校验；HTTP 跳转不会携带客户端凭据跟随。

回调成功后创建独立随机会话，Cookie 原文不落库。工作台每个受保护业务请求复核上游三项准入状态、人员映射和安全版本，网络故障返回 503。成功回复中的来源角色没有授权效果。后端 `logout` 只撤销自己的会话，上游故障时仍可使用已持有的 CSRF 值退出。

完整字段、错误语义、部署与迁移边界见根目录 `docs/IDENTITY-CONTRACT.md` 和 `docs/MIGRATION.md`。缺少端点、专用客户端或联调验收时，不应启用真实入口。部署已完成认证 Redis 限流和登录尝试/消费记录到期清理；服务端独立 worker 同时负责提醒与组织授权同步。不会自动删除业务审计。服务器隔离 MySQL 迁移与业务流程已验证，实际并发负载和恢复演练仍需专项安排。
