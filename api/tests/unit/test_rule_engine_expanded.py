"""
확장 Rule Engine 단위 테스트 — litter / grow-finish / abortion 규칙 + 임계 해석.
DB 없이 RuleContext를 직접 생성해 규칙 함수를 호출(국가 중립 로직, 임계만 조정).
"""
import asyncio
from uuid import uuid4

from app.engine.rule_engine import Finding, RuleContext, Severity
from app.engine.rules._common import resolve, sev_above, sev_below
from app.engine.rules.batch import _batch_aiao_detect
from app.engine.rules.boar import _boar_farrow_rate_low
from app.engine.rules.composite import _farm_health_class, _farm_weakest_kpi
from app.engine.rules.grow_finish import _adg_low, _fcr_high, _finish_mortality_high
from app.engine.rules.litter import (
    _born_alive_low,
    _crushing_rate_high,
    _death_age_skew,
    _lactation_long,
    _lactation_short,
    _mummified_high,
    _stillborn_high,
    _total_born_low,
    _weaned_low,
)
from app.engine.rules.loss import (
    _loss_npd,
    _loss_pregnancy_accident,
    _loss_preweaning,
    _loss_sow_culling,
)
from app.engine.rules.reproduction import (
    _abortion_rate_high,
    _conception_rate_low,
    _summer_infertility,
)
from app.engine.rules.sow_herd import (
    _accident_parity_skew,
    _culling_rate_high,
    _msy_below_bep,
    _parity_high_ratio,
    _replacement_rate_abnormal,
    _second_litter_slump,
    _sow_mortality_high,
)


def ctx(kpi: dict, rule_configs: dict | None = None, benchmarks: dict | None = None) -> RuleContext:
    return RuleContext(
        farm_id=uuid4(), country="KR", kpi=kpi,
        benchmarks=benchmarks or {}, sow_counts={"OPEN": 50},
        extra={"rule_configs": rule_configs or {}},
    )


def run(coro):
    return asyncio.run(coro)


# ── severity 헬퍼 ───────────────────────────────────────────────────────────────
class TestSeverityHelpers:
    def test_above(self):
        assert sev_above(5.0, 8.0, 12.0) is None
        assert sev_above(9.0, 8.0, 12.0) == Severity.WARNING
        assert sev_above(13.0, 8.0, 12.0) == Severity.CRITICAL

    def test_below(self):
        assert sev_below(12.0, 11.0, 10.0) is None
        assert sev_below(10.5, 11.0, 10.0) == Severity.WARNING
        assert sev_below(9.0, 11.0, 10.0) == Severity.CRITICAL


# ── 임계 해석 우선순위: rule_config > benchmark > code default ──────────────────
class TestResolvePrecedence:
    def test_code_default_when_nothing(self):
        assert resolve(ctx({}), "stillborn.rate_high", "STILLBORN_RATE", 8.0, 12.0) == (8.0, 12.0)

    def test_benchmark_overrides_default(self):
        c = ctx({}, benchmarks={"STILLBORN_RATE": {"warning": 6.0, "critical": 9.0}})
        assert resolve(c, "stillborn.rate_high", "STILLBORN_RATE", 8.0, 12.0) == (6.0, 9.0)

    def test_rule_config_wins_over_benchmark(self):
        c = ctx({}, rule_configs={"stillborn.rate_high": {"warning": 5.0, "critical": 7.0}},
                benchmarks={"STILLBORN_RATE": {"warning": 6.0, "critical": 9.0}})
        assert resolve(c, "stillborn.rate_high", "STILLBORN_RATE", 8.0, 12.0) == (5.0, 7.0)


# ── litter 규칙 ─────────────────────────────────────────────────────────────────
class TestLitterRules:
    def test_stillborn_none_when_normal(self):
        assert run(_stillborn_high(ctx({"STILLBORN_RATE": 5.0}))) == []

    def test_stillborn_warning(self):
        f = run(_stillborn_high(ctx({"STILLBORN_RATE": 10.0})))
        assert f and f[0].severity == Severity.WARNING

    def test_stillborn_critical(self):
        f = run(_stillborn_high(ctx({"STILLBORN_RATE": 15.0})))
        assert f and f[0].severity == Severity.CRITICAL

    def test_mummified_critical(self):
        f = run(_mummified_high(ctx({"MUMMIFIED_RATE": 5.0})))
        assert f and f[0].severity == Severity.CRITICAL

    def test_born_alive_low_below(self):
        f = run(_born_alive_low(ctx({"BORN_ALIVE": 9.5})))
        assert f and f[0].severity == Severity.CRITICAL

    def test_born_alive_ok(self):
        assert run(_born_alive_low(ctx({"BORN_ALIVE": 12.0}))) == []

    def test_weaned_low_warning(self):
        f = run(_weaned_low(ctx({"WEANED_COUNT": 9.5})))
        assert f and f[0].severity == Severity.WARNING

    def test_lactation_short(self):
        f = run(_lactation_short(ctx({"WEANING_AGE": 17.0})))
        assert f and f[0].severity == Severity.WARNING

    def test_lactation_long(self):
        f = run(_lactation_long(ctx({"WEANING_AGE": 30.0})))
        assert f and f[0].severity == Severity.WARNING

    def test_missing_kpi_no_finding(self):
        assert run(_stillborn_high(ctx({}))) == []
        assert run(_weaned_low(ctx({}))) == []

    def test_crushing_rate(self):
        assert run(_crushing_rate_high(ctx({"CRUSHING_RATE": 4.0}))) == []      # ok
        f = run(_crushing_rate_high(ctx({"CRUSHING_RATE": 8.0})))               # >6 warn
        assert f and f[0].severity == Severity.WARNING
        f2 = run(_crushing_rate_high(ctx({"CRUSHING_RATE": 12.0})))             # >10 crit
        assert f2 and f2[0].severity == Severity.CRITICAL

    def test_death_age_skew(self):
        assert run(_death_age_skew(ctx({"DEATH_AGE_0_3_RATIO": 60.0}))) == []   # ok
        f = run(_death_age_skew(ctx({"DEATH_AGE_0_3_RATIO": 75.0})))            # >70 warn
        assert f and f[0].severity == Severity.WARNING
        f2 = run(_death_age_skew(ctx({"DEATH_AGE_0_3_RATIO": 85.0})))           # >80 crit
        assert f2 and "possible_farrowing_management_or_low_vitality_piglets" in f2[0].causes


# ── grow-finish 규칙 ────────────────────────────────────────────────────────────
class TestGrowFinishRules:
    def test_fcr_high_warning(self):
        f = run(_fcr_high(ctx({"FCR": 3.1})))
        assert f and f[0].severity == Severity.WARNING

    def test_fcr_high_critical(self):
        f = run(_fcr_high(ctx({"FCR": 3.5})))
        assert f and f[0].severity == Severity.CRITICAL

    def test_fcr_ok(self):
        assert run(_fcr_high(ctx({"FCR": 2.7}))) == []

    def test_adg_low_critical(self):
        f = run(_adg_low(ctx({"ADG": 500.0})))
        assert f and f[0].severity == Severity.CRITICAL

    def test_finish_mortality_high(self):
        f = run(_finish_mortality_high(ctx({"FINISH_MORTALITY": 9.0})))
        assert f and f[0].severity == Severity.CRITICAL


# ── abortion 규칙 ───────────────────────────────────────────────────────────────
class TestAbortionRule:
    def test_abortion_ok(self):
        assert run(_abortion_rate_high(ctx({"ABORTION_RATE": 2.0}))) == []

    def test_abortion_warning(self):
        f = run(_abortion_rate_high(ctx({"ABORTION_RATE": 4.0})))
        assert f and f[0].severity == Severity.WARNING

    def test_abortion_critical_has_disease_cause(self):
        f = run(_abortion_rate_high(ctx({"ABORTION_RATE": 6.0})))
        assert f and f[0].severity == Severity.CRITICAL
        assert "possible_abortive_disease" in f[0].causes


# ── 모돈군 구조 규칙 ────────────────────────────────────────────────────────────
class TestSowHerdRules:
    def test_culling_ok(self):
        assert run(_culling_rate_high(ctx({"CULLING_RATE": 40.0}))) == []

    def test_culling_warning(self):
        f = run(_culling_rate_high(ctx({"CULLING_RATE": 50.0})))
        assert f and f[0].severity == Severity.WARNING

    def test_culling_critical(self):
        f = run(_culling_rate_high(ctx({"CULLING_RATE": 60.0})))
        assert f and f[0].severity == Severity.CRITICAL

    def test_sow_mortality_critical(self):
        f = run(_sow_mortality_high(ctx({"SOW_MORTALITY": 13.0})))
        assert f and f[0].severity == Severity.CRITICAL

    def test_parity_high_ratio_warning(self):
        f = run(_parity_high_ratio(ctx({"HIGH_PARITY_RATIO": 25.0})))
        assert f and f[0].severity == Severity.WARNING

    def test_total_born_low(self):
        f = run(_total_born_low(ctx({"TOTAL_BORN": 10.5})))
        assert f and f[0].severity == Severity.CRITICAL

    def test_missing_no_finding(self):
        assert run(_culling_rate_high(ctx({}))) == []
        assert run(_parity_high_ratio(ctx({}))) == []

    def test_msy_below_bep(self):
        assert run(_msy_below_bep(ctx({"MSY": 20.0}))) == []                # ok
        f = run(_msy_below_bep(ctx({"MSY": 16.0})))                         # <17 warn
        assert f and f[0].severity == Severity.WARNING
        f2 = run(_msy_below_bep(ctx({"MSY": 14.0})))                        # <15 crit
        assert f2 and f2[0].severity == Severity.CRITICAL
        assert run(_msy_below_bep(ctx({}))) == []                          # 출하데이터 없음

    def test_batch_detect(self):
        assert run(_batch_aiao_detect(ctx({"BATCH_DOW_CONCENTRATION": 35.0}))) == []   # 비배치
        f = run(_batch_aiao_detect(ctx({"BATCH_DOW_CONCENTRATION": 60.0})))            # 집중→배치 INFO
        assert f and f[0].severity == Severity.INFO
        assert run(_batch_aiao_detect(ctx({}))) == []                                  # 표본 부족


# ── Phase B2: herd dynamics 탐지 규칙 ───────────────────────────────────────────
class TestHerdDynamicsRules:
    def test_replacement_high_warning(self):
        f = run(_replacement_rate_abnormal(ctx({"REPLACEMENT_RATE": 55.0})))
        assert f and f[0].severity == Severity.WARNING and "excessive_sow_replacement" in f[0].causes

    def test_replacement_high_critical(self):
        f = run(_replacement_rate_abnormal(ctx({"REPLACEMENT_RATE": 65.0})))
        assert f and f[0].severity == Severity.CRITICAL

    def test_replacement_low_warning(self):
        f = run(_replacement_rate_abnormal(ctx({"REPLACEMENT_RATE": 25.0})))
        assert f and "insufficient_sow_replacement" in f[0].causes

    def test_replacement_ok(self):
        assert run(_replacement_rate_abnormal(ctx({"REPLACEMENT_RATE": 40.0}))) == []

    def test_second_litter_slump(self):
        assert run(_second_litter_slump(ctx({"SECOND_LITTER_DROP": 1.0}))) == []
        f = run(_second_litter_slump(ctx({"SECOND_LITTER_DROP": 2.0})))
        assert f and f[0].severity == Severity.WARNING
        f2 = run(_second_litter_slump(ctx({"SECOND_LITTER_DROP": 3.0})))
        assert f2 and f2[0].severity == Severity.CRITICAL

    def test_accident_parity_skew(self):
        assert run(_accident_parity_skew(ctx({"ACCIDENT_P1_RATIO": 30.0}))) == []
        f = run(_accident_parity_skew(ctx({"ACCIDENT_P1_RATIO": 45.0})))
        assert f and f[0].severity == Severity.WARNING
        f2 = run(_accident_parity_skew(ctx({"ACCIDENT_P1_RATIO": 60.0})))
        assert f2 and "possible_reproductive_disease_in_gilts" in f2[0].causes

    def test_summer_infertility(self):
        assert run(_summer_infertility(ctx({"SUMMER_FARROW_DROP": 4.0}))) == []
        f = run(_summer_infertility(ctx({"SUMMER_FARROW_DROP": 8.0})))
        assert f and f[0].severity == Severity.WARNING
        f2 = run(_summer_infertility(ctx({"SUMMER_FARROW_DROP": 12.0})))
        assert f2 and f2[0].severity == Severity.CRITICAL

    def test_missing_no_finding(self):
        assert run(_replacement_rate_abnormal(ctx({}))) == []
        assert run(_summer_infertility(ctx({}))) == []

    def test_conception_rate(self):
        assert run(_conception_rate_low(ctx({"CONCEPTION_RATE": 90.0}))) == []   # ok
        f = run(_conception_rate_low(ctx({"CONCEPTION_RATE": 83.0})))            # <85 warn
        assert f and f[0].severity == Severity.WARNING
        f2 = run(_conception_rate_low(ctx({"CONCEPTION_RATE": 78.0})))           # <80 crit
        assert f2 and f2[0].severity == Severity.CRITICAL
        assert run(_conception_rate_low(ctx({}))) == []                         # 데이터 없음


# ── Phase B4: 웅돈별 분만율(멀티개체) ────────────────────────────────────────────
class TestBoarRule:
    def _ctx(self, boar_stats):
        return RuleContext(farm_id=uuid4(), country="KR", kpi={}, benchmarks={},
                           sow_counts={}, extra={"rule_configs": {}, "boar_stats": boar_stats})

    def test_no_boars(self):
        assert run(_boar_farrow_rate_low(self._ctx([]))) == []

    def test_low_boar_flagged(self):
        stats = [{"boar_id": "b1", "ear_tag": "B-1", "matings": 20, "fr": 60.0},   # warn (<65)
                 {"boar_id": "b2", "ear_tag": "B-2", "matings": 15, "fr": 50.0},   # crit (<55)
                 {"boar_id": "b3", "ear_tag": "B-3", "matings": 30, "fr": 88.0}]   # ok
        out = run(_boar_farrow_rate_low(self._ctx(stats)))
        assert len(out) == 2
        sev = {f.detail["ear_tag"]: f.severity for f in out}
        assert sev["B-1"] == Severity.WARNING and sev["B-2"] == Severity.CRITICAL


# ── Phase B1: 손실계산기 (실 count × 단가, 위조 0) ──────────────────────────────
class TestLossRules:
    def _ctx(self, loss_inputs, kpi=None):
        return RuleContext(farm_id=uuid4(), country="KR", kpi=kpi or {}, benchmarks={},
                           sow_counts={}, extra={"loss_inputs": loss_inputs})

    def test_no_price_no_loss(self):
        c = self._ctx({"price": None, "pw_deaths": 50})
        assert run(_loss_preweaning(c)) == []

    def test_preweaning_loss(self):
        c = self._ctx({"price": 300000, "currency": "KRW", "demo": False, "pw_deaths": 40})
        f = run(_loss_preweaning(c))
        assert f and f[0].detail["loss"]["amount"] == 40 * 300000
        assert f[0].detail["loss"]["demo"] is False

    def test_pregnancy_accident_loss(self):
        c = self._ctx({"price": 300000, "currency": "KRW", "demo": True, "accident_count": 5},
                      kpi={"WEANED_COUNT": 11.0})
        f = run(_loss_pregnancy_accident(c))
        assert f and f[0].detail["loss"]["amount"] == round(5 * 11.0 * 300000)

    def test_accident_loss_needs_per_litter(self):
        c = self._ctx({"price": 300000, "accident_count": 5}, kpi={})  # no WEANED_COUNT
        assert run(_loss_pregnancy_accident(c)) == []

    def test_npd_loss(self):
        c = self._ctx({"price": 365000, "currency": "KRW", "demo": False, "wei_total_days": 100},
                      kpi={"PSY": 25.0, "BORN_ALIVE": 12.0, "WEANED_COUNT": 12.0})
        f = run(_loss_npd(c))
        # per_sow_day = 25 * 1.0 * 365000/365 = 25000; ×100 = 2,500,000
        assert f and f[0].detail["loss"]["amount"] == 2_500_000

    def test_npd_loss_needs_inputs(self):
        c = self._ctx({"price": 365000, "wei_total_days": 0}, kpi={"PSY": 25.0})
        assert run(_loss_npd(c)) == []

    def test_sow_culling_loss(self):
        bench = {f"SOW_RESIDUAL_P{p}": {"target": v, "unit": "KRW"} for p, v in
                 {0: 8400000, 1: 7100000, 2: 5800000, 3: 4500000, 4: 3300000, 5: 1950000, 6: 800000}.items()}
        bench["SOW_SALVAGE_CULL"] = {"target": 300000}
        bench["SOW_SALVAGE_DEATH"] = {"target": 0}
        c = RuleContext(farm_id=uuid4(), country="KR", kpi={}, benchmarks=bench, sow_counts={},
                        extra={"loss_inputs": {"cull_by_parity": [
                            {"status": "CULLED", "parity": 2, "count": 1},   # 5.8M-0.3M=5.5M
                            {"status": "DEAD", "parity": 1, "count": 1},     # 7.1M-0=7.1M
                            {"status": "CULLED", "parity": 8, "count": 1}]}})  # 7+ → 0
        f = run(_loss_sow_culling(c))
        assert f and f[0].detail["loss"]["amount"] == 5_500_000 + 7_100_000
        assert f[0].current_value == 2  # 8산 제외

    def test_sow_culling_no_seed_no_fire(self):
        c = RuleContext(farm_id=uuid4(), country="US", kpi={}, benchmarks={}, sow_counts={},
                        extra={"loss_inputs": {"cull_by_parity": [{"status": "CULLED", "parity": 2, "count": 5}]}})
        assert run(_loss_sow_culling(c)) == []


# ── Phase B3: 종합 룰(롤업, 위조 0) ──────────────────────────────────────────────
class TestCompositeRules:
    def _ctx(self, prior):
        return RuleContext(farm_id=uuid4(), country="KR", kpi={}, benchmarks={},
                           sow_counts={}, extra={"_prior_findings": prior})

    def _f(self, sev, rule_id="x.y", kpi="K", gap=0.0):
        return Finding(rule_id=rule_id, kpi=kpi, severity=sev, current_value=1.0,
                       target_value=1.0, detail={"normalized_gap": gap})

    def test_green_when_no_issues(self):
        f = run(_farm_health_class(self._ctx([])))
        assert f[0].grade == "GREEN"

    def test_yellow_one_warning(self):
        f = run(_farm_health_class(self._ctx([self._f(Severity.WARNING)])))
        assert f[0].grade == "YELLOW"

    def test_red_on_critical(self):
        f = run(_farm_health_class(self._ctx([self._f(Severity.CRITICAL)])))
        assert f[0].grade == "RED" and f[0].severity == Severity.CRITICAL

    def test_red_on_three_warnings(self):
        f = run(_farm_health_class(self._ctx([self._f(Severity.WARNING)] * 3)))
        assert f[0].grade == "RED"

    def test_weakest_picks_critical_highest_gap(self):
        prior = [self._f(Severity.WARNING, "a", "A", 0.5),
                 self._f(Severity.CRITICAL, "b", "B", 0.2),
                 self._f(Severity.CRITICAL, "c", "C", 0.8)]
        f = run(_farm_weakest_kpi(self._ctx(prior)))
        assert f and f[0].detail["weakest_kpi"] == "C"

    def test_weakest_none_when_all_ok(self):
        assert run(_farm_weakest_kpi(self._ctx([self._f(Severity.INFO)]))) == []


# ── 운영자 임계 조정 반영(국가별 KPI 조정 구조) ────────────────────────────────
class TestOperatorOverride:
    def test_operator_tightens_threshold(self):
        # 기본 8.0이면 7.0은 정상이지만, 운영자가 6.0으로 조이면 경고
        assert run(_stillborn_high(ctx({"STILLBORN_RATE": 7.0}))) == []
        c = ctx({"STILLBORN_RATE": 7.0},
                rule_configs={"stillborn.rate_high": {"warning": 6.0, "critical": 9.0}})
        f = run(_stillborn_high(c))
        assert f and f[0].severity == Severity.WARNING
