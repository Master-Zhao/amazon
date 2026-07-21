## 变更摘要


## 变更类型

- [ ] 业务逻辑
- [ ] 测试或评估
- [ ] CI/CD 或工程治理
- [ ] 文档

## 测试证据

请给出命令、结果及对应的脱敏证据路径。

## 安全影响


## 文档影响


## 提交前检查

- [ ] 未提交 API Key、Token、Authorization 或 `.env`
- [ ] `python -m pytest -q` 已通过
- [ ] Fake 评估已通过
- [ ] `real_model_used=false`
- [ ] `production_write_violation_count=0`
- [ ] 未弱化 Runtime Validator
- [ ] 未扩大 Reasoner 权限
- [ ] 未绕过人工审批
- [ ] 未增加生产写入能力
- [ ] Agent revision 与 Transport retry 仍然分离
- [ ] 新增场景具有固定评估案例
- [ ] 文档已按需更新
