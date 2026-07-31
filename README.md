# 캐릭터 마켓 레이더 (SLBS)

네이버쇼핑 검색 결과에서 캐릭터 상품 판매 데이터를 수집하고,
캐릭터 IP별 판매지수(point = 리뷰 수 ÷ 판매개월수)를 대시보드로 보여주는 도구입니다.

## 구조

```
크롤러 (내 PC에서 실행)  →  Supabase (데이터 저장)  →  대시보드 (Vercel, 항상 켜져 있음)
```

## 평소 사용법

1. 새 데이터가 필요할 때 `crawler/run_crawler.bat` 을 더블클릭합니다.
2. 크롬 창이 자동으로 뜨고 수집이 진행됩니다 (키워드당 약 5~7분).
3. 완료되면 대시보드에서 바로 확인할 수 있습니다. 새로고침 후 상단에서 수집 회차를 선택하세요.

## 처음 한 번만 하는 설정

### 1) Supabase 테이블 만들기

Supabase → SQL Editor 에서 아래 순서로 실행합니다.

1. `db/schema.sql` — 테이블 4개 + 읽기전용 RLS 정책 + 기본 키워드 1개
2. `db/seed_character_dict.sql` — 캐릭터 사전 48개 토큰

### 2) 크롤러에 키 넣기 (내 PC)

1. `crawler/config.example.py` 를 복사해 같은 폴더에 `crawler/config.py` 로 저장합니다.
2. Supabase → Project Settings → API 에서 값을 복사해 넣습니다.
   - `SUPABASE_URL` — Project URL
   - `SUPABASE_SERVICE_KEY` — **service_role** 키 (비밀키)
3. Python이 없으면 https://www.python.org 에서 설치할 때
   "Add python.exe to PATH" 를 반드시 체크합니다.

### 3) 대시보드에 키 넣기 (Vercel)

`config.js` 를 열어 `SUPABASE_URL` 과 **anon(public)** 키를 넣고 커밋합니다.
anon 키는 공개용이라 깃에 올라가도 괜찮습니다.
Vercel은 이 레포를 연결해 두면 `git push` 할 때마다 자동 배포합니다.
빌드 설정은 필요 없습니다(정적 사이트, 루트 `index.html`).

## 수집 키워드 바꾸기

Supabase → Table Editor → `crawl_keywords` 테이블에서
키워드를 추가하거나 `is_active` 를 끄고 켜면 됩니다.
예: `갤럭시 Z플립7 케이스`, `아이폰16 케이스`, `폰 스트랩`

## 캐릭터 사전 관리

Supabase → Table Editor → `character_dict` 테이블에서
`token`(상품명에 포함된 단어)과 `character_name`(캐릭터명)을 추가합니다.
대시보드의 "미분류 상위 상품" 카드를 보면서 빠진 캐릭터를 보강하면 됩니다.
긴 단어가 우선 매칭되므로 '곰'과 '곰돌이푸'가 같이 있어도 안전합니다.

## 폴더 안내

- `crawler/` — 수집기 (PC에서 실행). `config.example.py` 를 `config.py` 로 복사해 키 입력
- `db/` — Supabase 테이블 생성 SQL(`schema.sql`)과 캐릭터 사전 초기 데이터(`seed_character_dict.sql`)
- `index.html`, `config.js` — 대시보드 (Vercel이 자동 배포)

## 주의

- `crawler/config.py` 의 service_role 키는 비밀키입니다. git에 올라가지 않도록 되어 있습니다(.gitignore).
- `config.js` 의 anon 키는 공개용 키라 커밋해도 됩니다.
- 네이버 페이지 구조가 바뀌면 수집이 실패할 수 있습니다. "수집된 상품이 없습니다" 메시지가 나오면 선택자 업데이트가 필요합니다.
