# 添加权限

在 `apps.permissions.services.PERMISSION_CATALOG` 增加稳定 permission code，
新增数据迁移或运行 `seed_permission_catalog`，再把权限授给系统/自定义 Role。
业务 Service 调用：

```python
authorize(
    user=request.user,
    tenant_id=tenant_id,
    permission_code="module.action",
    profile=profile,
    minimum_profile_level=ProfileAccessLevel.EDIT,
)
```

Store 范围使用 `accessible_store_ids`，Profile 等级使用
`effective_profile_level`；不要在业务 App 复制 Owner/Admin 特判。测试必须覆盖
有效 Membership、功能权限、Store/Profile grant、对象归属、跨范围 404 和范围内
缺动作权限 403。菜单隐藏只是体验层，后端校验不可省略。
