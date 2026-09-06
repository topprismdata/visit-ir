# IR 设计调研（论文 + 工业界） · 2026-09-06

> 目的：为"周期拜访计划 IR"寻找可借鉴的成熟设计。每条标注 **借鉴 / 规避**。

## 1. 编译器 IR

### 1.1 MLIR：方言 + 渐进降级 ⭐ 核心借鉴
Lattner et al., *"MLIR: A Compiler Infrastructure for the End of Moore's Law"*, CGO 2021（arXiv:2002.11054）。
- **方言（dialect）**：不建单一巨型 IR，而是"IR 构建套件"——各源（SRP xlsx、优化器输出、调度对话）各定义方言，共享一套验证/改写基础设施；
- **渐进降级（progressive lowering）**：高层语义（合同/日历）→ 中层（指派/例外）→ 求解器方言（SP 模型、TSP 实例），每层降级都有验证；
- **借鉴**：VisitIR = 中枢方言；SRP 解析器/优化器/LLM 适配器都是"前端方言"，求解接口是"后端方言"；
- **规避**：不搬它的 op/type/attribute 三件套泛型机制——领域窄得多，dataclass + 校验函数即可。

### 1.2 Sea of Nodes / SSA
以依赖图而非线性序列表示程序。**借鉴**：派生关系显式化（by_store/by_day 是同一事件序列的两个投影，而非两份独立真相）。

## 2. ML 编译器交换格式

### 2.1 ONNX / StableHLO：版本化规范交换 ⭐ 核心借鉴
- `ir_version` + `opset` + 独立 checker：加载即验，未知版本 fail-closed；
- 自包含（不依赖产生它的训练框架）；
- **借鉴**：`plan_ir/v1` schema + 加载器内置 checker；跨机审计（M2↔M1 Max）只交换 IR 文件，不交换解释代码；
- **规避**：ONNX 曾因早期版本演进无迁移指南导致生态混乱——版本纪律（Protobuf 式）必须先于第一个消费者确立。

## 3. 运筹学建模语言（OR 领域自己的"IR"先例）

### 3.1 Pyomo / JuMP / AMPL / GAMS
- Hart et al. 2017（Pyomo, Math. Prog. Computation）；Dunning et al. 2017（JuMP, SIAM Review）；Jusevičius et al. 2021（五 AML 理论+实验对比, Informatica）。
- **核心思想**：把"数学模型"（符号层：集合/参数/约束）与"求解实例"（数值层）分离——模型对多求解器可移植；
- **借鉴**：VisitIR 的合同层（符号：cadence×phase×weekday 规则）与计划实例层（地面：具体店×日期集）显式分离；`contract_of` = 符号→地面的 grounding 操作；
- **规避**：AML 面向"人写模型"，VisitIR 面向"机器往返"——不做 DSL 语法，做规范数据结构。

## 4. 事件溯源 / CQRS ⭐ 核心借鉴（例外账的理论基础）
Fowler, *"Event Sourcing"* (2005) / *"CQRS"*；Kafka Streams 的 table-stream 对偶。
- **真相 = 类型化事件序列**（Assigned / ExceptionRaised / ContractAmended…），快照与读模型（by_store、by_day）全是确定性 fold 的投影；
- **对偶投影天然一致**：我们的双视图一致性从"构造期断言"升级为"同一 fold 的两个读模型"；
- **LLM 适配层的正确入口**：LLM 产出的不是新状态，而是**事件提案**；事件校验器裁决后入账；
- **审计免费获得**：Phase B"新旧解恒等"= 事件序列等价（或快照等价）；
- **规避**：不建事件存储基础设施——事件序列就是 JSON 数组，快照就是 schema 版本化对象。

## 5. Schema 演化纪律

### 5.1 Protocol Buffers
- 字段编号永不复用；required→optional 纪律；未知字段保留（前向兼容）；
- **借鉴**：`plan_ir` 字段演进规则成文（v1 内只加不改删；破坏性变更 = v2 + 迁移器 + 双读期）。

### 5.2 OpenAPI / JSON Schema
契约先行、工具可验。**借鉴**：`plan_ir/v1` 出 JSON Schema 供外部（LLM 结构化输出）直接校验——LLM 适配层用 schema-constrained generation，而非自由文本后校验。

## 6. 元建模框架

### 6.1 EMF（Eclipse Modeling Framework）
元模型 → 模型 → 序列化（XMI）三层 + 反射式工具。**借鉴**：三层等价物即 dataclass（元模型）/ VisitPlan 实例（模型）/ plan_ir JSON（序列化）。**规避**：EMF 的重量级反射与代码生成——Python dataclass 已够。

### 6.2 RDF/OWL 本体
**规避为主**：描述逻辑本体对"单域窄语义+强校验"场景过重；我们要的是可执行的类型系统，不是可推理的知识库。W53 锚点这类问题靠性质测试，不靠本体推理。

## 7. 领域基准格式（反面教材）

### 7.1 VRPLIB / Solomon VRPTW
路线问题研究的标准交换格式。**教训**：纯平面文本、无版本、无校验器、语义靠约定俗成——几十年积累了大量"格式相同、语义漂移"的实例。VisitIR 必须带 checker 与版本。

## 8. 同域先例扫描（GPT 共研议程）
- OR-Tools RoutingModel 内部表示（int indices + dimension 累加器）能否作后端方言参考；
- 工业界现场调度系统（FourKites/Project44 类、美团/顺丰城配调度）是否有公开 IR；
- SMT 求解器 Z3 的 AST/排序设计（类型化项 + 排序检查）；
- 时序数据库/工作流引擎（Temporal 的 workflow history 即事件溯源变体）。

---
**引用清单**：Lattner et al. 2021 (CGO; arXiv:2002.11054) · Hart et al. 2017 (Pyomo, MPCR) · Dunning et al. 2017 (JuMP, SIAM Review 59(1)) · Jusevičius et al. 2021 (Informatica) · Fowler 2005 (Event Sourcing/CQRS) · Protocol Buffers Language Spec (style/evolution) · ONNX/StableHLO IR specs · Steinberg et al., EMF Book.
