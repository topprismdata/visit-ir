# VisitIR v0 设计草案（Strawman） · 2026-09-06

> 状态：供 GPT 协同评审的靶子。逐条可被推翻，推翻需给出设计与文献依据。

## 0. 边界（先说 NOT）

- **不含**：路线顺序（Layer-2 优化对象，作可选附件 `routes` 挂载）、距离矩阵、优化器内部状态、求解器方言细节；
- **不含**：LLM 调用。LLM 是边界适配器（NL→类型化事件提案），IR 核心确定性可复现；
- **不含**：多区域/多人协同语义（当前单业代单线路）。

## 1. 分层架构（MLIR 式方言枢纽）

```
源方言 (front-ends)              核心方言 (VisitIR)              后端方言 (back-ends)
├─ SRP xlsx 解析器      ──┐                        ┌──  验收器 (四闸 GateReport)
├─ 优化器输出 (days dict) ──┼──→  WorkCalendar       ├──  序列化 plan_ir/v1 (跨机审计)
├─ 历史 JSON (旧审计账)  ──┤      ContractBook      ├──  SP 数学模型 (约束 RHS)
└─ LLM 适配器 (NL 事件)  ──┘      VisitPlan          ├──  ALNS 合法域 (contract_slot_dates)
   │ 只产「事件提案」              └─ 例外账 EventLog  └──  报表/可视化
   └────── IR 校验器裁决，拒绝即报告 ──────┘
```

## 2. 核心结构（v0）

| 结构 | 内容 | 设计来源 |
|---|---|---|
| `WorkCalendar` | 工作日序、星期几槽位、**相位锚 AnchoredCycle**（见 §OQ-1） | ONNX 自包含 |
| `Contract(cadence, phase, effective_from/to)` | 符号层合同规则；effective 区间占位（月中开关店语义缺口） | Pyomo 符号/地面分离 |
| `ContractBook` | {store: Contract} + 派生查询 `slot_dates(store, weekday)`、`derived_count` | JuMP 容器风格 |
| 事件序列 `PlanEvent[]` | Assigned / Unassigned / ExceptionRaised / ContractAmended；**真相源** | 事件溯源 |
| `VisitPlan`（快照） | 事件序列 fold 的确定性快照；双视图 by_store / by_day 为读模型 | CQRS 对偶 |
| `ExceptionRecord(store, date, kind, reason)` | 类型化例外账；审计净除；LLM 写入口 | 事件溯源 |
| `GateReport` | 四闸（合同/星期几/走廊/次数）+ 例外透出 | 母项目验收闸 |
| `plan_ir/v1` JSON | 版本化交换格式 + JSON Schema（供 LLM 结构化输出约束） | ONNX + Protobuf + OpenAPI |

## 3. 语义基础（母项目数据钉死 + 已知缺口）

- 15 行结构表（全办 1,524 店零例外）：W=全槽位；B(φ)=ISO 周 mod 2 匹配槽位；
- f 是派生量；`服务周`=ISO 周 mod 4（行级全吻合）；
- **已知缺口 OQ-1**：53 周年边界（2026-W53→2027-W01）mod-2 parity 断裂 → 见 §OQ-1；
- **缺口 OQ-2**：月中开关店（effective 区间语义）→ Contract 占位字段；
- **缺口 OQ-3**：weekday 本体地位（合同承诺 vs 优化变量）→ 业务拍板。

## 4. 待裁决开放问题（GPT 共研议程）

- **OQ-1 锚点抽象**：把 `phase_of(d)=ISOWeek(d)%2` 泛化为 `AnchoredCycle(epoch, period)`——ISO 周只是 epoch 取值之一；连续全局周（days_since_epoch//7）是另一个。哪个是"真"的？判定实验设计（需 53 周年边界数据）；抽象层是否足以让两种锚点成为配置而非代码分支？
- **OQ-2 事件溯源 vs 快照**：核心真相存事件序列（fold 出视图）还是存快照+附加事件？事件粒度（store×date 一事一事件 vs 月度计划整体一事件）？
- **OQ-3 双视图一致性**：构造期断言（现状）vs 事件 fold 保证（结构上不可能不一致）？后者是否值得把 by_store/by_day 降级为纯派生 property？
- **OQ-4 版本策略**：v1 内只加不改；破坏性变更 v2+迁移器+双读期。迁移器放本仓库还是消费方？JSON Schema 是否随版本一起发？
- **OQ-5 LLM 适配器形态**：schema-constrained generation（OpenAPI/JSON Schema 约束）产事件提案 vs 自由文本+后校验？与 function-calling 生态怎么接？
- **OQ-6 与 OR 建模语言的关系**：SP 求解方言（约束 RHS 线性化）定义在 VisitIR 内还是母项目内？Pyomo 式符号层要不要进 IR？
- **OQ-7 测试策略**：母项目已裁定"语义层=精确重构+反例拒绝+有界日历穷举（2025~2029）"；IR 层再加 hypothesis 性质测试（任意日历×任意合同→投影一致性恒真）？
- **OQ-8 命名与身份**：店身份 = 线路内 idx vs 全局客户编码 vs 双向映射表冻结？跨线路指派（未来多业代联合优化）预留什么？

## 5. 不变的铁律

1. fail-closed：非法状态不可表示，构造即校验；
2. LLM 提案、IR 处置；
3. 版本化 schema 先于第二个消费者；
4. 每条语义必须能追溯到"1524 店数据零例外"或"用户业务澄清"，二者皆无 = 假设，标注假设。
