# 部署边界

生产已于 2026年10月13日部署，详见 docs/DEPLOYMENT-2026-10-13.md。工作台前端独立构建，后端独立进程、独立 MySQL 数据库；不复用训练营或商城的账号登录密钥与数据库凭据。

生产至少配置 WORKBENCH_ENV=production、随机 WORKBENCH_SECRET_KEY、独立 WORKBENCH_DATABASE_URL 和 HTTPS WORKBENCH_PUBLIC_ORIGIN。先完成显式数据库迁移，再启动后端。客户端密钥从进程环境或受保护配置注入，不入仓库。

使用后端 wsgi:app 启动服务。Gunicorn 不自动读取 .env，生产由进程管理器注入环境。监听 127.0.0.1:5003，并在同一个公开 origin 提供前端与 /api。PUBLIC_ORIGIN 必须与浏览器 origin 精确相同。示例只适用于独立域名根路径；若改为子路径，需要同步调整路由、cookie、回调和代理规则。

反向代理及应用访问日志不得记录认证回调的 code 或 state 查询参数。示例日志使用 $uri，配置应用服务器日志时同样只记录路径。配置完整不代表训练营端点可用，上线前按 docs/IDENTITY-CONTRACT.md 联调。

本次 IP 部署使用 nginx-lan.conf.example 和两个 systemd 单元，公开入口经既有 8080 网关转发独立 8083 服务。需要显式设置 WORKBENCH_LAN_HTTP=true、WORKBENCH_BASE_PATH=/workbench，并以认证 Redis 保存跨进程限流状态。HTTP 不加密；后台客户端凭据的 HTTP 交换只允许回环地址。

基本运维：systemctl status bme-workbench bme-workbench-worker；日志位于 /var/log/bme-workbench。不要使用旧 Supervisor 的 reread 作为本应用发布步骤。

已完成服务器隔离 MySQL 迁移、任务和文件流程验证及正式工作数据迁移；没有模拟真实多人并发负载或执行整机恢复演练。用户本人密码登录后的实际使用验收不由测试适配器替代。
