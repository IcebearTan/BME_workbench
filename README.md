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

## 任职履历（本地开发，2026-10-14）

工作台新增“任职履历”（`/work/appointments`），支持按人员、年份查看任期、资料来源和变更日志。训练营管理端“社团职务”的任职档案支持历史补录；换职/连任与信息纠错显式分开。已结束的历史记录不会激活账号或授予工作区权限。

数据库须显式升级：训练营迁移 79（默认仅显示计划，执行时才传 `--apply`），工作台升级到 Alembic `0003`。本轮先在隔离数据库验证，再备份并升级本地开发库；本地训练营22条任职原记录保留，缺少真实事件的登记时间继续留空。生产未修改。部署时先升级两侧 schema，再按 deploy/README.md 的交接顺序发布工作台后端、训练营后端及前端。具体字段与接口见架构文档及身份契约。

本次定向检查入口：工作台 backend 的 `tests/test_appointment_history.py`、frontend 的 `e2e/appointment-history.spec.js`；来源方 `scripts/test_appointment_history.py`、`scripts/test_appointment_history_mysql.py --run`（仅回环地址的临时 MySQL 库）；管理端 `admin.spec.js` 的任职档案/调整任职用例。按用户要求不扩大后续回归范围。

最终定向验收：来源任职12项、SSO接入7项、工作台履历6项通过；工作台履历4项浏览器用例、管理端相关5项通过。本地 MySQL 隔离迁移及重复升级通过，工作台带存量数据的 SQLite 升级通过；4个受影响 Vue 组件编译通过。浏览器使用模拟接口，不能替代生产真实登录联调。

## 多组小组任职（2026-10-14，待部署）

新增“工作台 → 小组任职管理”，一人可任职多个组，一组可有多名分管核心。认证姓名匹配、工作台应用准入和本地小组授权分别校验；登记、换角色和结束均保留期间记录，也进入年度履历。正式社长/副社长等职务及原两槽投影保持兼容，不把教学或商城身份当成小组管理权。

数据库变更为训练营迁移80及工作台0004。本地开发库已显式升级，生产未修改；按用户要求先推送交接，由其他模型部署后再继续正式名单录入。受保护名单文件及预览命令见 deploy/README.md，文件没有提交到 Git。

定向验证：工作台组织及履历15项后端、训练营SSO9项、组织管理2项浏览器用例通过；年度履历的相关浏览器用例此前检查通过。新增Vue及受影响外壳/履历组件编译通过，迁移80在本地临时MySQL库重复执行通过，本地0004升级通过。没有运行本轮全量回归。

## 轻量创建与跨组协作（2026-10-15，已部署）

创建任务仅需标题与工作区，负责人、截止时间及验收配置改在详情“事项设置”补齐；话题仍可直接发布。详情新增协作区，支持按多个小组筛选并批量邀请成员，以及持续查看跨组交付、接单结果与固定版本附件。任务设置、邀请和下载仍受事项级权限、人员否决及版本校验约束。

本轮不改数据库结构，应用版本 `fcfbe19` 已发布到现有 `/workbench/` 入口。按用户要求仅运行相关后端与浏览器用例及发布验收，未运行全量回归。流程、权限和发布记录见 [跨组协作方案](docs/CROSS-GROUP-COLLABORATION-2026-10-15.md)。

## Git 与后续迁移

默认分支为 `main`，远端仓库为 https://github.com/IcebearTan/BME_workbench 。配套训练营改动位于两个原项目的 feature/workbench-extraction 分支。

完整迁移范围和保留行为见 `docs/MIGRATION.md`。本地建立仓库不代表现有线上工作台已搬迁，也不会修改旧项目的发布配置。
