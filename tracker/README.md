# 생두 트래커

국내 생두 업체들의 상품 페이지를 주기적으로 수집해서 **신규 입고 / 판매 시작 / 품절·재입고 / 가격 변동**을 알려주고, 한 화면에서 모아 보여줍니다.

## 구조
- `sources.json` — 수집할 업체 목록 (여기에 업체를 추가)
- `scrape.py` — 수집 + 이전 상태와 비교 + 알림
- `web/index.html` — 대시보드 (폰/PC 브라우저)
- `data/` — 수집 결과 (자동 갱신)
- `.github/workflows/scrape.yml` — 3시간마다 자동 실행

## 업체 추가하는 법
1. `sources.json`의 `template` 항목을 복사해 `id`, `name`, `url`을 채우고 `enabled: true`.
2. 업체가 카페24 쇼핑몰이면 `preset: "cafe24"`만으로 되는 경우가 많습니다. 안 되면 브라우저 F12로 상품 목록의 CSS 선택자를 확인해 `selectors`에 적습니다.
3. `python tracker/scrape.py` 로 확인. "상품을 하나도 찾지 못함"이 나오면 선택자 문제입니다.
4. 첫 수집은 "기준선"이라 알림이 가지 않고, 이후 변동분부터 알림이 갑니다.

## 알림 설정 (GitHub 저장소 Settings → Secrets → Actions)
- 텔레그램: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- 디스코드: `DISCORD_WEBHOOK_URL`

## 보기
- 로컬: 저장소 루트에서 `python3 -m http.server` → `/tracker/web/`
- 폰: GitHub Pages를 켜면 `https://<계정>.github.io/dayycoffee/tracker/web/` 로 접속 (홈 화면에 추가 가능)

## 주의
- 업체 사이트 약관/robots.txt를 확인하고, 수집 주기는 너무 짧게 하지 마세요.
- 네이버 스마트스토어 등 자바스크립트로 그려지는 사이트는 이 방식으로 안 읽힙니다 (별도 어댑터 필요).
