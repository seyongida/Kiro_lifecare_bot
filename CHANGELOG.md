# Changelog

## [0.9.1] - 2026-03-20

### 변경사항
- `.github/workflows/scrape.yml`: 디버그용 step 2개 추가 (`if: always()`로 실패 시에도 실행)
  - 스크린샷 크기 확인: Pillow로 이미지 width×height, 파일 크기(KB) 출력
  - `actions/upload-artifact@v4`로 `screenshots/` 폴더를 artifact로 업로드 (3일 보관)
  - `Photo_invalid_dimensions` 원인 파악을 위한 임시 디버그 조치

## [0.9.0] - 2026-03-20

### 문서
- `.kiro/specs/lg-lifecare-scraper/design.md` 실제 구현 기준으로 전면 수정
  - Overview: "페이지네이션 신규 추가" 문구 제거, 실제 구현 기준 서술로 변경
  - 핵심 설계 결정: URL 페이지네이션 전략 → 더보기 버튼 클릭 DOM 누적 로드 전략으로 교체, SSL 우회 항목 추가
  - Architecture 다이어그램: `scrape_products` 흐름을 더보기 버튼 클릭 루프 구조로 재작성
  - `scrape_products` 인터페이스: URL 페이지네이션 루프 → 더보기 버튼 클릭 루프 의사코드로 교체
  - `send_telegram` 인터페이스: `HTTPXRequest(verify=False)` SSL 우회 명세 추가
  - Data Models: 스크린샷 파일명 패턴에 `full_page=False` 뷰포트 캡처 주의사항 추가
  - Correctness Properties: Property 1·2를 URL 기반 → 더보기 버튼 DOM 증가/루프 종료 속성으로 교체
  - Testing Strategy: 속성 기반 테스트 표에서 `test_pagination_url_format` → `test_more_btn_loop_termination`으로 교체
- `.kiro/specs/lg-lifecare-scraper/tasks.md` 신규 생성 — 테스트 작성 구현 계획
  - 태스크 1: `pyproject.toml`에 `pytest`, `hypothesis` 의존성 추가
  - 태스크 2: `tests/test_main.py` 단위 테스트 (빈 상품 목록, 패턴 불일치 순서 보존)
  - 태스크 3: Hypothesis 속성 기반 테스트 6개 (Property 2~7, 각 100회 반복)
  - 태스크 4: 전체 테스트 통과 확인 체크포인트

## [0.8.3] - 2026-03-20

### 문서
- `.kiro/specs/lg-lifecare-scraper/requirements.md` 실제 구현 기준으로 업데이트
  - Requirement 2: URL `&page=N` 페이지네이션 방식 → 더보기 버튼 클릭으로 DOM 누적 로드 후 JS evaluate 한 번에 수집하는 방식으로 전면 수정
  - Requirement 3: "전체 페이지 스크린샷" → 뷰포트 캡처(`full_page=False`) 명세로 수정
  - Requirement 5: 회사 네트워크 self-signed SSL 인증서 우회(`HTTPXRequest(verify=False)`) 항목 추가
  - Introduction 및 Glossary의 더보기 버튼 설명을 실제 동작(DOM 누적 로드)에 맞게 수정

## [0.8.2] - 2026-03-20

### 버그 수정
- `main.py`: 스크린샷 `full_page=True` → `full_page=False` 변경
  - full_page 캡처 시 이미지 높이가 텔레그램 제한 초과 → `Photo_invalid_dimensions` 에러 수정

### 변경사항
- `.github/workflows/scrape.yml`: `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true` 환경변수 추가
  - `actions/checkout@v4`, `actions/setup-python@v5`의 Node.js 20 deprecation 경고 해결

## [0.8.1] - 2026-03-20

### 버그 수정
- `login()`, `scrape_products()`: `wait_for_load_state("networkidle")` → `"domcontentloaded"` 로 변경
  - 회사 네트워크 환경에서 networkidle 상태 미도달로 인한 30초 타임아웃 오류 해결
- `send_telegram()`: 회사 네트워크 self-signed 인증서로 인한 SSL 검증 실패 해결
  - `HTTPXRequest(httpx_kwargs={"verify": False})` 옵션으로 Bot 초기화

### 추가
- `from telegram.request import HTTPXRequest` import 추가

## [0.8.0] - 2026-03-20

### 추가
- `.github/workflows/scrape.yml` 신규 생성 — GitHub Actions 자동 실행 설정
  - 매일 KST 09:00 cron 스케줄 실행 (`0 0 * * *`)
  - `workflow_dispatch`로 수동 실행 버튼 활성화
  - `ubuntu-latest` 환경에서 Python 3.11 + Playwright Chromium 설치 후 `main.py` 실행
  - `.env` 값 5개를 GitHub Secrets(`LG_ID`, `LG_PW`, `TARGET_URL`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`)로 주입

### 변경사항
- `main.py`: `p.chromium.launch(channel="chromium")` → `p.chromium.launch()` 로 복원
  - `channel="chromium"` 은 Windows 로컬 전용 옵션으로 Linux(GitHub Actions)에서 불필요

## [0.7.2] - 2026-03-19

### 삭제
- 개발/디버깅용 임시 파일 전체 삭제
  - `_tmp_quick.py`, `_tmp_login_only.py`, `_tmp_test_more.py`
  - `_tmp_debug_pages.py`, `_tmp_scrape_only.py`
  - `_test_pagination.py`, `_test_all_pages.py`
  - `_pagination_result.txt`, `_all_pages_result.txt`

## [0.7.1] - 2026-03-19

### 변경사항
- `README.md` 실행 방법 업데이트
  - 의존성 설치: `uv sync` 명령으로 단순화
  - Playwright 브라우저 설치: `.venv\Scripts\python.exe -m playwright install chromium`으로 변경
  - 실행 명령: `uv run --with ...` 방식 → `.venv\Scripts\python.exe main.py`로 변경
  - 사내망 텔레그램 차단 환경 주의사항 추가

## [0.7.0] - 2026-03-19

### 변경사항
- `scrape_products()`: 수집 방식 재검증 후 더보기 버튼 클릭 방식으로 최종 확정
  - `&page=N` URL 파라미터는 서버에서 무시됨을 실제 실행으로 재확인 (항상 1페이지 40개 반환)
  - 더보기 버튼 클릭 시 DOM에 상품이 누적되는 구조 확인 (40 → 80 → 120 → 145개)
  - `wait_for_function`으로 DOM 증가 감지 후 수집하는 방식으로 복원
  - 실행 결과: 총 145개 중 145개 정상 수집 확인
- `main()`: `p.chromium.launch(channel="chromium")` 추가
  - `headless_shell` 실행 시 `EPERM` 권한 오류 발생 → 일반 Chromium으로 전환
- `pyproject.toml` 신규 생성 — `uv sync` 기반 의존성 관리를 위해 추가
  - `playwright==1.49.1`, `python-dotenv==1.0.1`, `python-telegram-bot==21.9` 명시

### 실행 환경 이슈
- 텔레그램 전송 실패: 회사 네트워크에서 `api.telegram.org` 차단으로 `ConnectError` 발생
  - 스크래핑 로직 자체는 정상 — VPN 또는 외부 네트워크 환경에서 실행 필요

## [0.6.0] - 2026-03-19

### 변경사항
- `scrape_products()`: 페이지네이션 방식 재교체
  - 기존: 더보기 버튼 클릭 방식 — 클릭 시 DOM이 새 40개로 교체되어 이전 상품이 사라지는 구조적 문제로 항상 40개만 수집
  - 변경: `&page=N` URL 파라미터 순회 방식으로 전환
  - 각 페이지 상품을 `all_products` 리스트에 누적
  - `seen_names` set으로 중복 상품 감지 및 조기 종료 처리
  - 더보기 버튼(`button.btn_more_down`) 미노출 시 마지막 페이지로 판단하여 종료
  - 결과: 140여 개 전체 상품 정상 수집 및 텔레그램 전송

## [0.5.0] - 2026-03-19

### 변경사항
- `scrape_products()`: 페이지네이션 방식 전면 교체
  - 기존: `&page=N` URL 파라미터 순회 방식 (서버에서 무시되어 항상 동일한 40개 반환 → 무한 루프 버그)
  - 변경: `button.btn_more_down` 클릭 방식으로 전체 상품 로드
  - 더보기 버튼 클릭 후 DOM 상품 수 증가 감지(`wait_for_function`)로 로드 완료 대기
  - 버튼이 사라지거나 타임아웃 시 수집 종료
  - 전체 상품을 DOM에 로드한 뒤 한 번에 수집

## [0.4.0] - 2026-03-19

### 추가
- `.kiro/specs/lg-lifecare-scraper/design.md` 신규 생성 — 아키텍처 설계 문서화
  - 전체 실행 흐름 Mermaid 다이어그램
  - 각 함수 인터페이스 및 페이지네이션 루프 설계 (`scrape_products` 신규 로직)
  - 데이터 모델 및 환경 변수 명세
  - 정확성 속성(Correctness Properties) 7개 정의
  - Hypothesis 기반 속성 기반 테스트 전략 및 예시

## [0.3.0] - 2026-03-19

### 추가
- `.kiro/specs/lg-lifecare-scraper/requirements.md` 신규 생성 — 현재 구현 기능 전체를 EARS 패턴 요구사항으로 문서화
  - Requirement 1: 사번 로그인
  - Requirement 2: 전체 페이지 상품 수집 (페이지네이션 포함 — 신규 요구사항)
  - Requirement 3: 전체 페이지 스크린샷 저장
  - Requirement 4: 상품 목록 포맷팅
  - Requirement 5: 텔레그램 전송
  - Requirement 6: 에러 처리
- `_test_pagination.py` 신규 생성 — 페이지네이션 구조 탐색 스크립트 (`.btn_more_down` 버튼 및 `&page=N` URL 파라미터 확인)
- `_pagination_result.txt` 신규 생성 — 페이지네이션 탐색 결과 (40개 상품, 더보기 버튼 확인)

## [0.2.3] - 2026-03-19

### 변경사항
- `format_products()`: 텔레그램 메시지 포맷 개선
  - 헤더를 `총 {사이트전체}개 중 {수집}개 수집 (품절 제외)` 형식으로 변경 (실제 수집 개수와 사이트 전체 개수 구분)
  - 두 번째 라인에 `TARGET_URL` 추가
  - 정렬 기준 변경: 기존 등급 기준 → 종류 기준 1차 그룹핑 후 가격 오름차순 2차 정렬

## [0.2.2] - 2026-03-19

### 변경사항
- `README.md` 업데이트 — `pip install` 방식에서 `uv run` 방식으로 실행 명령 수정
  - uv 설치 방법 안내 추가
  - Playwright Chromium 브라우저 최초 설치 명령 추가
  - 텔레그램 봇 준비 방법(BotFather, chat_id 확인) 가이드 추가
  - 실행 명령을 `uv run --with ...` 형식으로 변경

## [0.2.1] - 2026-03-19

### 변경사항
- `README.md` 신규 생성 — 프로젝트 개요, 동작 흐름, 설치/설정/실행 방법 문서화

## [0.2.0] - 2026-03-19

### 변경사항
- `login()`: 실제 사이트 셀렉터에 맞게 로그인 로직 전면 수정
  - 사번 입력: `input#id[name="id"]`, 비밀번호: `input[name="password"]`
  - 사번 로그인 버튼: `button.again-btn_bg_gradient` (MY LG ID 버튼과 구분)
  - 로그인 후 `todayClosePop` 팝업 자동 닫기 처리 추가
- `scrape_products()`: 기존 Selenium 스크립트 기반으로 셀렉터 교체
  - 상품 요소: `.nhm-item`
  - 상품명: `.tit_cpn.ga-prd-click` innerHTML
  - 가격: `.num-disPrice span` innerHTML
  - 품절 상품(`.sold_txt`) 자동 제외
  - 총 상품 수(`.txt_mb .num`) 표시 추가
- `format_products()`: 신규 함수 — `[카테고리][등급]` 패턴 파싱 후 등급/가격 기준 정렬
- `send_telegram()`: 상품 없을 때 기본 메시지 전송 처리 추가
- `.env`: `TARGET_URL`을 `/search` 경로에서 `/products` 경로로 변경 (기존 Selenium 스크립트와 동일)

### 테스트 결과
- 로그인 성공, 총 149개 상품 중 40개(첫 페이지, 품절 제외) 수집 확인
