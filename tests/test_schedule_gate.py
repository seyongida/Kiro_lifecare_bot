"""scripts/schedule_gate.py — 매일 목표 시각 1회 실행 게이트 테스트"""
from datetime import datetime, time, timedelta, timezone

import hypothesis.strategies as st
import pytest
from hypothesis import given, settings

from scripts.schedule_gate import KST, decide, main, parse_hhmm

RUN_AT = time(11, 29)
WINDOW = timedelta(minutes=60)


def kst(h, mi, s=0, day=12):
    return datetime(2026, 11, day, h, mi, s, tzinfo=KST)


def test_too_early_is_skipped():
    d = decide(kst(9, 7), RUN_AT, WINDOW, already_sent=False)
    assert not d.proceed


def test_inside_window_waits_until_run_at():
    d = decide(kst(10, 37), RUN_AT, WINDOW, already_sent=False)
    assert d.proceed
    assert d.run_at_epoch == int(kst(11, 29).timestamp())


def test_window_start_is_inclusive():
    assert decide(kst(10, 29), RUN_AT, WINDOW, already_sent=False).proceed


def test_late_run_executes_immediately():
    """GitHub 스케줄이 크게 지연돼도(실측 17시경) 그날 한 번은 반드시 실행"""
    d = decide(kst(17, 20), RUN_AT, WINDOW, already_sent=False)
    assert d.proceed and d.run_at_epoch == 0


def test_already_sent_is_skipped_even_when_late():
    assert not decide(kst(17, 20), RUN_AT, WINDOW, already_sent=True).proceed


def test_force_ignores_time_and_marker():
    d = decide(kst(4, 0), RUN_AT, WINDOW, already_sent=True, force=True)
    assert d.proceed and d.run_at_epoch == 0


def test_utc_input_is_converted_to_kst():
    # 02:00 UTC == 11:00 KST → 대기 구간
    now = datetime(2026, 11, 12, 2, 0, tzinfo=timezone.utc)
    d = decide(now, RUN_AT, WINDOW, already_sent=False)
    assert d.proceed and d.run_at_epoch == int(kst(11, 29).timestamp())


def test_naive_datetime_rejected():
    with pytest.raises(ValueError):
        decide(datetime(2026, 11, 12, 11, 0), RUN_AT, WINDOW, already_sent=False)


def test_parse_hhmm():
    assert parse_hhmm(" 11:29 ") == time(11, 29)


@given(st.integers(min_value=0, max_value=24 * 60 * 60 - 1))
@settings(max_examples=200)
def test_never_waits_longer_than_window(seconds_of_day):
    now = kst(0, 0) + timedelta(seconds=seconds_of_day)
    d = decide(now, RUN_AT, WINDOW, already_sent=False)
    if d.proceed and d.run_at_epoch:
        wait = d.run_at_epoch - now.timestamp()
        assert 0 < wait <= WINDOW.total_seconds()


def test_cron_schedule_covers_window_for_any_delay():
    """워크플로의 30분 간격 트리거라면 지연이 0~8시간 어디든 목표 시각 직전 구간에 도착하는 실행이 있다"""
    triggers = [kst(3, 7) + timedelta(minutes=30 * i) for i in range(17)]  # KST 03:07 ~ 11:07
    assert triggers[-1] == kst(11, 7)
    for delay_min in range(0, 8 * 60 + 1, 5):
        arrivals = [t + timedelta(minutes=delay_min) for t in triggers]
        waiting = [a for a in arrivals if decide(a, RUN_AT, WINDOW, already_sent=False).run_at_epoch]
        on_time = [a for a in arrivals if kst(11, 29) <= a < kst(11, 59)]
        assert waiting or on_time, f"delay={delay_min}분이면 11:29 직전/직후 도착 실행 없음"


def test_cli_writes_github_output(tmp_path, monkeypatch, capsys):
    out = tmp_path / "out"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    assert main(["--force", "true"]) == 0
    assert out.read_text() == "proceed=true\nrun_at_epoch=0\n"


def test_cli_print_date(capsys):
    assert main(["--print-date"]) == 0
    printed = capsys.readouterr().out.strip()
    assert len(printed) == 8 and printed.isdigit()
