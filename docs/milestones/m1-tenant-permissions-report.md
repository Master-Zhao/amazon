# M1 Tenant、Store、Profile 与权限报告

## 1. 目标

实现全局 User 之上的 Tenant/Team、店铺站点/Profile 层级、功能 RBAC、User/Team 数据授权合并、四级上下文 API 与前端选择器。

## 2. 文件、依赖与迁移

- 新增 `apps.tenants`、`apps.stores`、`apps.permissions` 的 Model、Service、Selector、API、seed 和测试。
- 新增前端 `tenant-context` 与 `system` 基础页面；Axios 自动附加当前 `X-Tenant-ID`。
- 无第三方依赖变化。
- 新迁移：`tenants.0001_initial`、`stores.0001_initial`、`permissions.0001_initial`、`permissions.0002_seed_permissions`；未修改既有迁移。

## 3. API 与页面

- `/api/v1/context/tenants`
- `/api/v1/context/tenants/{tenantId}/stores`
- `/api/v1/context/tenants/{tenantId}/stores/{storeId}/marketplaces`
- `/api/v1/context/tenants/{tenantId}/store-marketplaces/{id}/profiles`
- 权限目录、角色列表/创建/分配、User Store/Profile 授权 API。
- 页面：卖家空间四级选择、角色与权限基础管理。

## 4. 验证

- SQLite 从既有 Phase 2A 数据库升级执行 4 个新迁移成功；Django check 0 issues；`makemigrations --check` 无差异。
- 后端：62 passed、0 failed、25 warnings；重点覆盖 Owner/Admin、个人 Tenant 无 Team、直接/Team Store 并集、Profile 最高等级、无效 Membership、跨 Tenant 404、范围内缺功能 403、只允许固定权限码和授权原子性。
- OpenAPI 生成/校验无 warning/error；TypeScript 类型重新生成。
- 前端：9 files / 31 tests passed；lint、typecheck、production build 通过（108 modules）。
- local/test/prod 三套 Compose 静态配置检查通过；当前沙箱未取得 Docker daemon 连接，M1 未执行容器 MySQL 测试和运行态浏览器 E2E，保留到后续最终验收。

## 5. 契约、风险、启动和演示

认证契约不变；新增上下文和权限路径。真实 Amazon Profile 结构尚未用真实账号验证，但 D-101 基数已按主规格实现。可通过 `seed_demo_context` 创建虚构 PERSONAL Tenant、美国店铺/站点/Profile，然后登录并完成四级选择。下一里程碑 M2 实现广告产品与三类报表异步导入。
