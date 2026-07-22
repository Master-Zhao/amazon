# 实体验收样例

这是一个只读、离线的静态页面，用于展示当前 PoC 中单个 Keyword 实体及其竞价优化结果。

启动：

```powershell
python -m http.server 8765 --directory demo
```

然后访问 `http://127.0.0.1:8765/`。

页面中的数据来自 `examples/high-acos-keyword.json` 对应的合成场景。页面不会调用 Amazon Ads API，不实现正式审批，也不会产生生产写入。
