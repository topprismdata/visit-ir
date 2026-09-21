# -*- coding: utf-8 -*-
"""SemanticCompiler 测试: 合同反解/零例外闸/走廊所有权/保护/哈希确定性.

合成事实: 2026-03-02(周一)..03-13(周五), ISO 周 10/11, 相位锚 = 周 10 (偶 → 与 ISO%2 同相).
门店: W1 周一, W2 周二, W3 周三, W4 周四 (全槽位), B1 周五相位0, B2 周五相位1, W1b 周一.
每日店数: 周一 2, 其余 1 → 历史走廊 (1, 2).
"""
from datetime import date

import pytest
from visit_ir import SemanticCompiler
from visit_semantic_api import (
    CompilerProfile,
    ContractType,
    PlanningHorizon,
    WorkloadCorridorPolicy,
)

D = date
MON = (D(2026, 3, 2), D(2026, 3, 9))
TUE = (D(2026, 3, 3), D(2026, 3, 10))
WED = (D(2026, 3, 4), D(2026, 3, 11))
THU = (D(2026, 3, 5), D(2026, 3, 12))
FRI = (D(2026, 3, 6), D(2026, 3, 13))
WORKDAYS = tuple(sorted(MON + TUE + WED + THU + FRI))


def _facts():
    days = {
        MON[0]: ["W1", "W1b"], MON[1]: ["W1", "W1b"],
        TUE[0]: ["W2"], TUE[1]: ["W2"],
        WED[0]: ["W3"], WED[1]: ["W3"],
        THU[0]: ["W4"], THU[1]: ["W4"],
        FRI[0]: ["B1"],   # ISO 周10 → 相位 0
        FRI[1]: ["B2"],   # ISO 周11 → 相位 1
    }
    return {"days_orig": days, "workdays": list(WORKDAYS)}


def _compile(**kw):
    return SemanticCompiler().compile(_facts(), CompilerProfile(snapshot_id="t1", **kw))


class TestContractDerivation:
    def test_weekly_and_biweekly_contracts(self):
        spec = _compile()
        by = {c.customer_code: c for c in spec.contracts}
        assert by["W1"].contract_type == ContractType.WEEKLY
        assert by["W1"].phase is None and by["W1"].sigma == 0
        assert by["W1"].legal_dates == MON and by["W1"].obligation == 2
        assert by["W1"].legal_slot_indices == (0, 1)
        assert by["B1"].contract_type == ContractType.BIWEEKLY
        assert by["B1"].phase == 0 and by["B1"].legal_dates == (FRI[0],)
        assert by["B2"].phase == 1 and by["B2"].legal_dates == (FRI[1],)
        assert by["B1"].obligation == 1

    def test_horizon_anchor(self):
        h = _compile().horizon
        assert (h.start_date, h.end_date) == (D(2026, 3, 2), D(2026, 3, 13))
        assert h.anchor_week == 10 and h.phase_period == 2
        assert h.phase_of(10) == 0 and h.phase_of(11) == 1


class TestCorridorOwnership:
    def test_historical_baseline_derived(self):
        c = _compile().corridor
        assert (c.k_min, c.k_max) == (1, 2)  # 周一 2 家, 其余 1 家
        assert c.source == "historical_baseline"
        assert c.approved is False, "数据推导 ≠ 管理批准"

    def test_management_directive_override(self):
        override = WorkloadCorridorPolicy(
            k_min=2, k_max=4, source="management_directive",
            derivation="manual", approved=True, approved_by="boss",
        )
        c = _compile(corridor_override=override).corridor
        assert c is override, "管理指令走廊原样入 spec"


class TestProtection:
    def test_protected_codes_become_mandatory(self):
        prot = _compile(protected_codes=("W1", "B1")).core_protections
        assert {p.customer_code for p in prot} == {"W1", "B1"}
        assert all(p.mandatory_visit for p in prot)

    def test_unknown_protected_code_rejected(self):
        with pytest.raises(ValueError, match="未知客户"):
            _compile(protected_codes=("GHOST",))


class TestZeroExceptionGate:
    def test_multi_weekday_store_rejected(self):
        facts = _facts()
        facts["days_orig"][WED[0]] = ["W3", "X"]   # X 周三+周四各一访 → 闸必拒
        facts["days_orig"][THU[0]] = ["W4", "X"]
        with pytest.raises(ValueError, match="零例外闸未过"):
            SemanticCompiler().compile(facts)


class TestDeterminism:
    def test_same_facts_same_hash(self):
        s1, s2 = _compile(), _compile()
        assert s1.metadata.content_hash == s2.metadata.content_hash
        assert s1.metadata.source_snapshot_id == "t1"

    def test_different_facts_different_hash(self):
        assert _compile().metadata.content_hash != _compile(protected_codes=("W1",)).metadata.content_hash

    def test_spec_is_frozen(self):
        spec = _compile()
        with pytest.raises(Exception):
            spec.corridor = WorkloadCorridorPolicy(0, 0, "x", "x", False)
