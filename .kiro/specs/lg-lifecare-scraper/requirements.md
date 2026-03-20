# Requirements Document

## Introduction

LG U+ Life Care(lguplus.lglifecare.com) 사이트에 사번으로 로그인하여 지정된 카테고리(LG등급)의 상품명과 가격을 수집하고, 결과를 텔레그램 봇으로 전송하는 스크래퍼입니다.

더보기 버튼 클릭 방식으로 단일 페이지 DOM에 전체 상품을 로드한 뒤 한 번에 수집하며, 로그인·스크린샷·텔레그램 전송 기능을 포함합니다.

## Glossary

- **Scraper**: LG U+ Life Care 사이트에서 상품 정보를 수집하는 본 시스템 전체
- **Authenticator**: 사번/비밀번호로 Life Care 사이트에 로그인하는 컴포넌트
- **ProductCollector**: 상품 목록 페이지에서 상품명·가격을 추출하는 컴포넌트
- **Formatter**: 수집된 상품 목록을 정렬·포맷팅하는 컴포넌트
- **TelegramSender**: 포맷된 메시지와 스크린샷을 텔레그램 봇으로 전송하는 컴포넌트
- **ScreenshotCapture**: 현재 페이지의 전체 스크린샷을 저장하는 컴포넌트
- **LG등급 상품**: `displayCategoryNo=364503` 카테고리에 속한 상품
- **품절 상품**: `.sold_txt` 요소를 포함하는 `.nhm-item` 항목
- **더보기 버튼**: `.btn_more_down` 클래스를 가진 버튼으로, 추가 상품이 존재함을 나타냄. 클릭 시 현재 페이지 DOM에 상품이 추가 로드됨
- **TARGET_URL**: `.env`에 설정된 상품 카테고리 페이지 기본 URL

---

## Requirements

### Requirement 1: 사번 로그인

**User Story:** As a LG U+ 임직원, I want 사번과 비밀번호로 Life Care 사이트에 자동 로그인하고 싶다, so that 수동 개입 없이 상품 정보를 수집할 수 있다.

#### Acceptance Criteria

1. WHEN 스크래퍼가 실행되면, THE Authenticator SHALL `https://lguplus.lglifecare.com/auth/login` 페이지로 이동한다
2. THE Authenticator SHALL 환경 변수 `LG_ID`를 `input#id[name="id"]` 필드에 입력한다
3. THE Authenticator SHALL 환경 변수 `LG_PW`를 `input[name="password"]` 필드에 입력한다
4. WHEN 자격증명 입력이 완료되면, THE Authenticator SHALL `button.again-btn_bg_gradient`를 클릭하여 로그인을 시도한다
5. WHEN 로그인 후 `.todayClosePop` 팝업이 표시되면, THE Authenticator SHALL 해당 팝업을 닫는다
6. IF `.todayClosePop` 팝업이 5초 이내에 나타나지 않으면, THE Authenticator SHALL 팝업 없음으로 간주하고 계속 진행한다

---

### Requirement 2: 더보기 버튼 클릭으로 전체 상품 수집

**User Story:** As a LG U+ 임직원, I want LG등급 카테고리의 모든 상품을 빠짐없이 수집하고 싶다, so that 전체 상품 현황을 파악할 수 있다.

#### Acceptance Criteria

1. WHEN 상품 수집이 시작되면, THE ProductCollector SHALL `TARGET_URL`로 이동하여 첫 번째 상품 목록을 로드한다
2. THE ProductCollector SHALL `.txt_mb .num` 요소에서 총 상품 수를 읽어 반환한다
3. WHILE `button.btn_more_down`이 존재하고 표시 상태이면, THE ProductCollector SHALL 해당 버튼을 클릭하여 추가 상품을 현재 페이지 DOM에 로드한다
4. WHEN 더보기 버튼 클릭 후, THE ProductCollector SHALL `.nhm-item` 개수가 증가할 때까지 최대 10초 대기한다
5. WHEN `button.btn_more_down`이 존재하지 않거나 비표시 상태이면, THE ProductCollector SHALL 더보기 클릭을 종료하고 수집 단계로 진행한다
6. WHEN 전체 상품이 DOM에 로드되면, THE ProductCollector SHALL JavaScript evaluate로 모든 `.nhm-item` 요소를 한 번에 수집한다
7. THE ProductCollector SHALL `.nhm-item` 중 `.sold_txt`를 포함하는 항목을 제외한다
8. THE ProductCollector SHALL 각 상품에서 `.tit_cpn.ga-prd-click` 요소의 텍스트를 상품명으로, `.num-disPrice span` 요소의 텍스트를 가격으로 추출한다

---

### Requirement 3: 전체 페이지 스크린샷 저장

**User Story:** As a LG U+ 임직원, I want 수집 시점의 페이지 화면을 저장하고 싶다, so that 나중에 수집 결과를 시각적으로 확인할 수 있다.

#### Acceptance Criteria

1. WHEN 상품 수집이 완료되면, THE ScreenshotCapture SHALL 현재 뷰포트 기준으로 스크린샷을 캡처한다 (전체 페이지 스크롤 캡처 아님)
2. THE ScreenshotCapture SHALL 스크린샷을 `screenshots/capture_{YYYYMMDD_HHMMSS}.png` 형식의 파일명으로 저장한다
3. THE ScreenshotCapture SHALL `screenshots/` 디렉토리가 없으면 자동으로 생성한다

---

### Requirement 4: 상품 목록 포맷팅

**User Story:** As a LG U+ 임직원, I want 수집된 상품 목록이 읽기 쉽게 정렬·포맷팅되기를 원한다, so that 텔레그램 메시지에서 빠르게 원하는 상품을 찾을 수 있다.

#### Acceptance Criteria

1. THE Formatter SHALL 수집된 상품 목록을 `[등급][종류]모델명 / 가격` 패턴으로 파싱한다
2. WHEN 패턴 파싱이 성공하면, THE Formatter SHALL 종류(1차)와 가격 오름차순(2차) 기준으로 정렬한다
3. IF 패턴 파싱이 실패하면, THE Formatter SHALL 원본 수집 순서 그대로 출력한다
4. THE Formatter SHALL 메시지 첫 줄에 `총 {total}개 중 {collected}개 수집 (품절 제외)` 형식의 요약 헤더를 포함한다
5. THE Formatter SHALL 헤더 다음 줄에 `TARGET_URL`을 포함한다

---

### Requirement 5: 텔레그램 전송

**User Story:** As a LG U+ 임직원, I want 수집 결과를 텔레그램으로 받고 싶다, so that 별도 접속 없이 모바일에서 바로 확인할 수 있다.

#### Acceptance Criteria

1. WHEN 포맷팅된 메시지가 준비되면, THE TelegramSender SHALL 환경 변수 `TELEGRAM_BOT_TOKEN`과 `TELEGRAM_CHAT_ID`를 사용하여 메시지를 전송한다
2. THE TelegramSender SHALL `HTTPXRequest(verify=False)` 설정으로 봇을 초기화하여 회사 네트워크의 self-signed SSL 인증서를 우회한다
3. WHEN 메시지 길이가 4096자를 초과하면, THE TelegramSender SHALL 4096자 단위로 분할하여 순서대로 전송한다
4. WHEN 메시지 전송이 완료되면, THE TelegramSender SHALL 스크린샷 이미지를 동일 채팅방에 전송한다
5. WHEN 수집된 상품이 0개이면, THE TelegramSender SHALL `"오늘은 등록된 상품이 없습니다."` 메시지와 스크린샷을 전송한다

---

### Requirement 6: 에러 처리

**User Story:** As a LG U+ 임직원, I want 스크래퍼 실행 중 오류가 발생해도 원인을 파악할 수 있기를 원한다, so that 문제를 빠르게 진단하고 수정할 수 있다.

#### Acceptance Criteria

1. WHEN 실행 중 예외가 발생하면, THE Scraper SHALL `screenshots/error_{YYYYMMDD_HHMMSS}.png` 파일명으로 에러 시점의 스크린샷을 저장한다
2. WHEN 에러 스크린샷 저장이 완료되면, THE Scraper SHALL 원래 예외를 다시 발생시켜 호출자에게 전파한다
3. THE Scraper SHALL 브라우저 컨텍스트를 항상 종료한다 (정상 종료 및 에러 발생 시 모두)
