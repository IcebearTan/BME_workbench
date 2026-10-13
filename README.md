# BME Workbench

独立的 BME 内部工作台。沿用 Vue 3、Vite、Vue Router、Vuex、Element Plus、DewUI 和 Flask、SQLAlchemy、数据库迁移方案，通过训练营身份接入，不依赖积分商城账号。

本仓库现已移植原工作台的事项、话题、任务、跨组交付、附件版本、通知、记录与治理页面。训练营侧的专用 SSO 提供端已实现，工作台不依赖商城账号。新环境默认关闭接入，配置并完成迁移后启用；生产切换情况见 docs/DEPLOYMENT-2026-10-13.md。

## 目录

```text
frontend/       独立 Vue 应用及浏览器契约测试
backend/        Flask 应用、身份适配、数据库迁移及隔离测试
packages/       原平台 DewUI 和设计变量的独立快照
docs/           架构、身份契约及迁移清单
deploy/         生产部署参考
scripts/        本地开发与检查入口
```

所有代码和依赖声明都在本仓库内，不依赖相邻项目目录。UI 基础的来源版本见 `packages/PROVENANCE.md`。

## 本地启动

要求 Node.js 22 或更新版本、pnpm 11.22.0、Python 3.12 和 uv。也可用标准 Python venv 与 pip 安装锁定依赖。

在仓库根目录执行：

```sh
pnpm install --frozen-lockfile
uv venv backend/.venv --python 3.12
uv pip sync --python backend/.venv/bin/python backend/requirements-dev.txt
python3 scripts/init-local.py
pnpm db:upgrade
```

初始化脚本只创建不存在的本地配置并生成随机应用密钥，不输出密钥，不覆盖已有文件，保持身份提供方关闭。配置文件与本地 SQLite 数据库均被 Git 忽略。新环境的迁移是显式步骤，应用启动不会自动创建或改变数据表。

分别启动两个终端：

```sh
pnpm dev:backend
pnpm dev:frontend
```

浏览器访问 `http://127.0.0.1:8083`。前端将 `/api` 代理到本项目的 `127.0.0.1:5003`，不会访问旧训练营的开发数据库或 API。未配置身份接入时，页面应显示未接通状态；这不表示应用无法启动。

## 检查

```sh
pnpm test:backend
pnpm check:no-emoji
pnpm build
pnpm --filter @bme/workbench-web exec playwright install chromium
pnpm test:e2e
```

后端测试使用隔离数据库与测试身份提供方；浏览器测试使用明确的模拟 API 验证界面与权限边界，不连接生产。真实训练营接入、MySQL 并发行为和生产部署需单独联调，不能由这些测试替代。

## 身份边界

- 训练营确认账号、人员身份与社团准入。
- 工作台保存外部账号映射、自己的会话、工作区角色和治理授权。
- 训练营超级管理员不会自动成为工作台管理员；没有本地授权就没有本地管理权限。
- 不复制训练营密码、长效访问令牌或商城票据。
- 上游身份不可用时拒绝受保护请求；明确退社、封禁或身份失效时撤销本地访问。

详见 `docs/ARCHITECTURE.md` 与 `docs/IDENTITY-CONTRACT.md`。

## Git 与后续迁移

默认分支为 `main`，远端仓库为 https://github.com/IcebearTan/BME_workbench 。配套训练营改动位于两个原项目的 feature/workbench-extraction 分支。

完整迁移范围和保留行为见 `docs/MIGRATION.md`。本地建立仓库不代表现有线上工作台已搬迁，也不会修改旧项目的发布配置。
