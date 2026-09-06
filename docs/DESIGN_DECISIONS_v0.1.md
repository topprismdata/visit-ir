# VisitIR v0.1 设计裁决记录（Design Decision Record） · 2026-09-06

> **共研方式**：控制器起草调研+strawman → ChatGPT 独立批判并补充文献 → 控制器逐条交叉验证后裁决。
> ChatGPT 核心判断（已采纳）："**最值得立即定的不是 OQ-1 锚点，而是 ObligationIR + Command/Event 分离——这两个不定，VisitIR 两个月后会变成另一个更干净的排班 DTO**。"

## 一、八条裁决（全部采纳，含控制器注解）

| # | 裁决 | 内容 | 控制器验证注解 |
|---|---|---|---|
| D1 | **VisitObligation 强制降级边界** | Contract（符号规则）→ ObligationSet（具体周期内的具体拜访义务）→ PlanState 必须恰好满足义务集。求解器只消费义务，不读原始合同 | ✓ 直解"f 是派生量"：义务由 (contract, calendar, cycle 假设) 按地平线派生；`count_ok` 从"行数相等"升级为"义务集被精确满足" |
| D2 | **锚点 = 假设集，不选边** | `AnchoredCycle` 抽象 + 假设注册表（iso-week-v1 / continuous-week-v1 …）；每个 plan 声明其有效假设；地平线跨越假设分歧点（如 53 周年界）→ fail-closed | ✓ 优于"猜一个"：7 月数据本就无法区分两假设（观测等价）；分歧点检测把 W53 风险变成类型错误而非静默错误 |
| D3 | **PlanState + History，拒绝纯事件溯源** | 当前状态可查询；History 存 Command[] / Decision[] / Event[] 供审计回放 | ✓ 修正了控制器 v0 草案"事件即真相"的过度设计——无事件存储基础设施时纯溯源是负资产 |
| D4 | **LLM 输出 Command，不输出 Event** | 命令经校验器裁决 → 产生事件（或被拒并说明）。事件是"已发生"，命令是"提议" | ✓ 与"LLM 提案、IR 处置"铁律一致，且给了拒绝语义一个正式位置 |
| D5 | **by_store/by_day 永远是投影** | 不可写状态；由 PlanState 确定性派生 | ✓ 结构性消除双视图不一致（此前靠构造期断言） |
| D6 | **SP/ALNS 是独立方言/包** | core IR 不含线性化、不含算法状态 | ✓ 与宪法三层纪律同构；数学层（母项目 Task 2）即 SP 方言的宿主 |
| D7 | **稳定全局实体 ID + 降级局部索引** | 店身份 = 全局稳定 ID（客户编码/URN `visitir://store/...` + external_refs 别名表）；线路内 idx 是求解器降级产物（OR-Tools RoutingIndexManager 先例） | ✓ 修正控制器 v0 草案"冻结线路内 idx"的短视——那是求解器局部索引，不配当身份；ServiceEligibility(store↔rep, valid_from/to) 关系表为多业代预留，Route 降为 RoutePlan 对象 |
| D8 | **版本三元组** | `ir_version` + `opset_imports`（依赖的语义能力集，如 cycle.v1.iso / exceptions.v1）+ `required_capabilities`；parse ≠ validate ≠ lower ≠ solve ≠ certify 五段分离 | ✓ ONNX 经验的完整吸收；比单一版本号强在"能力声明"可被加载器做依赖判定 |

## 二、v0.1 核心模块树（ChatGPT 提案，控制器采纳）

```
VisitIR Module
├── Header            # ir_version + opset_imports + required_capabilities
├── MasterData        # Store[] / ServiceResource[] / ExternalRef[] (别名: SRP/CRM/...)
├── WorkCalendar      # timezone ★ / working_dates / CycleSpec[] (AnchoredCycle 假设注册)
├── ContractBook      # Contract[] / ContractBinding[]
├── ObligationSet     # ★ VisitObligation[] — Contract→Solver 的降级边界
├── PlanState         # Assignment[] — 当前状态
├── ExceptionSet      # Exception[] — 类型化例外账
├── Provenance        # source_refs / solver_run / semantic_evidence ← 每条语义的数据证据链
└── History           # Command[] / Decision[] / Event[]
```
`by_store / by_day / GateReport / SP 列 / ALNS 状态 / solver idx` **全部移出 core state**，降为派生投影或方言产物。

## 三、补充文献（ChatGPT 检索，控制器核实纳入调研）

- **Timefold / OptaPlanner 领域模型**：problem facts（求解不变）/ planning entities / planning variables / PlanningId 稳定标识 + rebasing——比 AML 更贴近"语义-决策分离"；映射：Calendar/Store/Contract ≈ problem facts，VisitObligation ≈ immutable demand，Assignment ≈ planning variable。
- **GS1 EPCIS 2.0**：供应链类型化事件标准（what/when/where/why/who 五维信封 + 类型化事件层级）——EventLog 信封直接吸收；比泛型 CQRS 博客更贴 FMCG 域。
- **OR-Tools RoutingIndexManager**：业务 location index 与 solver 内部 index 显式分离的工业先例（D7 依据）。
- **美团配送公开架构**：**无公开 IR**（不宣称"参考美团 IR"）；可借鉴的是系统边界——dispatch/routing/ETA/planning 是分离决策组件 ⇒ 支持"共享世界语义 + 多决策后端"。
- **Temporal**：借 immutable history / deterministic replay / version-aware evolution；**不照搬**事件流即一切状态（它是 workflow runtime，我们是开放交换语义）。

## 四、修正后的五段纪律

`parse ≠ validate ≠ lower ≠ solve ≠ certify`
每段独立可测、独立可拒。母项目现行"四道闸"对应 validate 段；"池内差距声明"对应 certify 段的诚实性约束。

## 五、下一步

1. 母项目 Task 1 语义核心（已绿）作为 `visit_ir` 首批实现迁移进本仓库（grit/copy + 归属注释）；
2. 按 v0.1 模块树重构：ObligationSet 与 Command/Event 为新增件；
3. 主线 `core/contract.py` 改为薄 shim → `visit_ir` 依赖；
4. JSON Schema（plan_ir/v0.1）随首版发布，供 LLM 适配层做约束生成（OQ-5 裁定：schema-constrained 优先）。

## 六、共研批判清单（ChatGPT P0/P1 逐条裁决）

| # | 批判 | 裁决 | 落点 |
|---|---|---|---|
| P0-1 | 缺 ObligationIR，Contract 直接跳 Plan 太远；否则合同解释器/SP/Gate 三处重复实现日历语义 | 采纳（即 D1） | ObligationSet；grounding 函数唯一实现处 |
| P0-2 | 反对 PlanEvent[] 作唯一真相源（replay 成本、事件语义自身演化、历史缺失即 artifact 不可解释）| **采纳，修正 v0 草案**：PlanState=authoritative current；PlanHistory=authoritative provenance；不变量 `fold(base_snapshot, events) == head_snapshot`，二者不许漂移 | §二 History 结构 |
| P0-3 | LLM 不该制造事实：Event=已接受事实；应为 Command(意图)→Decision(IR裁决)→Accept?Event:Reject(reason) 三型 | 采纳（即 D4 的严格化） | History 三桶；LLM 适配层只产 ProposedCommand |
| P0-4 | `additionalProperties:false` 与"v1 内只加不改"直接冲突（老 reader 遇新字段即崩）| **采纳，修正 v0 版本纪律**：ir_version(结构) + opset_imports(方言语义) + required_capabilities(能力)；未知 capability fail-closed；未知非语义 metadata preserve 不解释；语义扩展=新 opset 版本 | Header 结构；schema 演化规则成文 |
| P0-5 | AnchoredCycle 不许把"未知真相"伪装成"可配置真相"（无证据选 ISO_WEEK_MOD vs CONTINUOUS_WEEK）| 采纳（即 D2）：unresolved hypothesis set + horizon equivalence + 分歧 fail-closed | WorkCalendar.CycleSpec |
| P1-1 | Contract 缺 weekday_policy（FIXED(WED) vs FLEXIBLE）——否则换星期几违法性永远靠经验判断 | 采纳：类型化 weekday_policy；母项目 R2′ 业务澄清 = FIXED(但 σ 可整体重指派，作为 policy 的一个取值文档化) | Contract 字段；拍板点②的 IR 侧表达 |
| P1-2 | effective_from/to 需最低限度双时态：valid_time(业务生效) vs recorded_time(系统知晓) | 采纳设计，实现延后（当前数据无此场景）：Contract 保留双字段对 | Contract 类型注释 + Non-Goal |
| P1-3 | ExceptionRecord 不能是万能逃生口：typed effect（WAIVE_OBLIGATION / SHIFT_SERVICE_DATE / SUSPEND_CONTRACT / OVERRIDE_WEEKDAY / MANUAL_ASSIGNMENT / DATA_CORRECTION）+ target/interval/reason_code/authority/source/approved_by | 采纳：v1 即做 typed effect 枚举；authority/approved_by 先留空 | ExceptionSet 结构 |
| P1-4 | GateReport 是派生证据非计划自带事实（checker 升级后同 Plan 产生新 Report）：应含 input_plan_hash / checker_version / gate_spec_version | 采纳：GateReport 独立于 VisitPlan，携带哈希与版本 | 验收器重构（母项目 Task 4 对齐） |
| P1-5 | ServiceResource 模型缺席（不做"广州10条线路专用格式"）| 采纳：MasterData.ServiceResource[] + ServiceEligibility(store↔rep, valid_from/to) M2M；RoutePlan(resource_id, service_date, assignments) 为对象非主数据 | §二 MasterData |

**结构裁定汇总**：v0.1 core = Header / MasterData / WorkCalendar / ContractBook / ObligationSet / PlanState / ExceptionSet / Provenance / History 九件；by_store、by_day、GateReport、SP 列、ALNS 状态、solver idx 全部为投影或方言产物，不进 core state。五段纪律：`parse ≠ validate ≠ lower ≠ solve ≠ certify`。
