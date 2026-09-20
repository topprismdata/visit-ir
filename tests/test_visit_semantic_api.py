# -*- coding: utf-8 -*-
"""visit_semantic_api 类型契约测试: 不可变性 / 无裸容器 / 相位锚定语义."""
from dataclasses import fields, is_dataclass
from datetime import date

import pytest
from visit_semantic_api import (
    ContractType,
    CoreProtectionPolicy,
    ExceptionGrant,
    PlanningHorizon,
    SemanticObjectivePolicy,
    SourceMetadata,
    VisitContract,
    VisitSemanticSpec,
    WorkloadCorridorPolicy,
)


def _horizon() -> PlanningHorizon:
    return PlanningHorizon(
        start_date=date(2026, 3, 2),
        end_date=date(2026, 3, 13),
        timezone="Asia/Shanghai",
        calendar_id="cn_workdays_2026",
        anchor_week=10,
        phase_period=2,
    )


def _contract(code: str, sigma: int, dates: tuple, phase=None) -> VisitContract:
    return VisitContract(
        customer_code=code,
        contract_type=ContractType.BIWEEKLY if phase is not None else ContractType.WEEKLY,
        phase=phase,
        sigma=sigma,
        legal_slot_indices=tuple(range(len(dates))),
        obligation=len(dates),
        legal_dates=dates,
    )


def _spec() -> VisitSemanticSpec:
    mon = (date(2026, 3, 2), date(2026, 3, 9))
    fri0 = (date(2026, 3, 6),)
    fri1 = (date(2026, 3, 13),)
    return VisitSemanticSpec(
        horizon=_horizon(),
        contracts=(
            _contract("W1", 0, mon),
            _contract("B1", 4, fri0, phase=0),
            _contract("B2", 4, fri1, phase=1),
        ),
        corridor=WorkloadCorridorPolicy(
            k_min=1, k_max=3, source="historical_baseline", derivation="manual", approved=True
        ),
        core_protections=(CoreProtectionPolicy(customer_code="W1", mandatory_visit=True),),
        metadata=SourceMetadata(
            schema_version="1.0",
            content_hash="abc",
            source_snapshot_id="snap-1",
            compiler_version="visitir-0.1",
            compiled_at="2026-09-20T00:00:00",
        ),
    )


class TestImmutability:
    def test_frozen_rejects_attribute_write(self):
        spec = _spec()
        with pytest.raises(Exception):  # FrozenInstanceError
            spec.corridor = WorkloadCorridorPolicy(0, 0, "x", "x", False)

    def test_frozen_contract_tuple_rejects_mutation(self):
        c = _contract("W1", 0, (date(2026, 3, 2),))
        with pytest.raises(Exception):
            c.obligation = 99

    def test_no_bare_dict_or_list_fields_in_any_api_type(self):
        """铁律: 边界类型禁止裸 dict/list (v0.1 P0-2: frozen 不锁内容)."""
        for tp in (
            PlanningHorizon,
            WorkloadCorridorPolicy,
            CoreProtectionPolicy,
            ExceptionGrant,
            SemanticObjectivePolicy,
            VisitContract,
            VisitSemanticSpec,
            SourceMetadata,
        ):
            assert is_dataclass(tp), tp
            for f in fields(tp):
                assert f.type not in ("dict", "list", "Dict", "List"), (tp.__name__, f.name)


class TestPhaseAnchoring:
    def test_basic_phase(self):
        h = _horizon()
        assert h.phase_of(10) == 0
        assert h.phase_of(11) == 1

    def test_iso53_year_phase_continuity(self):
        """W53 年跨年不断链: 52→0, 53→1, 次年周1→1 (ISO%2 在此会翻车)."""
        h = PlanningHorizon(
            start_date=date(2026, 1, 1),
            end_date=date(2027, 1, 31),
            timezone="Asia/Shanghai",
            calendar_id="x",
            anchor_week=40,
            phase_period=2,
        )
        assert h.phase_of(52) == 0
        assert h.phase_of(53) == 1
        assert h.phase_of(1) == 1  # (1-40)%2 = 1 — 与周53同相, 连续
        assert h.phase_of(2) == 0


class SpecAccess:
    def test_contract_of_hit_and_miss(self):
        spec = _spec()
        assert spec.contract_of("W1").sigma == 0
        with pytest.raises(KeyError):
            spec.contract_of("NOPE")

    def test_protected_codes(self):
        assert _spec().protected_codes == frozenset({"W1"})

    def test_biweekly_contract_carries_phase(self):
        spec = _spec()
        assert spec.contract_of("B1").phase == 0
        assert spec.contract_of("B2").phase == 1
        assert spec.contract_of("W1").phase is None
