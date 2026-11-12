"""GitHub Actions 스케줄 게이트 — 매일 정해진 시각(기본 KST 11:29)에 한 번만 크롤러를 실행한다.

배경
  GitHub Actions의 schedule 이벤트는 '최선 노력(best effort)'이라 정각 cron이 몇 시간씩
  밀릴 수 있다. 실제로 `0 2 * * *`(KST 11:00) 스케줄이 2026-03엔 13시경, 2026-11엔
  17시경 시작될 만큼 지연이 계속 커졌다.

해결
  워크플로는 새벽부터 30분 간격으로 여러 번 트리거되고, 이 게이트가 각 실행마다 판단한다.
    - 오늘 이미 전송했으면           → skip
    - 목표 시각 - window 보다 이르면 → skip (다음 트리거에 맡김)
    - 목표 시각 직전 window 안이면   → 목표 시각까지 대기 후 실행
    - 목표 시각이 지났으면           → 즉시 실행 (지연 시에도 최대한 빨리)
  트리거가 어느 정도 지연되든 그중 하나는 목표 시각 직전 window에 도착하므로
  알림이 거의 정확히 목표 시각에 도착한다.

stdlib만 사용 (의존성 설치 전에 실행되므로).
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone

# 한국은 서머타임이 없으므로 고정 오프셋 사용 (tzdata 불필요)
KST = timezone(timedelta(hours=9), "KST")


@dataclass(frozen=True)
class Decision:
    proceed: bool
    run_at_epoch: int   # 이 시각(epoch 초)까지 대기 후 실행. 0이면 즉시
    reason: str


def parse_hhmm(value: str) -> time:
    hour, minute = value.strip().split(":")
    return time(int(hour), int(minute))


def decide(
    now: datetime,
    run_at: time,
    window: timedelta,
    already_sent: bool,
    force: bool = False,
) -> Decision:
    """현재 시각과 오늘 전송 여부로 실행/대기/스킵을 결정"""
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    now_kst = now.astimezone(KST)

    if force:
        return Decision(True, 0, "수동 실행(force) — 시간/중복 검사 생략")
    if already_sent:
        return Decision(False, 0, f"{now_kst:%Y-%m-%d} 이미 전송 완료")

    target = datetime.combine(now_kst.date(), run_at, tzinfo=KST)
    if now_kst < target - window:
        return Decision(False, 0, f"너무 이름 ({now_kst:%H:%M} < {target - window:%H:%M}) — 다음 트리거에 맡김")
    if now_kst < target:
        return Decision(True, int(target.timestamp()), f"{target:%H:%M}까지 대기 후 실행")
    return Decision(True, 0, f"목표 시각 {target:%H:%M} 경과 — 즉시 실행")


def _flag(value: str | None) -> bool:
    return (value or "").strip().lower() in ("1", "true", "yes", "on")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run-at", default="11:29", help="목표 실행 시각 (KST, HH:MM)")
    parser.add_argument("--window-minutes", type=int, default=60, help="목표 시각 전 대기 허용 구간(분)")
    parser.add_argument("--already-sent", default="false")
    parser.add_argument("--force", default="false")
    parser.add_argument("--print-date", action="store_true", help="오늘 KST 날짜(YYYYMMDD)만 출력")
    args = parser.parse_args(argv)

    now = datetime.now(timezone.utc)
    if args.print_date:
        print(now.astimezone(KST).strftime("%Y%m%d"))
        return 0

    decision = decide(
        now,
        parse_hhmm(args.run_at),
        timedelta(minutes=args.window_minutes),
        already_sent=_flag(args.already_sent),
        force=_flag(args.force),
    )
    print(f"[gate] now={now.astimezone(KST):%Y-%m-%d %H:%M:%S} KST proceed={decision.proceed} — {decision.reason}")

    output = os.getenv("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as f:
            f.write(f"proceed={'true' if decision.proceed else 'false'}\n")
            f.write(f"run_at_epoch={decision.run_at_epoch}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
