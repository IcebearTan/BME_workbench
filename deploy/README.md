# 部署边界

此目录仅包含部署参考，没有操作现有服务器。工作台前端独立构建，后端独立进程、独立 MySQL 数据库；不复用训练营或商城的密钥与数据库凭据。

生产至少配置 WORKBENCH_ENV=production、随机 WORKBENCH_SECRET_KEY、独立 WORKBENCH_DATABASE_URL 和 HTTPS WORKBENCH_PUBLIC_ORIGIN。先完成显式数据库迁移，再启动后端。客户端密钥从进程环境或受保护配置注入，不入仓库。

使用后端 wsgi:app 启动服务。Gunicorn 不自动读取 .env，生产由进程管理器注入环境。监听 127.0.0.1:5003，并在同一个公开 origin 提供前端与 /api。PUBLIC_ORIGIN 必须与浏览器 origin 精确相同。示例只适用于独立域名根路径；若改为子路径，需要同步调整路由、cookie、回调和代理规则。

反向代理及应用访问日志不得记录认证回调的 code 或 state 查询参数。示例日志使用 $uri，配置应用服务器日志时同样只记录路径。配置完整不代表训练营端点可用，上线前按 docs/IDENTITY-CONTRACT.md 联调。

当前数据库迁移和隔离测试覆盖基础身份模型，不代表已经完成真实 MySQL 并发、生产恢复演练或原工作台业务数据迁移。
