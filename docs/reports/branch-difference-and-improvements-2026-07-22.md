# 《Amazon Ads Agent 仓库分支差异与最新版改进建议报告》

> 基于全部远程分支、真实 Git 历史、代码、配置、干净环境测试、离线评估与安全审计结果

## 文档信息与分析日期

| 字段 | 内容 |
|---|---|
| 仓库 | https://github.com/Master-Zhao/amazon |
| 分析日期 | 2026-07-22（Asia/Shanghai） |
| 分析对象 | origin/main、origin/agent-poc-import、origin/feature/multi-provider-langgraph-security-audit |
| 最新分支 | feature/multi-provider-langgraph-security-audit |
| 最新 HEAD | b63da7152af13fb4bd386669a93669ef008741fc |
| 分析环境 | Windows，Python 3.11.9（隔离验证环境） |
| 结论标记 | 【已验证】代码或命令直接证明；【推断】根据结构和行为作出的合理判断；【未验证】受凭据、网络、费用或外部系统限制 |

## 执行摘要

【已验证】远程仓库共有三个实质分支。main 是独立历史的文档与汇报分支；agent-poc-import 是可运行的离线 PoC 基线；feature/multi-provider-langgraph-security-audit 从 agent-poc-import 直接前进 1 个提交，新增 MaaS Transport、LangGraph 工作流、安全审计和静态 Demo。最新分支由远程 HEAD 的提交时间确定，其提交时间为 2026-07-22 18:30:59 +0800，不是按名称推断。

【已验证】最新版相对 PoC 基线涉及 50 个文件，新增 38 个路径、修改 12 个路径、删除 0 个路径，Git 统计为 6711 行新增、254 行删除。main 与两个代码分支均无共同祖先，不能使用三点 diff 解释继承关系；快照比较显示 main 仅与代码分支共享 README.md 路径，内容也不同。

【已验证】【P0】最新版直接执行 from langgraph.graph import END, StateGraph，但 pyproject.toml 未声明 langgraph。干净安装 python -m pip install -e ".[test]" 虽成功，随后 LangGraph 导入失败，pytest 在收集阶段以 ModuleNotFoundError 中断。仅在临时环境补装 langgraph 1.2.9 并指定可写 pytest 临时目录后，最新版才达到 703 passed。

【已验证】【P0】最新版 README 未随代码更新：仍声明“未接入 LangGraph”“没有前端”“565 passed”，而最新版实际包含 LangGraph、demo/ 和 703 个可通过测试；README 还标注 2026-07-20 的验证日期。CI 同样只安装声明依赖，因此当前 feature 分支按其自身配置不能完成测试收集。

【已验证】agent-poc-import 在干净 Python 3.11 环境中为 565 passed；两个代码分支的固定 Fake 离线评估均为 12/12 passed、real_model_used=false、production_write_violation_count=0。该结果只证明离线固定合同和安全边界，不证明真实模型质量。

【已验证】最新版安全审计 CLI 以正确参数运行后生成 44 条结果：35 compliant、9 non-compliant，其中 critical 3、high 5、medium 1，进程退出码为 1。但多个 critical/high 结果来自审计模块扫描自身规则描述和正则，存在永久自匹配；传入空自定义 RuleRegistry 后仍产生 44 条结果，证明 Registry 没有控制执行逻辑。因此不能直接把“9 个问题”当成可信的项目安全结论。

【已验证】九场景双工作流语义 parity 探针全部一致，覆盖状态、输出字段、建议值、计划版本、重试次数、Failure Analysis、Manual Intervention Package、审计事件序列和 production_write_called。动态时间戳与随机事件 ID 被排除。该探针是本次审计底稿，仓库现有测试并未做两套工作流的直接交叉断言。

综合建议：当前 feature 分支不应直接合并或发布。必须先修复 P0 的依赖与文档/CI 问题，再处理 Provider 路由、SSRF/重定向、身份建模、HTTP 重试与安全审计可信度等 P1 项。结论中不包含真实 Amazon Ads API、生产写入、正式 Approval Service 或真实模型质量通过的声明。

## 目录

1. 分析范围和方法
2. 分支清单及提交信息
3. 分支关系和提交历史
4. 分支定位说明
5. 目录和文件差异
6. 功能与架构差异矩阵
7. 依赖与配置差异
8. 测试、评估和审计结果
9. 最新分支新增、删除和修改能力
10. 双工作流一致性专项验证
11. Provider 路由、身份与 HTTP Transport 审查
12. 安全审计模块自身质量
13. Demo 审查
14. 文档与代码不一致
15. 最新版风险清单
16. P0～P3 改进建议
17. 推荐实施路线图
18. 合并与发布建议
19. 结论
20. 附录：命令、SHA 与证据索引

## 1. 分析范围和方法

本次分析以更新后的远程引用为准，执行了 git fetch --all --prune、git branch -r 和全历史 git log。对有共同祖先的 agent-poc-import 与 feature 分支，使用 merge-base、三点 diff、name-status、numstat 和分支独有提交日志；对与 main 无共同祖先的比较，分别导出远程提交快照，并按 Git blob 路径与内容哈希比较。

代码审计覆盖 .github、config、demo、docs、evaluation、examples、prompts、schemas、src、tests、.env.example、README.md、pyproject.toml 与 AGENTS.md。比较时排除了虚拟环境、缓存、临时文件、构建产物、editable 安装生成的 egg-info、evaluation/results 和本次安全审计生成的 reports/audit-*。

【已验证】每个可运行代码分支建立独立 Python 3.11.9 虚拟环境。先记录原始声明依赖下的安装、导入、pytest、离线评估与审计结果；在最新版原始失败后，才于临时环境额外安装 LangGraph。未修改任何业务代码。

【未验证】真实模型调用、华为云或其他厂商账户认证、Amazon Ads API、生产写入、正式 Approval Service、真实浏览器端到端交互、Linux/macOS 运行结果均未执行。原因是仓库无相应生产接入证据，且真实模型调用需要外部凭据、显式确认并可能产生费用。

## 2. 分支清单及提交信息

| 远程分支 | HEAD SHA | 最后提交时间 | 作者 | 提交数 | 根提交 | 定位 |
|---|---|---|---|---:|---|---|
| origin/main | a2f409654e417e9d22379e04086b5ddf90ee428c | 2026-07-21 10:33:03 +0800 | Master-Zhao | 2 | 64d4dbad1afece71194bba58441937b4405a3fd8 | 独立历史的文档、日报和汇报材料分支 |
| origin/agent-poc-import | 57fbbf0a6145480a4d778f7a52747855457a4283 | 2026-07-21 10:44:35 +0800 | Master-Zhao | 16 | 0a99fbbe2f5501f588f125724f57f2e647046481 | 基础可运行离线 PoC 与交付基线 |
| origin/feature/multi-provider-langgraph-security-audit | b63da7152af13fb4bd386669a93669ef008741fc | 2026-07-22 18:30:59 +0800 | Nuility | 17 | 0a99fbbe2f5501f588f125724f57f2e647046481 | 功能开发分支；新增多 Provider、LangGraph、安全审计和 Demo |

最新分支判断依据是三个远程 HEAD Commit 的提交时间。feature/multi-provider-langgraph-security-audit 比 agent-poc-import 晚约 31 小时 46 分钟，比 main 晚约 32 小时。

## 3. 分支关系和提交历史

~~~
历史 A（独立文档历史）
64d4dba  first commit
   └─ 70cad47  docs: add GitHub repository overview
       └─ a2f4096  origin/main

历史 B（代码 PoC 历史）
0a99fbb  feat: initialize amazon ads agent poc
   └─ ... 14 个中间提交
       └─ 57fbbf0  origin/agent-poc-import / v0.1.0-offline-poc
           └─ b63da71  origin/feature/multi-provider-langgraph-security-audit
~~~

| 分支对 | 共同祖先 | ahead/behind（左/右独有提交） | 是否独立历史 | 解释 |
|---|---|---|---|---|
| main vs agent-poc-import | 无 | 2 / 16 | 是 | 不能用 main...agent-poc-import 解释继承；须比较快照 |
| main vs feature | 无 | 2 / 17 | 是 | 不能用 main...feature 解释继承；须比较快照 |
| agent-poc-import vs feature | 57fbbf0a6145480a4d778f7a52747855457a4283 | 0 / 1 | 否 | feature 是 PoC 基线的直接后继，领先 1 个提交 |

main 中的 amazon-ads-agent-poc 是一个 Git gitlink，指向 d8d7ce7e339224970123248d117ebbaa9c0a8d3a，而不是当前 agent-poc-import HEAD 57fbbf0。该 gitlink 形成内容引用，但不构成 main 与代码分支的 Git 祖先关系；其指针也落后于 PoC 分支末端 4 个提交。

## 4. 分支定位说明

### 4.1 main

【已验证】仅 2 个提交，主要包含工程规范、场景与痛点材料、日报、发言稿以及文档生成中间产物。无 pyproject.toml、src、tests、evaluation、schemas、config 或可安装 Python 包。定位是项目资料汇总和汇报分支，不是可运行软件交付分支。

### 4.2 agent-poc-import

【已验证】包含可安装的 src 布局、JSON Schema、版本化规则配置、Prompts、5 个合成示例、12 个固定评估案例和 32 个测试文件。实现确定性指标、Evidence Gate、Candidate Engine、Stub/Fake/OpenAI-compatible Transport、严格结构化输出、Runtime Validator、有限自动修订、Manual Intervention、dry-run Preflight、HITL 停点及内存审计事件。定位是基础可运行的离线 PoC 与 v0.1.0 交付基线。

### 4.3 feature/multi-provider-langgraph-security-audit

【已验证】从 PoC 基线直接增加 1 个功能提交，代码面新增 MaaS Transport、Provider 路由、Provider 身份字段、共享 HTTP 基类、LangGraph StateGraph、44 规则安全审计模块与静态 Web Demo；文档面新增 Level-3 测试产品规格和技术文档/日志规范。其性质是尚未完成依赖、文档和发布门禁收口的功能开发分支，不应按已发布交付分支理解。

## 5. 目录和文件差异

| 路径/文件 | main | agent-poc-import | 最新 feature | 差异说明 |
|---|---|---|---|---|
| .github | 无 | 6 个文件 | 同基线 | 治理模板与 CI 仅存在代码历史 |
| config | 无 | 1 | 1 | 版本化 PoC 规则未变 |
| demo | 无 | 无 | 4 | 新增静态 HTML/CSS/JS 演示 |
| docs | 5 个业务/规范文档 | 24 | 26 | feature 新增 2 份长文档 |
| evaluation | 无 | 39 | 39 | 12 案例框架保留，2 个实现文件修改 |
| examples | 无 | 5 | 5 | 合成示例不变 |
| prompts | 无 | 3 | 3 | 正式 Prompt 不变 |
| schemas | 无 | 6 | 6 | Schema 不变 |
| src | 无 | 32 | 52 | 新增 LangGraph、HTTP 抽取、MaaS、安全审计 |
| tests | 无 | 32 | 44 | 新增 12 个测试文件并修改 4 个测试文件 |
| .env.example | 无 | 基础 Provider 配置 | 增加 LLM_PROVIDER_NAME 与 GLM 示例 | 默认仍为 Stub |
| README.md | 文档分支说明 | PoC 说明 | 与基线内容相同 | 未描述 feature 新能力，且与实现冲突 |
| pyproject.toml | 无 | jsonschema、PyYAML、pytest | 与基线完全相同 | 缺少 LangGraph 声明 |
| AGENTS.md | 无 | PoC 安全约束 | 同基线 | 明确禁止真实 Amazon Ads API 和生产 Adapter |

基于 Git 对象而不是工作区生成物的定量比较：

| 比较 | 左侧 blob 文件 | 右侧 blob 文件 | 同路径 | 同内容 | 同路径不同内容 | 仅左侧 | 仅右侧 |
|---|---:|---:|---:|---:|---:|---:|---:|
| main vs agent-poc-import | 14 | 153 | 1 | 0 | 1 | 13 | 152 |
| main vs feature | 14 | 191 | 1 | 0 | 1 | 13 | 190 |
| agent-poc-import vs feature | 153 | 191 | 153 | 141 | 12 | 0 | 38 |

## 6. 功能与架构差异矩阵

| 能力 | main | agent-poc-import | 最新 feature |
|---|---|---|---|
| 确定性 Decimal 指标计算 | 仅文档 | 已实现并测试 | 保留 |
| Evidence Gate | 仅文档 | 已实现并测试 | 保留 |
| Candidate Engine | 仅文档 | 已实现并测试 | 保留 |
| Reasoner Stub | 无可运行代码 | 已实现，离线默认 | 保留；但 provider_name 默认值建模有误 |
| Fake Transport | 无 | 已实现，测试/评估使用 | 保留 |
| OpenAI-compatible Transport | 文档声明 | 已实现，默认关闭 | 抽取共享 BaseHTTPTransport |
| 华为云 ModelArts MaaS Transport | 无 | 无 | 新增 MaaSHTTPTransport 与适配器 |
| Provider 路由 | 无 | 无 | 新增，但主机名使用子串匹配 |
| Provider 身份 | 无 | 内部 stub/llm | 新增 provider_name，但协议、厂商与模式混合 |
| Prompt 与结构化输出 | 文档 | 3 个 Prompt、独立 Schema、严格 JSON | 保留 |
| Runtime Validator | 文档 | 已实现最终确定性边界 | 两套工作流复用 |
| 自动修订 | 文档 | 最多 3 次、同错 2 次停止 | 两套工作流保留 |
| Manual Intervention | 文档 | Schema-valid 包与终态 | 两套工作流保留 |
| dry-run Preflight | 文档 | 通过后停在 waiting_for_approval | 两套工作流保留 |
| Human-in-the-loop | 设计说明 | 状态停点，无正式审批服务 | 保留；Demo 按钮不是审批 |
| 审计事件 | 文档 | 内存追加式事件 | 保留；新增项目安全审计模块 |
| LangGraph 工作流 | 声明未接入 | 未接入 | 新增 600 行 StateGraph 替代实现 |
| 静态 Web Demo | 无 | 无 | 新增硬编码只读页面 |
| 离线评估 | 无 | 12 个固定 Fake 案例 | 保留，12/12 |
| 真实模型评估入口 | 无 | 有显式双确认入口，未执行 | 增加 MaaS 路由，仍未执行质量验收 |
| Amazon Ads API/生产写入 | 无 | 未实现 | 未实现 |

## 7. 依赖与配置差异

| 依赖/配置 | 代码使用 | agent-poc-import 声明 | 最新 feature 声明 | 结论 |
|---|---|---|---|---|
| jsonschema | Schema 校验 | 必需依赖 | 必需依赖 | 完整 |
| PyYAML | 规则和审计配置 | 必需依赖 | 必需依赖 | 完整 |
| pytest | 测试 | test optional | test optional | 完整 |
| langgraph | langgraph_workflow.py:13 | 不使用 | 未声明 | 【P0】缺失；破坏导入、测试收集和 CI |
| LLM_PROVIDER_NAME | 不适用 | 无 | .env.example 新增，默认 glm | 默认值会污染 Stub 身份 |
| CI 安装命令 | pip install -e ".[test]" | 可用 | 不会安装 LangGraph | feature CI 必然在测试收集失败 |

第三方 import 静态审计显示最新版新增的唯一未声明运行时第三方模块是 langgraph。是否将其设为必需依赖还是 optional dependency，需要由对外承诺决定：若 LangGraph 是 feature 的核心交付能力，应列入必需依赖；若仅为可选实验，应声明 langgraph extra，并使模块延迟导入、错误信息清晰、相关测试按 extra 分组。当前“代码强导入、测试强收集、依赖不声明”的组合不可接受。

## 8. 测试、评估和审计结果

| 分支/环境 | 安装 | 包导入 | LangGraph 导入 | pytest | 固定离线评估 | 安全审计 |
|---|---|---|---|---|---|---|
| main | 不适用：无 pyproject | 不适用 | 不适用 | 不适用 | 不适用 | 不适用 |
| agent-poc-import 原始声明依赖 | 成功 | 成功 | 模块不存在，符合基线定位 | 565 passed，97.59s | 12/12 passed，real_model_used=false | 模块不存在 |
| feature 原始声明依赖 | 成功 | 成功 | ModuleNotFoundError: langgraph | 收集阶段 1 error，0 个测试执行 | 12/12 passed，real_model_used=false | 正确参数下运行，35/44 compliant，退出码 1 |
| feature 临时补装 langgraph 1.2.9 | 额外安装成功 | 成功 | 成功 | 首跑 697 passed + 6 环境权限 error；指定可写 basetemp 后 703 passed，71.73s | 未重复，原始评估已通过 | 结果不受 LangGraph 补装影响 |

两个代码分支的高 ACoS CLI 均实际返回 exit=0、current_status=waiting_for_approval、production_write_called=false。

基础 PoC 测试完整通过；最新版在仓库声明的原始安装方式下没有完整通过。703 passed 只代表“人为补齐缺失依赖并修正本机 pytest 临时目录权限”后的代码结果，不能替代原始安装失败事实。第一次补装后出现的 6 个 error 均为 Windows 默认 pytest 临时目录 PermissionError；将 --basetemp 指向本任务可写目录后消失。

安全审计命令实际接口为：

~~~
python -m amazon_ads_agent.security_audit --project-path .
~~~

直接使用位置参数会返回 argparse exit=2；正确参数执行后返回 exit=1，并生成 JSON/Markdown 审计报告。

## 9. 最新分支新增、删除和修改能力

【已验证】相对 agent-poc-import 的三点 diff：50 files changed、6711 insertions、254 deletions；新增 38 个路径、修改 12 个路径、删除 0 个路径。

新增能力按模块归类：

- MaaS 与多 Provider：新增 _http_types.py、base_http_transport.py、maas_transport.py、maas_response_adapter.py、transport_router.py，并扩展 config、provider、response_adapter 和评估报告字段。
- LangGraph：新增 600 行 langgraph_workflow.py；把 build_reasoner_input 和 legacy_output 抽到 workflow_shared.py；原 workflow.py 净缩减。
- 安全审计：新增 security_audit 包 12 个模块，声明 44 条规则，提供 CLI、JSON/Markdown 报告。
- Demo：新增 demo/index.html、styles.css、app.js、README.md。
- 文档：新增 Level-3 测试产品规格 621 行与技术文档/日志规范 1044 行。
- 测试：新增 MaaS、Provider 身份、路由、LangGraph 和审计测试。

没有业务能力被显式删除；但 HTTP Transport 重构改变了错误处理和责任分配，需要兼容性回归。README、pyproject.toml 与 CI 未同步，是“代码新增但交付面未完成”的核心信号。

## 10. 双工作流一致性专项验证

本次临时 parity 探针对同一输入分别调用 run_workflow 与 run_langgraph_workflow，比较最终状态、输出 Schema 键、建议值、计划版本、重试次数、Failure Analysis、Manual Intervention Package、审计事件类型序列与 production_write_called。时间戳、随机 audit_event_id 等非业务动态字段被规范化排除。

| 场景 | 原工作流终态 | LangGraph 终态 | 建议值 | plan/retry | 审计事件数 | production_write_called | 语义一致 |
|---|---|---|---|---|---:|---|---|
| 高 ACoS 正常路径 | waiting_for_approval | waiting_for_approval | 1.08 | 1/0 | 10 | false | 是 |
| 数据不足 | completed | completed | 无 | 0/0 | 5 | 不适用 | 是 |
| 无需调整 | completed | completed | 无 | 0/0 | 5 | 不适用 | 是 |
| 第一次非法后修订成功 | waiting_for_approval | waiting_for_approval | 1.08 | 2/1 | 14 | false | 是 |
| 重复非法转人工 | manual_intervention_required | 同左 | 无 | 2/1 | 14 | 不适用；人工包中为 false | 是 |
| Reasoner Transport 失败 | manual_intervention_required | 同左 | 无 | 1/0 | 11 | 不适用；人工包中为 false | 是 |
| Schema 失败 | manual_intervention_required | 同左 | 无 | 1/0 | 13 | 不适用；人工包中为 false | 是 |
| Runtime Validator 失败 | manual_intervention_required | 同左 | 无 | 2/1 | 14 | 不适用；人工包中为 false | 是 |
| Preflight 通过并停待审批 | waiting_for_approval | waiting_for_approval | 1.08 | 1/0 | 10 | false | 是 |

【已验证】九场景均语义一致。【风险】现有 tests/test_workflow.py 与 tests/test_langgraph_workflow.py 是两份近似镜像测试，而非参数化调用两实现并直接比较结果；未来一侧增加字段、改变审计序列或修订策略时，两个测试文件可能分别“通过”但产生逻辑漂移。

【已验证】公开包 __init__ 和 CLI 只导出/调用 run_workflow；LangGraph 无 CLI 选择开关。缺少依赖时也没有友好降级错误，而是在模块导入时直接 ModuleNotFoundError。

## 11. Provider 路由、身份与 HTTP Transport 审查

### 11.1 Provider 路由安全性

transport_router.py:17 使用 _MAAS_HOST in parsed.hostname。实际负向探针结果：

| URL | 当前 is_maas_endpoint | 期望 |
|---|---|---|
| https://api.modelarts-maas.com/v1 | true | true |
| https://api.modelarts-maas.com.example.org/v1 | true | false |
| https://fake-api.modelarts-maas.com/v1 | true | false |
| https://notapi.modelarts-maas.com/v1 | true | false |
| https://sub.api.modelarts-maas.com/v1 | true | 仅在明确允许子域时为 true |

建议使用精确主机名，或 host == allowed / host.endswith("." + allowed) 的边界匹配；更稳妥的是显式 protocol_type/provider_id 配置优先，自动推断只作受控兼容路径。配置校验还应覆盖协议、端口 allow-list、DNS 解析后的私有/环回/链路本地地址、重绑定和重定向后的最终 URL。

_validate_endpoint 仅限制 scheme、凭据嵌入和明文 HTTP。实际探针显示 https://127.0.0.1:8443、https://10.0.0.1、https://169.254.169.254 和 https://localhost:9443 全部允许。UrllibHTTPClient 使用默认 urlopen，未禁用或重新校验重定向。因此存在 SSRF、元数据地址访问和重定向绕过校验的风险。

### 11.2 Provider 身份建模

| 概念 | 当前字段/值 | 问题 | 建议 |
|---|---|---|---|
| 内部执行模式 | provider=stub/llm | 与厂商身份混在同一配置类 | execution_mode 单独建模 |
| 协议类型 | 由 Endpoint 自动选择 OpenAI-compatible/MaaS | 缺少显式字段 | protocol_type=openai_chat_completions/modelarts_maas |
| 实际厂商 | provider_name 默认 glm 或 maas | 非 GLM 的兼容 Endpoint 也被标 glm | vendor_id 明确配置，默认 unknown |
| 模型名称 | model | 基本清晰 | 保留，并与 vendor/protocol 分离 |
| Endpoint | base_url | 既参与路由又可能进入报告 | 使用安全规范化 endpoint_id/host |

实际探针：空环境的 Stub 配置 provider_name=glm；任意 https://vendor.example/v1 的 OpenAI-compatible 配置在未显式指定时也推断为 glm。显式 provider_name 可以与由 URL 选择的 MaaS 协议冲突，代码仍会建立 MaaS Transport 并把错误/报告标成自定义名称。

兼容迁移建议：新增 execution_mode、protocol_type、vendor_id、model_id、endpoint_id；保留 provider/provider_name 为只读兼容属性一个版本；迁移时记录 deprecation audit event；显式新字段优先，旧值只在无歧义时映射，否则 fail closed。

### 11.3 HTTP Transport

【已验证】BaseHTTPTransport 保留了预算、Endpoint 校验、状态码映射、请求体构造和响应适配的共享逻辑；现有相关测试在补依赖后通过。

主要问题：

- actual_request_count 和列表更新无锁；共享 Transport 被多线程使用时，预算检查与递增不是原子的。
- urllib HTTPError 被转成空 body，丢失服务端错误体和可能的 Request ID；无法安全提取限流诊断。
- UrllibHTTPClient 的超时和网络错误 provider 固定为 openai_compatible，即使由 MaaS Transport 调用。
- LLMReasoner 重试没有指数退避、抖动、Retry-After 或总时限；429、5xx、超时会立即重试。
- 初始 Endpoint 校验后没有重定向最终 URL 校验、DNS 私网阻断或端口 allow-list。
- Authorization Header 由 Transport 构造；当前代码未主动记录它，但缺少防止底层异常、调试日志或代理泄露的系统性测试。
- Usage 只接受 prompt_tokens/completion_tokens/total_tokens 的非空子集；厂商扩展字段会被整体拒绝。
- HTTP 成功响应缺少服务端 Request ID 时生成 local-*，但响应模型没有 request_id_source，日志无法区分真实 ID 与本地替代 ID。

## 12. 安全审计模块自身质量

### 12.1 CLI 实际结果

| 指标 | 实际值 |
|---|---:|
| Total Rules | 44 |
| Compliant | 35 |
| Non-Compliant | 9 |
| Critical | 3 |
| High | 5 |
| Medium | 1 |
| Low | 0 |
| CLI exit | 1 |

### 12.2 结果可信度问题

| 问题 | 代码/命令证据 | 影响 |
|---|---|---|
| Registry 不控制执行 | AuditRunner 保存 self.registry，但 run_* 直接调用四个 Checker；空 Registry 仍输出 44 findings | 自定义规则无法生效，禁用规则也无效 |
| 审计自扫描 | source_scanner 扫描整个 src，包括 security_audit 自身 | 规则描述、正则和实现文本永久触发 |
| 禁止 Production Adapter 自匹配 | _PRODUCTION_ADAPTER_RE 命中自身规则与函数名，共 9 处 | 产生 critical 伪告警 |
| eval/exec 自匹配 | 正则命中 rules.py 的描述字符串 | 产生 critical 伪告警 |
| hardcoded secret 自匹配 | AKIA 模式命中规则定义文字 | 产生 critical 伪告警，不代表真实密钥 |
| float 规则范围过宽 | 扫描全部 src 文本并命中规则描述/实现 | 与“业务计算禁 float”目标不一致 |
| HTTPS 检查路径过时 | 只在 http_transport.py 搜 _validate_endpoint，实际函数已移到 _http_types.py | 报告实现存在为缺失 |
| .env.example 保留未验证 | has_env_example 被计算但从未参与合规条件 | .env.example 被忽略仍可能判通过 |
| 双重确认只查字符串 | has_cli_confirm 被计算但没有用于返回条件；发现环境变量字符串即判通过 | 不能证明环境变量与 CLI Flag 都实际控制调用 |
| 解析失败静默 continue | Source、Config、Schema 多处捕获后 continue | 无法读取/解析的关键文件可能被漏审 |

结论：44 条规则目前确实各返回一条 Finding，但这是硬编码 Checker 列表的结果，不是 Registry 驱动的规则执行。应把规则映射到可调用检查器；AST 适合 import、调用和类定义，配置应使用 TOML/YAML/ignore 语义解析，安全边界应增加行为测试。审计模块自身目录、规则测试数据和生成报告应明确排除或标记为 fixture。

## 13. Demo 审查

【已验证】demo 是纯静态 HTML/CSS/JS，页面中的实体、ACoS、候选值、AgentOutput 和审计链全部硬编码；app.js 不 fetch 本地 Agent 输出。按钮“标记样例符合预期”仅修改按钮文字、禁用按钮并显示 2.6 秒 toast，不保存、不提交、不审批。

【风险】页面标题和卡片使用“实体验收”“方案已通过全部安全校验”等字样，虽然 README 和页面下方说明其为只读本地样例，仍可能在截图或脱离上下文演示时被误认为正式审批界面。建议把顶部永久标识改为“静态合成数据演示 / 非审批系统”，按钮改成“关闭演示提示”或“确认已阅读”，避免“通过”语义。

【安全】当前 innerHTML 只写入固定常量，未发现用户输入进入 DOM 的路径，因此不能据此声称存在可利用 XSS；但未来读取 JSON 时必须只用 textContent/DOM 构造，并对 URL、富文本和错误消息做严格处理。

【可访问性】已有 dialog role、aria-modal、aria-labelledby、关闭按钮 label、Escape 关闭和焦点恢复；缺少完整焦点陷阱、背景 inert、初始焦点/Tab 循环行为测试。仓库无 package.json、Playwright/Jest/Vitest/Cypress 或其他前端自动化测试。

改造成只读运行结果工具的建议：

1. Agent CLI 增加显式 --output 文件，将脱敏的协议信封写入本地目录。
2. Demo 只读取用户主动选择的本地 JSON，不启动后端、不接收凭据。
3. 使用 JSON Schema 在浏览器或预处理脚本中验证后再渲染。
4. 每个字段用 textContent，禁止直接 innerHTML 插入运行结果。
5. 永久展示 run_id、生成时间、real_model_used、production_write_called 和“非审批”水印。
6. 增加 Playwright 离线测试、键盘可访问性和恶意字符串 fixture。

## 14. 文档与代码不一致

| README/文档声明 | 代码/命令证据 | 判断 |
|---|---|---|
| LangGraph 未接入；代码未调用 StateGraph | langgraph_workflow.py:13 导入 END/StateGraph，534-575 构建图 | 严重冲突 |
| pyproject 不包含 langgraph、代码也不需要它 | pyproject 确实不含；实际导入失败并阻断 pytest | 前半句事实，后半句冲突，形成 P0 |
| 全量测试 565 passed | feature 补依赖后 703 passed；原始环境收集失败 | 数量和“完整通过”均不成立 |
| 验证日期 2026-07-20 | feature HEAD 为 2026-07-22 | 过期 |
| 没有前端 | feature 新增 demo/ 四个文件 | 冲突；应称静态 Demo，不是正式前端 |
| 仅 OpenAI-compatible Provider | 代码新增 MaaS Transport 与路由 | 功能清单过期 |
| 未描述安全审计 | 新增 44 规则 CLI 与报告器 | 目录和使用说明缺失 |
| 项目结构无 demo、安全审计、LangGraph | Git 快照实际存在 | 目录说明过期 |
| 未接入 Amazon Ads API | 未发现 Adapter、SDK、调用或生产写入 | 一致 |
| 无生产写入、无正式 Approval Service | AGENTS、Preflight、测试和 Demo 均支持该结论 | 一致 |

## 15. 最新版风险清单

| 风险 | 优先级 | 可能性 | 影响 | 当前证据 |
|---|---|---|---|---|
| 声明安装后测试无法收集 | P0 | 必现 | CI、验收和新用户安装失败 | 干净环境 ModuleNotFoundError |
| README/CI 验收结论失真 | P0 | 必现 | 交付误导、错误合并判断 | 565/LangGraph/前端声明冲突 |
| MaaS 域名子串误路由 | P1 | 高 | 协议错选、错误身份、凭据发送到错误端点 | 三个恶意相似域名均返回 true |
| SSRF/重定向/DNS 私网风险 | P1 | 中 | 内网访问、元数据访问、凭据风险 | 私网 HTTPS 地址均被允许 |
| Provider 身份污染 | P1 | 高 | 审计、报告、错误归因不可信 | Stub 和任意兼容端点默认 glm |
| HTTP 重试风暴和诊断丢失 | P1 | 中 | 限流放大、恢复慢、难排障 | 无 backoff/jitter；HTTPError body 丢弃 |
| 安全审计误报/漏报 | P1 | 必现 | 错误安全结论、门禁不可用 | 自匹配、Registry 无效、静默忽略 |
| 双工作流未来漂移 | P1 | 中 | 状态/审计/安全边界不一致 | 600 行复制实现，无直接 parity 测试 |
| Demo 被误认作审批 | P2 | 中 | 演示和验收沟通风险 | “通过”按钮仅前端状态 |
| Request ID 来源不明 | P2 | 中 | 跨系统追踪错误 | local-* 与真实 ID 共用字段 |

## 16. P0～P3 改进建议

| 编号 | 优先级 | 类别 | 问题 | 证据 | 影响 | 建议方案 | 验收标准 | 工作量 | 阻塞合并 |
|---|---|---|---|---|---|---|---|---|---|
| IMP-P0-001 | P0 | 依赖/CI | LangGraph 强导入但未声明 | pyproject.toml 依赖段；langgraph_workflow.py:13；原始 pytest 收集失败 | 安装后功能不可用、CI 失败 | 明确必需或 extra；锁定兼容版本；缺失时给出清晰错误；CI 覆盖最小安装与完整安装 | 全新 Python 3.11/3.12 环境仅按文档安装后，导入和 pytest 均通过 | S | 是 |
| IMP-P0-002 | P0 | 文档/验收 | README 与 feature 实现、测试数、日期、目录和 Provider 冲突 | README:22,27,34,108,170,243；Git 快照和 703 passed | 严重误导验收和发布结论 | 更新 README、目录树、依赖、CLI、Provider、Demo、安全审计；明确 Fake 与真实模型边界；以 CI 产物生成测试数 | README 声明均有可复现命令；CI 校验文档中的测试数/功能标志；审阅无冲突 | S | 是 |
| IMP-P1-001 | P1 | 安全/网络 | 域名子串路由，且 Endpoint 缺少 SSRF、DNS、端口和重定向控制 | transport_router.py:17；私网 URL 探针全部允许 | 错选协议、访问内网或错误端点 | 显式 protocol allow-list；精确域名边界；解析并阻断私网/链路本地；禁用或逐跳校验重定向；限制端口 | 正负域名、IPv4/IPv6、DNS 重绑定、重定向和端口测试全部通过 | M | 是 |
| IMP-P1-002 | P1 | 架构/审计 | execution mode、协议、厂商、模型、Endpoint 混为 provider/provider_name | config.py:51-59,79-80,114-120；Stub=glm 探针 | 日志、错误、报告和路由身份不可信 | 引入 execution_mode/protocol_type/vendor_id/model_id/endpoint_id；兼容属性限期迁移；冲突 fail closed | Stub 为 stub/unknown；任意兼容端点不默认 GLM；显式冲突测试失败关闭 | M | 是 |
| IMP-P1-003 | P1 | HTTP/可靠性 | 预算非线程安全、错误体/Request ID 丢失、Provider 名错误、无退避抖动 | base_http_transport.py:45,76-106；_http_types.py:35-44；llm.py:80-127 | 并发超预算、重试风暴、诊断不足 | 锁或原子预算；安全提取错误码/Request ID；Provider 注入；指数退避+抖动+Retry-After+总时限 | 并发预算、429/5xx/timeout、错误体脱敏和 Provider 归因测试通过 | M | 是 |
| IMP-P1-004 | P1 | 安全审计 | Registry 不驱动执行，字符串规则自匹配、静默忽略解析失败 | runner.py:25-31,58-77；source_scanner.py:14-23,87-232；空 Registry 仍 44 findings | 审计门禁结论错误 | Registry 映射检查器；AST/TOML/YAML/ignore 语义解析；排除自身与 fixtures；读/解析失败产生 error finding | 空 Registry=0；单规则只执行单规则；自身零伪告警；损坏文件明确报错 | L | 是 |
| IMP-P1-005 | P1 | 架构/测试 | 双工作流复制，LangGraph 无 CLI，缺少直接 parity 回归 | cli.py:13,46；langgraph_workflow.py 600 行；两份镜像测试 | 逻辑漂移、功能不可发现 | 共享节点/服务层；CLI 增加 --workflow；把九场景探针固化为参数化 parity 测试；定义单一默认实现 | 九场景逐字段比较；两入口均可用；缺依赖错误清晰；覆盖新增字段 | M | 是 |
| IMP-P2-001 | P2 | Demo/体验 | Demo 完全硬编码，按钮语义类似审批，无前端自动化 | demo/index.html:151-268；app.js:42-49 | 截图误导、无法同步真实输出、可访问性回归 | 本地文件只读加载；非审批永久标识；textContent；Playwright/a11y 测试 | 读取脱敏本地 JSON；恶意文本不执行；键盘流程和非审批提示测试通过 | M | 否 |
| IMP-P2-002 | P2 | 协议/可观测性 | MaaS 适配路径过宽，Usage 过窄，Request ID 来源不明 | maas_response_adapter.py:22-76；response_adapter.py:22-38 | 误接受非合同响应或拒绝扩展字段；追踪混乱 | 按已验证 API 版本建适配器；允许已知 usage 扩展；增加 request_id_source/provider_request_id | 版本化合同 fixture、扩展 usage、无服务端 ID 和错误响应测试通过 | M | 否 |
| IMP-P2-003 | P2 | 分支治理 | main 独立历史且 gitlink 落后，默认分支不是代码交付源 | main gitlink=d8d7ce7；PoC HEAD=57fbbf0；无共同祖先 | 克隆默认分支的用户无法安装，交付关系混乱 | 明确默认分支策略；移除/更新 gitlink；发布 tag 指向代码历史；文档链接到固定 SHA | 新用户从默认分支按 README 可安装；tag/branch/githlink 一致 | M | 否 |
| IMP-P2-004 | P2 | CI/兼容性 | 仅 Python 3.12，未测试声明下限 3.11；依赖无上界/锁定 | pyproject requires >=3.11；CI setup 3.12 | 依赖升级和版本兼容风险 | 3.11/3.12 矩阵；最小/最新依赖测试；生成锁定或约束文件 | 两版本、最小/最新依赖组合通过；供应链审计无阻塞项 | M | 否 |
| IMP-P3-001 | P3 | CLI/文档体验 | 安全审计必须 --project-path，但无 README 使用说明；LangGraph/审计入口不可发现 | audit CLI argparse 实际 exit=2；根 README 无安全审计章节 | 使用成本和误操作 | 增加 console_script、根 README 命令和 exit code 说明；--help 示例 | 全新用户按 README 一次运行成功；help 与文档一致 | S | 否 |

P0 数量：2。P1 数量：5。

## 17. 推荐实施路线图

| 阶段 | 优先级 | 建议时序 | 主要工作 | 退出标准 |
|---|---|---|---|---|
| Gate 0：恢复可安装性 | P0 | 0.5～1 天 | 声明 LangGraph、修 CI、更新 README 和测试数 | 原始安装命令后 703 tests 收集并通过 |
| Gate 1：封闭网络边界 | P1 | 2～4 天 | 显式协议/Provider、域名 allow-list、SSRF/重定向/DNS 控制 | 全部安全负向测试通过 |
| Gate 2：提升 Transport 可靠性 | P1 | 2～3 天 | 线程安全预算、退避抖动、Request ID、错误体脱敏 | 并发、限流、超时和诊断测试通过 |
| Gate 3：让审计可信 | P1 | 3～5 天 | Registry 驱动、AST/配置解析、自扫描隔离、失败可见 | 自定义 Registry 和零伪告警验收通过 |
| Gate 4：收敛工作流 | P1/P2 | 2～4 天 | 共享节点、CLI 选择、九场景 parity 固化 | 两实现语义门禁稳定 |
| Gate 5：演示与发布治理 | P2/P3 | 2～3 天 | 只读动态 Demo、前端测试、默认分支/Tag/文档收口 | 默认分支可交付，Demo 不被误认审批 |

## 18. 合并与发布建议

当前建议：阻止 feature 直接合并到发布分支。

合并前最低门禁：

1. 修复 IMP-P0-001 和 IMP-P0-002。
2. 原始 python -m pip install -e ".[test]" 后，LangGraph 导入与完整 pytest 在 CI 通过。
3. Provider 路由的相似恶意域名、私网地址、重定向和端口负向测试通过。
4. 安全审计不再扫描自身产生 critical 伪告警，自定义 Registry 实际控制执行。
5. 九场景 parity 成为仓库自动测试，而不是一次性审计探针。
6. README 明确：Fake 评估不是真实模型质量验证；没有 Amazon Ads API、生产写入或正式 Approval Service；Demo 不是审批界面。

发布建议：在完成上述门禁后，从代码历史创建新的 release tag；不要以 main 中落后的 gitlink 作为发布证据。真实模型评估应作为单独、显式、有限预算的验收阶段，不得覆盖 Fake 报告；真实 Amazon Ads 集成必须另立项目边界和安全评审。

## 19. 结论

最新版带来了有价值的架构扩展：多协议 Transport、MaaS 适配、LangGraph 图编排、安全审计框架和演示页面，并且在补齐依赖后 703 个测试全部通过；本次九场景探针也证明两套工作流当前语义一致。

但“代码可通过”不等于“分支可交付”。原始依赖声明导致必现的测试收集失败，README/CI 与实现严重不一致，Provider 路由和网络边界存在可复现的误匹配与 SSRF 风险，安全审计又因自匹配和 Registry 无效而不能作为可信门禁。因此当前分支应保持功能开发状态，先完成 2 个 P0 和 5 个 P1 项，再讨论合并与发布。

【未验证】本报告没有执行真实模型调用，没有使用任何 API Key，没有接入或调用 Amazon Ads API，没有执行生产写入，没有验证正式 Approval Service，也没有把静态 Demo 当成真实审批系统。

## 20. 附录

### 20.1 关键命令

~~~
git fetch --all --prune
git branch -r
git log --all --date=iso --pretty=format:"%H|%ad|%an|%D|%s"
git merge-base origin/agent-poc-import origin/feature/multi-provider-langgraph-security-audit
git diff --stat origin/agent-poc-import...origin/feature/multi-provider-langgraph-security-audit
git diff --name-status origin/agent-poc-import...origin/feature/multi-provider-langgraph-security-audit
git diff --numstat origin/agent-poc-import...origin/feature/multi-provider-langgraph-security-audit
git log --oneline origin/agent-poc-import..origin/feature/multi-provider-langgraph-security-audit

py -3.11 -m venv <temporary-environment>
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
python -c "import amazon_ads_agent"
python -c "from amazon_ads_agent.langgraph_workflow import build_graph"
python -m pytest -q
python evaluation/run_evaluation.py
python -m amazon_ads_agent.security_audit --project-path .
~~~

### 20.2 重要 Commit SHA

| 名称 | SHA |
|---|---|
| main HEAD | a2f409654e417e9d22379e04086b5ddf90ee428c |
| agent-poc-import HEAD / feature merge-base | 57fbbf0a6145480a4d778f7a52747855457a4283 |
| feature HEAD | b63da7152af13fb4bd386669a93669ef008741fc |
| main 根提交 | 64d4dbad1afece71194bba58441937b4405a3fd8 |
| 代码历史根提交 | 0a99fbbe2f5501f588f125724f57f2e647046481 |
| main 内 gitlink | d8d7ce7e339224970123248d117ebbaa9c0a8d3a |

### 20.3 证据索引

| 主题 | 主要证据 |
|---|---|
| LangGraph 依赖 | pyproject.toml；src/amazon_ads_agent/langgraph_workflow.py:13；原始导入/pytest 输出 |
| CLI 入口 | src/amazon_ads_agent/cli.py:13,46；src/amazon_ads_agent/__init__.py |
| 路由误匹配 | src/amazon_ads_agent/reasoners/transport_router.py:11-18；五 URL 探针 |
| SSRF/重定向 | reasoners/_http_types.py:27-59；私网 URL 探针 |
| Provider 身份 | reasoners/config.py:47-120；Stub 与 generic endpoint 探针 |
| HTTP 重试/预算 | reasoners/base_http_transport.py:45-117；reasoners/llm.py:80-127 |
| 安全审计可信度 | security_audit/runner.py、registry.py、source_scanner.py；空 Registry 探针；CLI 报告 |
| Demo | demo/index.html:151-268；demo/app.js:32-49；demo/README.md |
| 双工作流 parity | 本次临时 parity_probe.py 输出；tests/test_workflow.py 与 test_langgraph_workflow.py |
| 测试与评估 | 两个 Python 3.11 隔离环境的 pip/pytest/evaluation 命令输出 |

### 20.4 环境限制与未验证事项

- 未提供且未读取任何真实 API Key、Token 或 Authorization Header。
- 未执行真实 OpenAI-compatible、GLM 或华为云 MaaS 网络调用，不能评价认证、配额、延迟、真实响应兼容性和模型质量。
- 仓库没有 Amazon Ads API Adapter 或生产写入代码，因此没有验证 Amazon Ads 接入或生产变更能力。
- 没有正式 Approval Service、数据库、RBAC 或持久化审计后端，无法验证生产级人审闭环。
- Demo 依据源码完成静态审查，未把本地按钮行为视为正式审批；未进行真实浏览器跨浏览器兼容性测试。
- 测试环境为 Windows + Python 3.11.9；Linux、macOS、Python 3.12 及更高版本未在本次本地审计中复跑。
