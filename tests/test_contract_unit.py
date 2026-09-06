# -*- coding: utf-8 -*-
"""VisitIR 合同原语单元测试 (合成日历, 零母项目依赖).
真实数据精确重构测试在母项目 tests/test_semantic_contract.py (集成层)."""
import datetime as dt
from datetime import date

import pytest


def _july_workdays():
    d0 = date(2026, 7, 1)
    return [d0 + dt.timedelta(days=i) for i in range(31)
            if (d0 + dt.timedelta(days=i)).weekday() < 5]


def test_phase_of_iso_week_parity():
    from visit_ir.contract import phase_of
    assert phase_of(date(2026, 7, 1)) == 1
    assert phase_of(date(2026, 7, 8)) == 0
    assert phase_of(date(2026, 7, 15)) == 1
    assert phase_of(date(2026, 7, 6)) == 0
    assert phase_of(date(2026, 7, 13)) == 1


def test_slot_sets_exhaustive_15_row_table():
    from visit_ir.contract import contract_slot_dates
    dates = _july_workdays()
    wd = {w: [d for d in dates if d.weekday() == w] for w in range(5)}
    for w, ds in wd.items():
        assert contract_slot_dates("W", None, ds) == set(ds)
    for w in (0, 1):
        assert len(contract_slot_dates("B", 0, wd[w])) == 2
        assert len(contract_slot_dates("B", 1, wd[w])) == 2
    for w in (2, 3, 4):
        even = contract_slot_dates("B", 0, wd[w])
        odd = contract_slot_dates("B", 1, wd[w])
        assert len(even) == 2 and len(odd) == 3
        assert even | odd == set(wd[w]) and not (even & odd)
    assert contract_slot_dates("B", 1, wd[2]) == \
        {date(2026, 7, 1), date(2026, 7, 15), date(2026, 7, 29)}


def test_contract_of_weekly_and_biweekly():
    from visit_ir.contract import contract_of
    dates = _july_workdays()
    mon = [d for d in dates if d.weekday() == 0]
    wed = [d for d in dates if d.weekday() == 2]
    days = {mon[0]: [0], mon[1]: [0], mon[2]: [0], mon[3]: [0],
            wed[0]: [1, 2], wed[2]: [1, 2], wed[4]: [1, 2],
            wed[1]: [2], wed[3]: [2]}
    ct = contract_of(days, dates)
    assert ct[0] == ("W", None)
    assert ct[1] == ("B", 1)
    assert ct[2] == ("W", None)


def test_check_contract_rejects_all_counterexamples():
    from visit_ir.contract import check_contract
    dates = _july_workdays()
    wed = [d for d in dates if d.weekday() == 2]
    thu = [d for d in dates if d.weekday() == 3]
    ct = {7: ("B", 1), 8: ("W", None)}
    good = {**{d: [7] for d in (wed[0], wed[2], wed[4])},
            **{d: [8] for d in thu}}
    assert check_contract(good, ct, dates) == []
    assert 7 in check_contract({wed[1]: [7], wed[3]: [7],
                                **{d: [8] for d in thu}}, ct, dates)
    bad2 = dict(good); bad2[wed[0]] = [8]; bad2[thu[0]] = [7, 8]
    assert 7 in check_contract(bad2, ct, dates)
    bad3 = {wed[0]: [7], wed[2]: [7], wed[4]: [], **{d: [8] for d in thu}}
    assert 7 in check_contract(bad3, ct, dates)
    bad4 = dict(good); bad4[wed[1]] = [7]
    assert 7 in check_contract(bad4, ct, dates)
    bad5 = dict(good); bad5[thu[0]] = []
    assert 8 in check_contract(bad5, ct, dates)


def test_calendar_property_2025_2029():
    from visit_ir.contract import contract_slot_dates
    for year in range(2025, 2030):
        for month in range(1, 13):
            first = date(year, month, 1)
            last = date(year + (month == 12), (month % 12) + 1, 1) - dt.timedelta(days=1)
            days = [first + dt.timedelta(days=i) for i in range((last - first).days + 1)
                    if (first + dt.timedelta(days=i)).weekday() < 5]
            for w in range(5):
                ds = [d for d in days if d.weekday() == w]
                if not ds:
                    continue
                even = contract_slot_dates("B", 0, ds)
                odd = contract_slot_dates("B", 1, ds)
                assert not (even & odd) and (even | odd) == set(ds)
                assert abs(len(odd) - len(even)) <= 1
    from visit_ir.contract import phase_of
def test_zero_solver_dependencies():
    """VisitIR 铁律: 语义核心零求解器/零 numpy 依赖 (AST 级 import 检查, 不看文案)."""
    import ast
    import inspect
    import visit_ir.contract as m
    tree = ast.parse(inspect.getsource(m))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    banned = {"ortools", "numpy", "pandas", "torch"}
    assert not (imported & banned), f"语义核心不得依赖 {imported & banned}"
