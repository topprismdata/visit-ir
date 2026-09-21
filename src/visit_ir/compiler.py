# -*- coding: utf-8 -*-
"""SemanticCompiler — L1 语义编译器: 业务事实 + 策略档案 → VisitSemanticSpec.

> 出处: docs/design/THREE_LAYER_ARCHITECTURE_v0.2.md §3, Phase B (语义所有权迁移).

所有权迁移 (v0.1 泄漏修复的正面落点):
- 走廊 K_min/K_max: 此前藏在 LineData.__post_init__ 从 days_orig 静默推导 —
  现在是显式的 WorkloadCorridorPolicy(source/derivation/approved);
- f_c: 此前是 LineData.freq 独立输入(与合同双真相)→ 现在是 obligation 派生量;
- 核心保护: 此前只是 OTM 等级 bool → 现在是 CoreProtectionPolicy;
- 全部进 frozen VisitSemanticSpec, 带 SourceMetadata 哈希 (G4 可复现).

零例外闸: 合同反解后必须通过 check_contract (CONTRACT_CADENCE_MODEL 定稿
验收), 否则拒绝编译 — 语义正确性在这里一次性保证, 下游不再重复判断.

本模块零依赖 (不 import visitmodel / ortools / numpy) — L1 纪律.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import date, datetime, timezone as _tz
from typing import Mapping, Optional, Sequence

from visit_ir.contract import check_contract, contract_of, contract_slot_dates, slot_index_map
from visit_semantic_api import (
    CompilerProfile,
    ContractType,
    CoreProtectionPolicy,
    PlanningHorizon,
    SemanticObjectivePolicy,
    SourceMetadata,
    VisitContract,
    VisitSemanticSpec,
    WorkloadCorridorPolicy,
)

SCHEMA_VERSION = "1.0"
COMPILER_VERSION = "visit-ir-0.1.0+semantic-compiler"


class SemanticCompiler:
    """业务事实 + CompilerProfile → 不可变 VisitSemanticSpec (纯函数语义)."""

    def compile(self, facts: Mapping, profile: Optional[CompilerProfile] = None) -> VisitSemanticSpec:
        """facts: {"days_orig": {date: [customer_code,...]}, "workdays": [date,...]}.

        编译步骤:
        G1 事实结构校验 (日期⊆工作日, 客户编码非空)
        G2 contract_of 反解合同 (W / B+φ)
        G3 零例外闸: check_contract 必须 [] — 否则拒绝编译
        G4 每客户 σ/合法槽位序号/合法日期/obligation (派生)
        G5 走廊: profile.corridor_override 或 历史基线 min/max(日店数)
        G6 核心保护: profile.protected_codes → CoreProtectionPolicy
        G7 SourceMetadata: 确定性 content_hash (同事实+同档案 → 同哈希)
        """
        profile = profile or CompilerProfile()
        days_orig: Mapping[date, Sequence[str]] = facts["days_orig"]
        workdays: Sequence[date] = list(facts["workdays"])

        # ---- G1 事实结构 ----
        if not workdays:
            raise ValueError("facts.workdays 为空")
        wd_set = set(workdays)
        for d in days_orig:
            if d not in wd_set:
                raise ValueError(f"days_orig 含工作日之外的日期: {d}")
        codes_seen = {c for seq in days_orig.values() for c in seq}
        if not all(isinstance(c, str) and c for c in codes_seen):
            raise ValueError("客户编码必须为非空字符串")

        # ---- G2 合同反解 ----
        contracts_raw = contract_of(days_orig, workdays)

        # ---- G3 零例外闸 ----
        bad = check_contract(days_orig, contracts_raw, workdays)
        if bad:
            raise ValueError(
                f"零例外闸未过: {len(bad)} 家门店日期集不符合任何 (合同,相位,σ): "
                f"{sorted(bad)[:10]}"
            )

        # ---- G4 每客户槽位/合法日期/义务 ----
        slot_of = slot_index_map(workdays)
        by_wd: dict[int, list[date]] = defaultdict(list)
        for dd in sorted(workdays):
            by_wd[dd.weekday()].append(dd)
        sched: dict[str, set] = defaultdict(set)
        for dd, seq in days_orig.items():
            for c in seq:
                sched[c].add(dd)

        contracts: list[VisitContract] = []
        for c in sorted(contracts_raw):
            kappa, phi = contracts_raw[c]
            ds = sched[c]
            sigma = next(iter(ds)).weekday()  # 闸保证单一星期几
            wd_dates = by_wd[sigma]
            legal = sorted(contract_slot_dates(kappa, phi, wd_dates))
            contracts.append(
                VisitContract(
                    customer_code=c,
                    contract_type=ContractType.WEEKLY if kappa == "W" else ContractType.BIWEEKLY,
                    phase=phi,
                    sigma=sigma,
                    legal_slot_indices=tuple(sorted(slot_of[d][1] for d in ds)),
                    obligation=len(legal),
                    legal_dates=tuple(legal),
                )
            )

        # R2′ 换挡自由: 每店在每个星期一下的合同槽位集 (相位语义由 L1 独占)
        weekday_slots: list[tuple[str, int, frozenset]] = []
        for c in sorted(contracts_raw):
            kappa, phi = contracts_raw[c]
            for w, wds in by_wd.items():
                weekday_slots.append(
                    (c, w, frozenset(contract_slot_dates(kappa, phi, wds)))
                )

        # ---- G5 走廊 (所有权正落点) ----
        if profile.corridor_override is not None:
            corridor = profile.corridor_override
        else:
            lens = [len(seq) for seq in days_orig.values()]
            corridor = WorkloadCorridorPolicy(
                k_min=min(lens) if lens else 0,
                k_max=max(lens) if lens else 0,
                source="historical_baseline",
                derivation="min/max(original_daily_counts)",
                approved=False,  # 数据推导 ≠ 管理批准
            )

        # ---- G6 核心保护 ----
        known = set(contracts_raw)
        unknown = [c for c in profile.protected_codes if c not in known]
        if unknown:
            raise ValueError(f"protected_codes 引用未知客户: {sorted(unknown)[:10]}")
        protections = tuple(
            CoreProtectionPolicy(customer_code=c, mandatory_visit=True)
            for c in sorted(profile.protected_codes)
        )

        # ---- 视野 ----
        horizon = PlanningHorizon(
            start_date=min(workdays),
            end_date=max(workdays),
            timezone=profile.timezone,
            calendar_id=profile.calendar_id,
            anchor_week=min(workdays).isocalendar()[1],
            phase_period=2,
        )

        # ---- G7 溯源 (确定性哈希: 不含 compiled_at) ----
        payload = {
            "contracts": [
                [c.customer_code, c.contract_type.value, c.phase, c.sigma,
                 sorted(str(d) for d in c.legal_dates)]
                for c in contracts
            ],
            "corridor": [corridor.k_min, corridor.k_max, corridor.source],
            "protections": [p.customer_code for p in protections],
            "exceptions": [e.exception_id for e in profile.exceptions],
            "workdays": sorted(str(d) for d in workdays),
            "weekday_slots": sorted(
                [code, w, sorted(str(d) for d in slots)]
                for code, w, slots in weekday_slots
            ),
        }
        content_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        metadata = SourceMetadata(
            schema_version=SCHEMA_VERSION,
            content_hash=content_hash,
            source_snapshot_id=profile.snapshot_id,
            compiler_version=COMPILER_VERSION,
            compiled_at=datetime.now(_tz.utc).isoformat(timespec="seconds"),
        )

        return VisitSemanticSpec(
            horizon=horizon,
            contracts=tuple(contracts),
            corridor=corridor,
            core_protections=protections,
            exceptions=tuple(profile.exceptions),
            objective_policy=SemanticObjectivePolicy(),
            weekday_slots=tuple(weekday_slots),
            metadata=metadata,
        )
