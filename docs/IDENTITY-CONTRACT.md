# 工作台身份接入契约

状态：工作台消费端基础实现；训练营提供端待开发与联调。以下三个来源方端点是新契约，不是现有训练营或积分商城已经提供的服务。本契约使用授权代码与 PKCE，不宣称已实现完整 OAuth 或 OpenID Connect。

## 准入与主体

issuer 标识可信来源，subject 为该来源不可变账号标识，person_id 为该来源稳定自然人标识。大小写属于标识的一部分，数据库不得依靠默认不区分大小写的排序规则混同两个账号。姓名只是显示值；邮箱不用于自动合并身份。

来源方必须根据实时数据确认 account_active、person_active、community_active 三个布尔值。community_active 应包含社团身份有效期与撤销状态，不能仅以存在一条历史任职记录判断。三项都为 true 才可进入工作台。

security_version 在封禁、账号安全变更或归并等事件中更新。工作台会话保存登录时版本，每次受保护请求与来源方当前版本比较；变化后需重新认证。本地 Person 被禁用、Account 被停用或工作区人员否决也独立生效。

## 来源方需要新增的三个端点

端点地址由配置指定，客户端不能提交任意上游或回调地址。HTTP provider 只接受 HTTPS；两个后端间以 HTTP Basic 使用专用工作台客户端 ID 和随机客户端密钥认证，不使用人的密码或商城密钥。凭据只发给固定端点，不跟随重定向。

### 浏览器授权端点

接收 client_id、response_type=code、redirect_uri、state、code_challenge、code_challenge_method=S256、scope=workbench:access。校验已注册客户端和固定回调，使用训练营现有会话认证用户，再实时检查社团准入。不要要求用户进入训练营管理后台。

成功返回短期一次性 code，绑定 client_id、redirect_uri、PKCE challenge 及本次身份。将 code 和原样 state 返回已登记的工作台回调。代码建议至多 90 秒有效，必须在来源数据库或可靠存储中原子消费。拒绝不符合准入的用户，不能回退为普通商城资格。

### 后端代码兑换端点

工作台以后端专用客户端认证发起 POST，JSON 字段为 grant_type=authorization_code、code、code_verifier、redirect_uri、audience。来源方核验客户端、用途、过期时间、回调和 PKCE 后原子消费代码，返回下述身份形状。

### 后端当前状态端点

工作台以后端专用客户端认证发起 POST，字段为 issuer、subject、audience。来源方核对该客户端允许查询该来源，按当前事实返回身份与准入。每次受保护请求都会检查，不允许返回永久缓存资格。

### 身份响应

```json
{
  "issuer": "bme-training",
  "audience": "bme-workbench",
  "subject": "stable-account-id",
  "person_id": "stable-person-id",
  "display_name": "成员姓名",
  "security_version": "1",
  "account_active": true,
  "person_active": true,
  "community_active": true
}
```

以上标识均是说明用占位值。所有字段必须存在且类型严格符合契约；字符串标识不能为空。工作台比对 issuer 和 audience，不读取中央 role 来授予本地治理权。

来源状态的失效通过 HTTP 200 加相应 false 标志表达。端点不存在、客户端凭据错误、网络超时、错误回包或服务失败属于身份服务不可用，应返回工作台 503，不应伪装成成员退社。兑换阶段仅 HTTP 400 且 JSON 为 `{"error":"INVALID_CODE"}` 被明确解释为无效代码；其他 HTTP 错误按上游不可用处理。任何异常都不得发会话。

## 工作台提供的基础接口

| 接口 | 用途 | 约束 |
| --- | --- | --- |
| GET /api/health | 进程健康 | 不表示身份提供方可用或数据库已迁移 |
| GET /api/auth/status | 接入配置状态 | configured 仅表示配置完整，不表示上游已联通 |
| POST /api/auth/login | 创建登录尝试并返回 authorization_url | 校验固定 Origin，生成浏览器 cookie、state 和 PKCE verifier |
| GET /api/auth/callback | 后端兑换代码并建立独立会话 | 浏览器 cookie 和 state 同时匹配、未过期、未消费；不能仅凭代码登录 |
| GET /api/auth/me | actor、admission、permissions 和 csrf_token | 逐请求复核中央与本地资格 |
| POST /api/auth/logout | 撤销工作台本地会话 | Origin 加 X-CSRF-Token；即使上游不可用也可撤销自己的会话 |
| GET /api/workspaces | 可见工作区及本地角色 | 以账号成员关系筛选，并排除人员级否决 |
| GET /api/admin/overview | 工作台治理元数据 | 本地 governance:view，不授正文权限 |

业务错误统一为 `{"error":{"code":"...","message":"..."}}`。401 表示会话无效；403 表示明确资格或业务权限不足；503 表示上游未配置或暂时不可用。前端不能把 503 解释为成功、空名单或永久退出。

回调成功 302 到工作台根路径；失败 302 到 `/login?error=<受控错误码>`。一次性 code 不进入前端状态或 localStorage。反向代理与访问日志必须避免记录回调查询参数，响应设置 no-store 和 no-referrer。深链接回跳由前端保存经过白名单限制的本站路径。

## 管理权的初次开通

首次登录仅创建普通 Account 映射，不创建治理授权。经有效登录的账号可由受控的本地管理命令明确授予或撤销 governance:view，必须填写原因并留审计。当前只是只读治理概览；后续写入管理动作要单独定义权限并校验 CSRF。

禁止将训练营 super_admin 自动翻译为工作台治理者。新账号即使映射到同一个 Person，也不自动继承其他账号的管理授权；人员级禁用与工作区否决则必须覆盖该人的所有账号。

## 联调验收

核验两端固定回调和来源名称、错误的 client/audience/issuer、PKCE 失败、重复代码、其他浏览器偷用回调、代码超时、退社、自然到期、全局封禁、身份归并、上游中断及恢复、工作台本地撤权。来源方接口没有完成这些场景前，不能将 configured 状态描述为真实 SSO 已上线。
