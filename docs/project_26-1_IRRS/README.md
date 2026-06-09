# HUFS 2026-1 Information Retrieval and Recommender System

## 도서 데이터 임베딩 및 FAISS index 구축

1. 기존 도서 데이터 4322 권에 대하여 로컬 GPU에서 임베딩 진행후 FAISS index 구축(books.faiss).
  - 사용 모델: paraphrase-multilingual-MiniLM-L12-v2 (GPU에 직접 로드)

  - 입력 텍스트에는 다음 정보가 포함된다: title(기존), author(기존), category(기존), 맥락(llm 생성)

  - llm 생성 맥락 텍스트는  Qwen2.5-14B를 이용 (GPU에 직접 로드) 프롬프트는 다음과 같다.
  
  """ write down the short German explanation of the following book. the explanation sentence should be under 20 words. The book's information is: 
    - title: {title}, 
    - author: {author}, 
    - category: {category} 
  
  Add the translated Korean text of your German text. The translated text should be attached next to the original German text."""

2. 신규 입력 도서 데이터 임베딩은 api 호출을 통해 진행.
  - 사용 모델: paraphrase-multilingual-MiniLM-L12-v2 (HF api calling 이용)

  - 입력 텍스트에는 다음 정보가 포함된다: title(기존), author(기존), category(기존), 맥락(llm 생성)

  - llm 생성 맥락 텍스트는 Gemini를 이용 (api calling) 프롬프트는 Qwen에서 썼던 것과 동일하다.

3. 쿼리 검색시 
  - 먼저 맨 위에 기존 '키워드 검색' 결과 반환
  - 이후 '의미 기반 검색'을 위하여 paraphrase-multilingual-MiniLM-L12-v2의 api를 호출하여 쿼리에 대해 임베딩을 계산 후 벡터 유사도 기반으로 후보 도서를 반환 
  - 다음으로 도서별 고유 번호를 기반으로 '키워드 검색 결과'와 '의미 기반 검색결과'를 비교하여 중복 도서 제거 
  - 최종적으로 키워드 매칭 결과 아래에 의미 기반 검색 결과를 추가하여 사용자에게 반환

## 파일 구조

```
Austrian-Library-HUFS/
├── backend/
│   ├── library/
│   │   ├── models.py                       # Book 모델: search_text 필드 추가 예정
│   │   ├── search_service.py               # [의미 기반 검색] FAISS 인덱스 관리 + HF API 임베딩 호출
│   │   ├── signals.py                      # [신규 도서용] API 이용하여 search_text 생성 -> 임베딩 -> 인덱스 추가
│   │   └── views.py                        # smart_search 하이브리드 검색 엔드포인트
│   └── media/search_index/
│       └── books.faiss                     # [기존 도서용] FAISS 인덱스 파일 (로컬 빌드 후 git 커밋)
└── docs/project_26-1_IRRS/
    ├── README.md
    ├── generate_search_text.py             # [기존 도서용] Qwen2.5-32B로 기존 도서 search_text 일괄 생성 → DB 저장
    ├── build_faiss_local.py                # [기존 도서용] 로컬 GPU에서 모델 직접 로드 → FAISS 인덱스 빌드
    ├── embedding_log.csv                   # [보고서 전용 (기존 도서)]: 도서별 입력 텍스트 샘플 (title, author, search_text)
    └── system_comparison/                  # 검색 시스템 평가
```
