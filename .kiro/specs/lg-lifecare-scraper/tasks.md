# 구현 계획: LG U+ Life Care 스크래퍼 테스트

## 개요

`main.py`의 핵심 기능(로그인·스크래핑·스크린샷·텔레그램 전송)은 이미 구현되어 있습니다.
이 태스크 목록은 `design.md`의 Testing Strategy에 따라 단위 테스트와 속성 기반 테스트를 작성하는 작업만 포함합니다.

## 태스크

- [x] 1. pyproject.toml에 테스트 의존성 추가
  - `[dependency-groups]` 섹션에 `dev` 그룹 추가
  - `pytest`, `hypothesis` 의존성 추가
  - _Requirements: 전체 테스트 인프라_

- [x] 2. tests/test_main.py 파일 생성 및 단위 테스트 작성
  - [x] 2.1 테스트 파일 기본 구조 및 픽스처 설정
    - `tests/test_main.py` 파일 생성
    - `main.py`에서 `format_products` 임포트
    - `TARGET_URL` 환경 변수 모킹 설정 (`monkeypatch` 또는 `unittest.mock.patch`)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 2.2 test_format_products_empty 단위 테스트 작성
    - 상품 0개(`[]`)와 `total="0"` 입력 시 반환 문자열에 헤더(`총 0개 중 0개 수집 (품절 제외)`)가 포함되는지 검증
    - 상품 목록 본문이 비어 있는지 검증
    - _Requirements: 5.4, 4.4_

  - [x] 2.3 test_format_products_no_pattern 단위 테스트 작성
    - `[등급][종류]모델명 / 가격` 패턴에 매칭되지 않는 상품명 목록 입력
    - 반환 문자열의 상품 순서가 입력 순서와 동일한지 검증
    - _Requirements: 4.3_

- [x] 3. 속성 기반 테스트 작성 (Hypothesis)
  - [x] 3.1 Property 2: test_more_btn_loop_termination
    - **Property 2: 더보기 루프 종료 조건**
    - **Validates: Requirements 2.5**
    - `button.btn_more_down`이 없거나 비표시 상태를 나타내는 플래그(`bool`)를 임의 생성
    - 종료 조건이 참일 때 루프 카운터가 증가하지 않음을 검증하는 순수 Python 로직으로 작성
    - `@settings(max_examples=100)` 적용

  - [x] 3.2 Property 3: test_format_header_format
    - **Property 3: 포맷팅 헤더 형식**
    - **Validates: Requirements 4.4, 4.5**
    - 임의의 상품 목록과 `total` 문자열에 대해 `format_products` 호출
    - 반환 문자열 첫 번째 줄이 `총 {total}개 중 {collected}개 수집 (품절 제외)` 형식인지 검증
    - 두 번째 줄이 `TARGET_URL`인지 검증
    - `@settings(max_examples=100)` 적용

  - [x] 3.3 Property 4: test_format_products_sorted
    - **Property 4: 정렬 불변성**
    - **Validates: Requirements 4.2**
    - `st.from_regex(r'\[[A-Z]+\]\[[가-힣]+\]\S+', fullmatch=True)`로 상품명 생성
    - `st.from_regex(r'\d{1,3}(,\d{3})*', fullmatch=True)`로 가격 생성
    - `format_products` 출력에서 상품 줄만 추출하여 종류(1차) 오름차순, 가격(2차) 오름차순 정렬 불변성 검증
    - `@settings(max_examples=100)` 적용

  - [x] 3.4 Property 5: test_format_products_fallback_order
    - **Property 5: 파싱 실패 시 원본 순서 보존**
    - **Validates: Requirements 4.3**
    - 패턴에 매칭되지 않는 임의 상품명 목록 생성 (`st.text()`로 패턴 불일치 보장)
    - `format_products` 출력의 상품 순서가 입력 순서와 동일한지 검증
    - `@settings(max_examples=100)` 적용

  - [x] 3.5 Property 6: test_message_chunk_roundtrip
    - **Property 6: 메시지 청크 분할 라운드트립**
    - **Validates: Requirements 5.2**
    - `st.text(min_size=0, max_size=20000)`으로 임의 메시지 생성
    - 4096자 단위 청크 분할 후 각 청크 길이 ≤ 4096 검증
    - 청크 이어 붙이기 결과가 원본과 동일한지 검증
    - `@settings(max_examples=100)` 적용

  - [x] 3.6 Property 7: test_screenshot_filename_pattern
    - **Property 7: 스크린샷 파일명 패턴**
    - **Validates: Requirements 3.2**
    - `st.datetimes()`로 임의 `datetime` 값 생성
    - `capture_{YYYYMMDD_HHMMSS}.png` 형식 정규식(`r'^capture_\d{8}_\d{6}\.png$'`) 검증
    - `@settings(max_examples=100)` 적용

- [x] 4. 체크포인트 — 전체 테스트 통과 확인
  - 모든 테스트가 통과하는지 확인하고, 문제가 있으면 사용자에게 질문하세요.

## 참고

- `*` 표시 태스크는 선택 사항으로 MVP 구현 시 건너뛸 수 있습니다
- 각 태스크는 추적성을 위해 특정 요구사항을 참조합니다
- 속성 테스트는 보편적 정확성 속성을 검증합니다
- Playwright 의존 기능(로그인·스크래핑·스크린샷·텔레그램 전송)은 외부 서비스 의존성으로 인해 자동화 테스트 범위에서 제외합니다
