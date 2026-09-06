# VisitIR — 周期拜访计划中间表示（An Intermediate Representation for Periodic Visit Plans）

> **Status**: v0.1 语义核心已落地（`src/visit_ir/contract.py`，自母项目剥离；7 单元测试含 AST 零依赖守卫 + W53 边界文档化）· 九件核心（ObligationSet/History 等）按 [`docs/DESIGN_DECISIONS_v0.1.md`](docs/DESIGN_DECISIONS_v0.1.md) 迭代中
> **Mission**: 为"周期性外勤拜访计划"定义一个**规范、版本化、可独立验证**的中间表示（IR），把合同语义、日历、指派、例外账从具体数据源（SRP/优化器/人工/LLM 代理）与具体消费方（求解器/验收/审计）中解耦。
> **母项目**: `visit-scheduling-optimizer`（快消外勤两阶段运筹引擎）；本项目从其语义层剥离独立。

## 为什么需要 IR（问题陈述）

母项目今天的语义散落在四种临时表示里：SRP 原始行 / `days` dict（date 键与 JSON 字符串键两套强制转换）/ ad-hoc 审计 JSON / 三处各自反推的合同三元组。每次跨边界都是一次语义漂移机会——2026-09-06 的"月频次→周节奏→合同-相位"三次语义修正即为例证。

## 设计研究

- [`docs/RESEARCH_IR_SURVEY.md`](docs/RESEARCH_IR_SURVEY.md) — 论文与工业界 IR 设计调研（MLIR / ONNX·StableHLO / Pyomo·JuMP / 事件溯源·CQRS / Protobuf 演化 / EMF / VRPLIB）
- [`docs/DESIGN_STRAWMAN.md`](docs/DESIGN_STRAWMAN.md) — v0 草案 + 待裁决开放问题（GPT 共研议程）

## 语义基础（已由母项目 1,524 店数据钉死）

合同 ∈ {周访 W, 双周访 B(相位 φ∈{0,1})}；月内次数 f 是派生量；`服务周` = ISO 周 mod 4；
已知边界：ISO 53 周年（如 2026）边界 mod-2 parity 断裂 → 锚点抽象待定（见 DESIGN_STRAWMAN §OQ-1）。

## 工程纪律

- IR 核心零 ML 依赖：确定性、可复现、fail-closed（这是它能当"语义法院"的前提）
- LLM 只在边界作为适配器：自然语言事件 → 类型化变更操作 → IR 校验裁决（LLM 提案，IR 处置）
