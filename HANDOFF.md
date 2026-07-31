# Claude Code 인계 문서 — 캐릭터 마켓 레이더 초기 셋업

이 폴더는 Claude.ai에서 생성한 완성 코드입니다. 아래 순서대로 셋업을 진행해 주세요.
사용자(Danny)는 비개발자이므로 각 단계에서 확인이 필요한 값은 직접 물어봐 주세요.

## 배경

- 기존 `naverShopCrawler.ipynb`(네이버쇼핑 캐릭터 상품 수집 → 엑셀 리포트)를
  다중 키워드 + Supabase + Vercel 대시보드 구조로 재구축한 것
- 기존 노트북의 버그 수정 완료: pagingIndex 고정, 0 나눗셈, 쉼표 파싱, 캐릭터 매칭 순서
- 사용자 환경: Windows PC, Vercel 계정 wacandacat(Hobby), 기존 프로젝트들과 동일 패턴

## 1. GitHub 레포

- 새 private 레포 생성: `WacandaCat/slbs-market-crawler`
- 이 폴더 전체를 커밋 (`crawler/config.py` 는 .gitignore로 제외됨 — 확인할 것)
- 커밋 author는 반드시 `Danny <daniel29park@gmail.com>` (Vercel 자동배포 이슈 방지, 기존 규칙)

## 2. Supabase

- 기존 Supabase 계정에 새 프로젝트 생성 또는 기존 프로젝트 사용 (사용자에게 확인)
- SQL Editor에서 순서대로 실행:
  1. `db/schema.sql` (테이블 4개 + RLS 읽기전용 정책 + 기본 키워드 1개)
  2. `db/seed_character_dict.sql` (캐릭터 사전 48개 토큰)
- `crawl_keywords` 테이블에 사용자가 원하는 키워드 추가 (예: 기종별 케이스 키워드)

## 3. 크롤러 설정 (사용자 PC)

- `crawler/config.example.py` → `crawler/config.py` 복사
- SUPABASE_URL, SUPABASE_SERVICE_KEY(service_role) 입력
- Python 설치 여부 확인, 없으면 설치 안내
- `run_crawler.bat` 더블클릭으로 테스트 실행 → Supabase에 데이터 들어가는지 확인
- 주의: 네이버 CSS 선택자(해시 클래스명)는 시점에 따라 깨질 수 있음.
  수집 0건이면 실제 페이지 구조를 확인해서 `crawler.py`의 선택자를 업데이트할 것

## 4. Vercel

- 정적 사이트 (빌드 불필요, 루트 index.html)
- 레포 연결 후 `config.js` 에 SUPABASE_URL과 anon 키 입력 후 커밋
- 배포는 항상 `git push` 방식 (Vercel CLI 토큰은 읽기전용 — 기존 규칙)
- 배포 확인 후 사용자에게 서브도메인 연결 의사 확인 (예: `radar.slbs.shop`)

## 5. 완료 확인 체크리스트

- [ ] 크롤러 실행 → crawl_runs / crawl_items에 데이터 적재
- [ ] 대시보드에서 수집 회차 선택, 키워드 필터, 캐릭터 순위, 미분류 목록 표시
- [ ] 숫자가 쉼표 포함 전체 표기로 나오는지 (사용자 표준)
- [ ] 시크릿 창에서 최종 확인 (사용자 습관)

## 이후 확장 아이디어 (지금은 구현하지 말 것)

- 회차 간 비교 (지난 수집 대비 순위 변동)
- 캐릭터 사전을 대시보드에서 직접 편집 (인증 필요)
- 수집 자동화 (작업 스케줄러) — 네이버 차단 리스크 검토 후

---

## 셋업 진행 기록 (Claude Code)

- **1. GitHub 레포** — 완료. Danny가 `WacandaCat/slbs-market-crawler` 를 생성,
  Claude Code가 전체 파일을 커밋·푸시.
- **index.html 관련 참고** — Dropbox에서 원본 HTML 소스를 그대로 내려받을 수 없어
  (텍스트 추출 시 태그가 제거됨) 대시보드를 동일 사양으로 새로 작성함.
  기능은 인계 문서 기준 그대로: 수집 회차 선택, 키워드 필터, 캐릭터 판매지수 순위,
  미분류 상위 상품, 정렬 가능한 상품 목록, 쉼표 포함 전체 숫자 표기.
- **2. Supabase** — 완료. 무료 플랜이 조직당 프로젝트 2개 한도라 새 프로젝트를 만들 수 없어,
  Danny 확인 후 기존 **`slbs-d2c-dashboard`** 프로젝트에 크롤러 테이블 4개만 추가함.
  - 캐릭터 사전 48개 토큰, 기본 키워드 `캐릭터 케이스` 1개 적재 확인
  - anon 키로 crawl_* / character_dict 읽기 가능, 쓰기는 거부(401) 확인
  - 같은 프로젝트의 기존 매출 테이블(sales_raw 등)은 anon 정책이 없어
    공개 대시보드 키로도 조회되지 않는 것을 확인함
  - `config.js` 에 해당 프로젝트 URL과 anon 키 입력 후 커밋
- **3. 크롤러 설정** — Danny PC에서 진행 필요.
  `crawler/config.py` 에 위 프로젝트의 **service_role** 키 입력 (Supabase 대시보드에서 복사).
- **4. Vercel** — Danny가 브라우저에서 레포를 Import 해야 함.
  이후에는 `git push` 만으로 자동 배포됨.

### 배포 전에 처리한 보안 문제

이 대시보드는 브라우저에서 anon 키로 Supabase를 직접 읽는 구조라,
같은 프로젝트에서 anon이 무엇을 할 수 있는지 점검했다.

`slbs-d2c-dashboard` 프로젝트의 `SECURITY DEFINER` 함수 2개에
PostgreSQL 기본 `PUBLIC` EXECUTE 권한이 남아 있어 anon 키로 호출이 가능했다.
SECURITY DEFINER 함수는 RLS를 우회하므로, 테이블이 잠겨 있어도 데이터가 나온다.

- `realtime_products(date, date, text[])` — 상품별 실판매 수량·매출액이 그대로 반환됨
- `trigger_ingest(text, integer, text)` — 적재 파이프라인을 실행시키는 함수

두 함수 모두 D2C 대시보드의 서버 코드(`api/daily.js`, `api/sync.js`)에서
**service_role 키로만** 호출되고 클라이언트는 Supabase를 직접 호출하지 않으므로,
공개 권한을 회수해도 기존 대시보드는 영향이 없음을 확인한 뒤 회수했다.
같은 프로젝트의 나머지 SECURITY DEFINER 함수 5개는 이미 같은 상태였다.

```sql
revoke execute on function public.realtime_products(date, date, text[]) from public, anon, authenticated;
revoke execute on function public.trigger_ingest(text, integer, text) from public, anon, authenticated;
grant  execute on function public.realtime_products(date, date, text[]) to service_role;
grant  execute on function public.trigger_ingest(text, integer, text) to service_role;
```

되돌리려면 위 `revoke` 대상에 다시 `grant execute ... to anon, authenticated;` 하면 된다.

앞으로 이 프로젝트에 SECURITY DEFINER 함수를 새로 만들 때는
`revoke execute on function ... from public;` 를 같이 실행할 것.
