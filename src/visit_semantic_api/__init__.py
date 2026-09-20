# -*- coding: utf-8 -*-
"""visit_semantic_api — 语义层跨层类型契约(纯类型, 零实现, 零依赖).

> 出处: docs/design/THREE_LAYER_ARCHITECTURE_v0.2.md §3 (GPT 评审 P0-3 修正).
> 本包是跨层"电插头": L1 (visit_ir) 实现经本包对外发布类型, L2 (visitmodel)
> 经本包消费类型 — 实现层互相不感知 (L2 不得 import visit_ir 实现模块).

铁律:
- 本包不得 import 任何实现包 (visit_ir / visitmodel / algos / ortools / numpy);
- 一切边界类型 frozen=True;
- 禁止裸 dict/list 字段 (用 tuple / frozenset / MappingProxyType);
- 数值字段带单位后缀 (distance_m / duration_s), 杜绝单位错.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional

__all__ = [
    "ContractType",
    "SourceMetadata",
    "PlanningHorizon",
    "WorkloadCorridorPolicy",
    "CoreProtectionPolicy",
    "ExceptionGrant",
    "SemanticObjectivePolicy",
    "VisitContract",
    "VisitSemanticSpec",
]


class ContractType(Enum):
    """合同类型 (CONTRACT_CADENCE_MODEL v3): 周访 W / 双周访 B."""

    WEEKLY = "W"
    BIWEEKLY = "B"


@dataclass(frozen=True)
class SourceMetadata:
    """编译产物溯源元数据 (G4 可复现性).

    同一 source_snapshot_id + compiler_version 必须重演出同一 content_hash.
    """

    schema_version: str
    content_hash: str
    source_snapshot_id: str
    compiler_version: str
    compiled_at: str  # ISO 8601


@dataclass(frozen=True)
class PlanningHorizon:
    """计划视野与日历身份.

    相位锚定语义 (取代 ISO 周 % 2, 规避 53 周年跨年断链):
        phase(w) = (w - anchor_week) mod phase_period
    例: anchor_week=40, period=2 → 周40/42/..→0, 周41/43/..→1;
    W53 年: 周52→0, 周53→1, 次年周1→(1-40)%2=1 — 跨年连续.
    """

    start_date: date
    end_date: date
    timezone: str  # e.g. "Asia/Shanghai"
    calendar_id: str  # 工作日历标识
    anchor_week: int  # ISO 自然周序锚点
    phase_period: int = 2  # 相位周期 (双周=2)

    def phase_of(self, iso_week: int) -> int:
        """锚定周期相位 (纯函数, 无副作用)."""
        return (iso_week - self.anchor_week) % self.phase_period


@dataclass(frozen=True)
class WorkloadCorridorPolicy:
    """走廊策略 (I2): K_min/K_max 的语义所有权在 L1.

    v0.1 教训: 此前隐藏在 LineData.__post_init__ 从 days_orig 推导 —
    业务推断政策不得由数据结构构造器或求解器发明.
    口径: k_max=0 表示无上界 (沿 core/metric.check_capacity 惯例).
    """

    k_min: int
    k_max: int
    source: str  # "historical_baseline" | "management_directive"
    derivation: str  # "min/max(original_daily_counts)" | "manual" | ...
    approved: bool
    approved_by: str = ""


@dataclass(frozen=True)
class CoreProtectionPolicy:
    """核心客户保护 (I5): 不是 bool, 是完整保护策略."""

    customer_code: str
    mandatory_visit: bool  # 不可跳过 (义务必须精确履行)
    cadence_relaxable: bool = False  # 频次可否放松 (需 ExceptionGrant)
    weekday_relaxable: bool = False  # 星期几可否改变 (需 ExceptionGrant)
    exception_priority: str = "NORMAL"  # CRITICAL | HIGH | NORMAL
    relaxation_priority: int = 0  # 资源不足时最后被牺牲的排序 (越小越后)


@dataclass(frozen=True)
class ExceptionGrant:
    """例外授权 (G6): 不是"绕过规则", 是"经授权的另一条规则".

    v0.1 教训: scope/target_rule/override_value 全 str/object 会产生
    silent semantic drift — 全部类型化, override 值必须不可变.
    """

    exception_id: str
    target_rule_id: str  # 被修改的规则标识
    subject_codes: tuple[str, ...]  # 受影响客户编码
    effective_interval: tuple[date, date]  # 闭区间 [start, end]
    typed_override: object  # 不可变值 (str/int/tuple/frozenset)
    authority_id: str  # 审批人
    approved_at: str  # ISO 8601
    expires_at: Optional[str] = None  # ISO 8601, None=不过期
    reason_code: str = ""


@dataclass(frozen=True)
class SemanticObjectivePolicy:
    """业务目标含义 (L1 定义, L2 翻译成 ObjectiveTerm 数学向量).

    v0.1 断层修复: 目标含义此前凭空出现在 MathIR — 现在 L1 是唯一出处.
    """

    distance: str = "minimize"  # "minimize" | "ignore"
    plan_stability: str = "prefer_low_change"  # "prefer_low_change" | "ignore"
    workload_balance: str = "prefer_even"  # "prefer_even" | "ignore"
    core_protection_mode: str = "hard_constraint"  # "hard_constraint" | "high_weight"
    preference_mode: str = "lexicographic"  # "lexicographic" | "pareto"


@dataclass(frozen=True)
class VisitContract:
    """客户拜访合同 (合同-相位本体, CONTRACT_CADENCE_MODEL v3 零例外).

    - 周访 W: legal_slot_indices = 所选星期几 σ 全部槽位序号, phase=None;
    - 双周 B: legal_slot_indices = σ 中相位匹配槽位, phase ∈ {0,1};
    - obligation = |legal_slot_indices| 是派生量 (v1 教训: 频次不是合同);
    - legal_dates 是 L1 内单向派生的编译产物 (槽位→具体日期), 供 L2 直用,
      L2 不得自行重推导槽位语义.
    """

    customer_code: str
    contract_type: ContractType
    phase: Optional[int]  # B 类必填, W 类 None
    sigma: int  # 星期几, 0=周一
    legal_slot_indices: tuple[int, ...]
    obligation: int
    legal_dates: tuple[date, ...]


@dataclass(frozen=True)
class VisitSemanticSpec:
    """L1 编译产物: 不可变语义规格 — L1→L2 唯一传递对象.

    不变量: 合同-相位一致性由 L1 编译时保证 (check_contract 零例外闸);
    本类型只承载结果, 不承载推导过程.
    """

    horizon: PlanningHorizon
    contracts: tuple[VisitContract, ...]
    corridor: WorkloadCorridorPolicy
    core_protections: tuple[CoreProtectionPolicy, ...] = ()
    exceptions: tuple[ExceptionGrant, ...] = ()
    objective_policy: SemanticObjectivePolicy = field(default_factory=SemanticObjectivePolicy)
    metadata: Optional[SourceMetadata] = None

    def contract_of(self, customer_code: str) -> VisitContract:
        """按编码取合同 (spec 规模 ~百级, 线性扫描足够; 不引入可变索引)."""
        for c in self.contracts:
            if c.customer_code == customer_code:
                return c
        raise KeyError(customer_code)

    @property
    def protected_codes(self) -> frozenset:
        """mandatory_visit 的核心客户编码集."""
        return frozenset(p.customer_code for p in self.core_protections if p.mandatory_visit)
