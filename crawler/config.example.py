# -*- coding: utf-8 -*-
# 이 파일을 복사해서 config.py 로 저장한 뒤 값을 채워 주세요.
# (config.py 는 git에 올라가지 않습니다)

# Supabase 프로젝트 설정 > API 에서 확인
SUPABASE_URL = "https://xxxxxxxx.supabase.co"

# service_role 키 (비밀키 - 절대 대시보드나 git에 넣지 마세요)
SUPABASE_SERVICE_KEY = "여기에_service_role_키"

# 키워드당 목표 수집 개수
ITEMS_PER_KEYWORD = 500

# DB(crawl_keywords)에 활성 키워드가 하나도 없을 때 사용할 기본값
FALLBACK_KEYWORDS = ["캐릭터 케이스"]
