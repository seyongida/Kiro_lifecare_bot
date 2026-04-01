# Changelog

## [1.3.0] - 2026-03-24

### 추가
- `check_projector_ust(model_name, browser_page)` 함수 신규 추가 — LG 전자 한국 사이트에서 프로젝터 초단초점 여부 판별
  - `lge.co.kr/projectors/{슬러그}` 페이지 로드 후 `초단초점` 텍스트 유무로 판정
  - User-Agent 설정 필수 (미설정 시 JS 렌더링 안 됨)
  - 타임아웃·404 등 오류 시 `False` 반환 → `(UST)` 미추가
- `format_products()`: `ust_page` 파라미터 추가 — 프로젝터 항목에 한해 초단초점 판별 후 모델명 뒤에 ` (UST)` 자동 추가
  - 동일 모델 중복 요청 방지를 위해 슬러그 기준 캐시 처리
  - `ust_page=None`이면 UST 판별 스킵 (하위 호환)
- `main()`: UST 판별 전용 페이지(`ust_page`) 별도 생성 후 `format_products()`에 전달
  - `set_extra_http_headers`로 User-Agent 설정

### 삭제
- `_tmp_ust_check.py` 임시 검증 스크립트 역할 종료 (main.py에 통합)

## [1.2.0] - 2026-03-24

### 조사
- 프로젝터 초단초점(UST) 자동 태깅 기능 구현 가능 여부 검증
  - `raw_products_20260323_082838.txt` 기준 프로젝터 11개(고유 모델 8개) 확인
  - LG 전자 한국 사이트(`lge.co.kr/projectors/{모델슬러그}`) 페이지에서 `초단초점` 텍스트 유무로 판별하는 방식 채택
  - Playwright headless 실행 시 User-Agent 미설정이면 JS 렌더링이 안 되어 `초단초점` 텍스트 미노출 확인 → User-Agent 설정 필수
  - `networkidle` 대기 시 일부 모델(BF50RG, BU60RG) 타임아웃 발생 — 오류 시 비초단초점으로 안전 처리
  - 초단초점 모델 3개 확인: `PU615U`(시네빔 쇼츠), `HU810PW`, `HU915QE`(시네빔 Laser 4K)
  - 초단초점 모델 라인에 `(UST)` 태그 추가 변환 로직 검증 완료

### 추가
- `_tmp_ust_check.py` 신규 생성 — 프로젝터 초단초점 판별 및 `(UST)` 태그 추가 검증용 임시 스크립트

## [1.1.4] - 2026-03-24

### 변경
- `.github/workflows/scrape.yml`: keep-alive step의 `if: github.event_name == 'schedule'` 조건 제거
  - 수동 실행(`workflow_dispatch`)에서도 keep-alive step 실행 가능하도록 변경
  - 실제 push는 매월 1일 조건(`if [ "$DAY" = "01" ]`)으로 여전히 제한됨

## [1.1.3] - 2026-03-23

### 버그 수정
- `.github/workflows/scrape.yml`: keep-alive step `git push` 403 권한 에러 수정
  - 원인: `permissions` 미설정으로 기본 `read` 권한만 부여 → `github-actions[bot]`이 push 불가
  - 수정: `permissions: contents: write` 추가

## [1.1.2] - 2026-03-23

### 검증
- `check_projector_ust()` 수정 로직을 실제 데이터(raw_products_20260323_082838.txt)로 검증
  - 프로젝터 11개(고유 모델 8개) 판별 결과
  - UST(초단초점): `PU615U.BKR`, `HU915QE.BKR`
  - 투사형: `BF60RG`, `BU50RG`, `KPU510RG`, `BF50RG`, `BU60RG`, `HU810PW` — 모두 정확 판별
  - 이전 버그였던 HU810PW 오판 없이 투사형으로 정확히 분류됨

## [1.1.1] - 2026-03-23

### 버그 수정
- `check_projector_ust()`: HU810PW 등 투사형 모델이 UST로 오판되는 버그 수정
  - 원인: 페이지 전체에서 `"초단초점"` 텍스트만 검색 → 연관 상품 섹션에 초단초점 모델이 노출되면 오판
  - 수정: `"투사형"` 텍스트가 있으면 UST 판별 없이 비초단초점으로 즉시 확정
  - HU810PW 페이지에는 `투사형`이 명시되어 있어 정확히 판별됨

## [1.1.0] - 2026-03-23

### 변경
- `.gitignore`: 임시 스크립트 및 크롤링 결과 파일 ignore 규칙 추가
  - `_tmp_*.py` — 개발/디버깅용 임시 스크립트
  - `raw_products_*.txt` — 크롤링 raw 결과 파일

## [1.0.9] - 2026-03-23

### 버그 수정
- `format_products()`: 공백 포함 상품명 패턴 미매칭 버그 수정
  - 기존: `\S+` → 공백 포함 상품명(`Life Style Display 27 (FHD) ...` 등) 매칭 실패로 117개 중 47개 누락
  - 변경: `.+?` + `$` 앵커로 교체 → 117개 전부 매칭, 미매칭 0개

## [1.0.8] - 2026-03-23

### 조사
- `format_products()` sorting 로직 문제 2개 확인 (실제 크롤링 데이터 117개 기준)
  - 문제 1 (버그): 패턴 `\S+`가 공백 포함 상품명 미매칭 → 117개 중 47개(40%)가 정렬 대상에서 누락됨
    - 원인: `[C등급][스텐드]Life Style Display 27 (FHD) 27ART10DSPL.AKR` 등 상품명에 공백이 있으면 `\S+` 매칭 실패
    - 수정 방향: `\S+` → `.+?` 로 교체
  - 문제 2 (설계): 정렬 키가 `(종류, 가격)` 2단계라 같은 종류 내 등급이 섞임
    - 예: `등급모니터` 그룹 내 D등급/C등급/D등급 순으로 혼재
    - 수정 방향: `(종류, 등급, 가격)` 3단계 정렬로 변경 여부 검토 필요

## [1.0.7] - 2026-03-23

### 조사
- `format_products()` sorting 로직 문제 분석
  - 정렬 키 `x[1]`(종류)이 한글 사전순 정렬이라 의도한 카테고리 순서와 다를 수 있음
  - 가격 필드 `x[3]`이 HTML `innerHTML` 그대로라 `<span>` 태그 잔존 시 `int()` 변환 실패 가능성 확인
  - 실제 크롤링 데이터 확인을 위해 raw 결과 txt 저장 스크립트 작성 시도 — Kiro IDE 환경에서 Playwright Chromium `EPERM` 권한 오류로 미완
  - 실제 데이터 확인 후 sorting 수정 예정

## [1.0.6] - 2026-03-20

### 추가
- `tests/test_white_monitor.py` 신규 생성 — `is_white_monitor()` 단위 테스트 5개
  - 화이트 모델 판별 (prod_name 블록 매칭)
  - 검색결과 없으면 비화이트
  - 연관 상품만 있으면 비화이트 (27MS500 케이스)
  - 한국 유통 suffix(.AKRG) 제거 후 base 모델명으로 검색하는지 확인
  - 네트워크 오류 시 비화이트 fallback
- `pyproject.toml`: `[dependency-groups] dev` 섹션 추가 — `pytest>=8.0`

## [1.0.5] - 2026-03-20

### 검증
- 실제 Life Care 데이터(128개 상품)로 `is_white_monitor()` 다나와 검색 판별 검증
  - (W) 판정 결과: `34GX90SAW.BKR(W)`, `32GS95UVW.BKR(W)` 2개 — 실제 화이트 모델 정확 확인
  - `27MS500` 비화이트 정확 판별 확인
  - 전체 등급모니터 18개 모델 판별 오류 없음

## [1.0.4] - 2026-03-20

### 변경
- `is_white_monitor()`: suffix 기반 판별 → 다나와 검색 기반 판별로 전면 교체
  - Life Care 사이트가 모델명을 `27SR75U.AKRG` 형태로만 노출 (색상 suffix 미포함)로 인해 suffix 방식으로는 화이트 판별 불가
  - 다나와 LG 화이트 모니터 필터(`attribute=346318-916486-OR`, `maker=2137`) 검색 후 `prod_name` 블록에 base 모델명이 포함되면 화이트로 판정
  - 연관 상품이 함께 노출되는 경우를 걸러내기 위해 단순 텍스트 포함 여부가 아닌 `prod_name` 블록 내 정확 매칭 방식 사용
  - 검증: `27SR75U`, `27SR50F`, `27US500` → 화이트 / `27MS500`, `27BR400` → 비화이트 정확 판별 확인
- `httpx` 의존성 → `requests>=2.32`로 교체 (`requirements.txt`, `pyproject.toml`)
- `urllib3` InsecureRequestWarning 전역 suppress 추가

## [1.0.3] - 2026-03-20

### 조사
- 실제 수집 모델명 형태 확인: `27SR75U.AKRG`, `27SR50F.AKRG`, `27US500.AKRG`
  - 사이트는 `모델명.AKRG` 형태로만 노출 — 색상 suffix(`-W`, `-B`) 미포함
  - `.AKRG` 제거 후 base 모델명에 색상 suffix가 없으므로 현재 로직으로는 화이트 모델 감지 불가
  - 해결 방향: 화이트 모델 화이트리스트 하드코딩 또는 상품명 HTML에서 색상 정보 추출 검토 필요

## [1.0.2] - 2026-03-20

### 조사
- `is_white_monitor()` 동작 검증 — suffix 없는 모델 3종 실행 확인
  - `27SR75U`, `27SR50F`, `27US500` 모두 suffix 없음 → 비화이트로 판별됨
  - 현재 로직은 사이트가 `-W` / `-B` 등 색상 suffix를 포함한 전체 모델명을 노출해야 정확히 동작
  - 사이트가 suffix 없이 모델명만 노출하는 경우 화이트/블랙 구분 불가 → 실제 수집 데이터 확인 필요

## [1.0.1] - 2026-03-20

### 버그 수정
- `is_white_monitor()`: 화이트 모델 오판 버그 수정
  - 기존: suffix 없는 모델(27MS500, 27BR400 등)을 DuckDuckGo 웹검색으로 판별 → 검색 결과에 "white" 언급이 많으면 화이트로 오판
  - 변경: `-W` suffix인 경우만 화이트로 확정, suffix 없거나 `-B` 등 기타 suffix는 모두 비화이트로 처리
  - 웹검색 fallback 로직 완전 제거
  - `async` 함수 → 일반 동기 함수로 변경 (비동기 불필요)
  - `format_products()` 내 `await is_white_monitor()` → `is_white_monitor()` 호출로 수정

### 삭제
- `httpx` import 제거 — 웹검색 fallback 제거로 더 이상 불필요

## [1.0.0] - 2026-03-20

### 추가
- `is_white_monitor(model_name)` 함수 신규 추가 — 등급모니터 상품의 화이트 색상 여부 자동 판별
  - 한국 유통 suffix(`.AKRG` 등) 제거 후 모델명 기준으로 판별
  - `-W` suffix → 화이트 확정
  - `-B`, `-S`, `-G`, `-P`, `-C`, `-K` suffix → 화이트 아님
  - suffix 없거나 불명확 → DuckDuckGo 웹 검색으로 판별 (white 언급 수가 black의 2배 이상이면 화이트)
- `format_products()` → `async` 함수로 변경, `[등급모니터]` 상품에 한해 `is_white_monitor()` 호출 후 모델명 뒤에 `(W)` 자동 추가
- `httpx>=0.27` 의존성 추가 (`pyproject.toml`, `requirements.txt`)

### 검증
- 8개 모델 테스트 케이스 8/8 통과
  - `-W` suffix 확정, 한국 유통코드 포함 케이스, `-B`/`-P` 비화이트, 웹검색 판별(`27SR75U`, `27SR50F`, `27US500`, `27SR75U.AKRG`)

## [0.9.3] - 2026-03-20

### 버그 수정
- `format_products()`: 패턴 미매칭 상품 누락 버그 수정
  - 기존: `pattern.findall()`로 전체 텍스트 검색 → 패턴 매칭된 상품만 반환, 나머지 누락
  - 변경: 상품별 개별 매칭 → 매칭 상품은 정렬 후 앞에, 미매칭 상품은 뒤에 그대로 추가
  - 전체 수집 상품이 빠짐없이 텔레그램으로 전송되도록 수정
  - 포맷 완료 시 정렬/미매칭 개수 로그 출력 추가

## [0.9.2] - 2026-03-20

### 추가
- `.github/workflows/scrape.yml`: 저장소 비활성 방지 keep-alive step 추가
  - 매월 1일 schedule 실행 시 빈 커밋(`[skip ci]`) 자동 push
  - GitHub Actions 60일 비활성 시 schedule 자동 중단되는 문제 방지

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
