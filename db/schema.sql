-- ============================================================
-- SLBS 캐릭터 마켓 레이더 - Supabase 스키마
-- Supabase SQL Editor에 전체 붙여넣기 후 실행
-- ============================================================

-- 1) 수집 실행 기록 (크롤러 1회 실행 = 1 run)
create table if not exists crawl_runs (
  id uuid primary key default gen_random_uuid(),
  run_at timestamptz not null default now(),
  keywords text[] not null,
  item_count int not null default 0
);

-- 2) 수집 상품 데이터
create table if not exists crawl_items (
  id bigint generated always as identity primary key,
  run_id uuid not null references crawl_runs(id) on delete cascade,
  crawled_at date not null default current_date,
  keyword text not null,
  product_name text not null,
  rating numeric,
  reviews int,
  purchases int,
  wishes int,
  reg_date text,                 -- 'YYYY.MM' 형식, 없으면 null
  months_on_sale int,            -- 판매개월수 (최소 1)
  point numeric,                 -- 리뷰 / 판매개월수
  character_name text not null default '기타'
);

create index if not exists idx_items_run on crawl_items (run_id);
create index if not exists idx_items_keyword on crawl_items (keyword);
create index if not exists idx_items_character on crawl_items (character_name);

-- 3) 캐릭터 사전 (기존 character_list.xlsx 대체)
create table if not exists character_dict (
  id bigint generated always as identity primary key,
  token text unique not null,          -- 상품명에 포함된 단어
  character_name text not null         -- 매칭될 캐릭터명
);

-- 4) 수집 키워드 목록 (크롤러가 이 테이블을 읽어서 순회)
create table if not exists crawl_keywords (
  id bigint generated always as identity primary key,
  keyword text unique not null,
  is_active boolean not null default true,
  sort_order int not null default 0
);

-- ============================================================
-- RLS: 대시보드(anon)는 읽기 전용. 쓰기는 크롤러(service_role)만.
-- ============================================================
alter table crawl_runs enable row level security;
alter table crawl_items enable row level security;
alter table character_dict enable row level security;
alter table crawl_keywords enable row level security;

drop policy if exists "anon read runs" on crawl_runs;
create policy "anon read runs" on crawl_runs for select using (true);

drop policy if exists "anon read items" on crawl_items;
create policy "anon read items" on crawl_items for select using (true);

drop policy if exists "anon read dict" on character_dict;
create policy "anon read dict" on character_dict for select using (true);

drop policy if exists "anon read keywords" on crawl_keywords;
create policy "anon read keywords" on crawl_keywords for select using (true);

-- ============================================================
-- 기본 수집 키워드 (필요시 Supabase 테이블 편집기에서 추가/수정)
-- ============================================================
insert into crawl_keywords (keyword, sort_order) values
  ('캐릭터 케이스', 1)
on conflict (keyword) do nothing;
