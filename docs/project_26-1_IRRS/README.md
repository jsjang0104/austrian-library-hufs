# HUFS 2026-1 Information Retrieval and Recommender System

## 도서 데이터 임베딩 및 FAISS index 구축

### 1. LLM 맥락 텍스트 생성 (search_text)

#### 기존 도서 (4322 권)
- **방식**: `generate_search_text.py` 스크립트로 오프라인 일괄 생성
- **LLM**: Qwen3.6-27B-FP8 (vLLM 서버, localhost:8000 OpenAI 호환 엔드포인트)
- **프롬프트**:
  ```
  write down the short German explanation of the following book. the explanation sentence should be under 20 words. The book's information is:
    - title: {title},
    - author: {author},
    - category: {category}

  Add the translated Korean text of your German text. The translated text should be attached next to the original German text.
  ```
- **실행 순서**: 
  1. `bash docs/project_26-1_IRRS/serve_qwen.sh` (vLLM 서버 시작)
  2. 별도 터미널에서 `python docs/project_26-1_IRRS/generate_search_text.py` (search_text 생성)
  3. 생성된 텍스트는 `backups/backup_YYYYMMDD_HHMMSS.json`에 백업됨
  4. 완료 후 `build_faiss_local.py`로 FAISS 인덱스 구축

#### 신규 도서
- **방식**: Django admin에서 `search_text` 필드에 직접 입력
- **자동 생성**: 없음 (admin에서 수동 입력만)
- **임베딩**: `signals.py`의 `post_save` 신호로 자동 임베딩 및 인덱싱 (HF API 호출)

### 2. 임베딩 및 FAISS 인덱싱

- **임베딩 모델**: intfloat/multilingual-e5-large (HF Inference API, 1024차원)
  - 기존: paraphrase-multilingual-MiniLM-L12-v2 → 새로운 모델로 교체
  - 평가 중: BAAI/bge-m3와 비교 검토 예정
  - CLI 옵션으로 모델 전환 가능 (`build_faiss_local.py --model e5|bge-m3`)

- **기존 도서 FAISS 인덱싱**:
  - `build_faiss_local.py`: 로컬 GPU에서 모델을 직접 로드하여 임베딩 + FAISS 인덱스 구축
  - 입력 텍스트: title + translated_title + author + translated_author + category + category(독일어) + search_text
  - 옵션:
    - `--model`: minilm(기존), e5(기본), bge-m3 중 선택
    - `--out`: 인덱스 파일명 (기본: books.faiss)

- **신규 도서 인덱싱**:
  - `signals.py`에서 Book 저장 시 자동으로 `search_service.add_book/remove_book` 호출
  - 재인덱싱 전용 (Gemini 관련 로직 없음)

### 3. 쿼리 검색 흐름
  
- 먼저 기존 '키워드 검색' 결과 반환
- 이후 '의미 기반 검색': intfloat/multilingual-e5-large로 쿼리 임베딩 계산 후 FAISS로 벡터 유사도 기반 후보 도서 반환
- 도서별 고유 번호로 '키워드 검색'과 '의미 기반 검색' 중복 제거
- 최종적으로 키워드 매칭 결과 아래에 의미 기반 검색 결과 추가하여 사용자에게 반환

## 파일 구조

```
Austrian-Library-HUFS/
├── backend/
│   ├── library/
│   │   ├── models.py                       # Book 모델: search_text, translated_title, translated_author 필드
│   │   ├── search_service.py               # [의미 기반 검색] FAISS 인덱스 관리 + HF API 임베딩 호출
│   │   │                                   # intfloat/multilingual-e5-large 사용, e5 prefix("query:"/"passage:") 적용
│   │   ├── signals.py                      # [신규 도서용] post_save 신호로 search_service.add_book/remove_book 호출 (FAISS 재인덱싱)
│   │   └── views.py                        # smart_search 하이브리드 검색 엔드포인트
│   └── media/search_index/
│       └── books.faiss                     # FAISS 인덱스 파일 (로컬에서 build_faiss_local.py로 빌드 후 git 커밋)
└── docs/project_26-1_IRRS/
    ├── README.md                           # (이 파일)
    ├── serve_qwen.sh                       # vLLM 서버 실행 (Qwen3.6-27B-FP8, 로컬호스트:8000)
    ├── generate_search_text.py             # [기존 도서용] vLLM 서버를 통해 search_text 일괄 생성 → DB 저장
    │                                       # DB 상태 백업을 backups/backup_YYYYMMDD_HHMMSS.json으로 저장
    ├── build_faiss_local.py                # [기존 도서용] 로컬 GPU에서 임베딩 모델 직접 로드 → FAISS 인덱스 빌드
    │                                       # 옵션: --model (minilm/e5/bge-m3, 기본 e5), --out (인덱스 파일명, 기본 books.faiss)
    ├── search_eval.py                      # 검색 시스템 평가 스크립트
    │                                       # 옵션: --model (모델명), --index (인덱스 파일 경로)
    ├── embedding_log.csv                   # [참고용] generate_search_text.py 실행 결과 (title, author, search_text)
    ├── backups/                            # generate_search_text.py 실행 시 생성되는 DB 백업
    │   └── backup_YYYYMMDD_HHMMSS.json     # 형식: [{"book_id": ..., "translated_title": ..., "translated_author": ..., "search_text": ...}, ...]
    └── system_comparison/                  # 검색 시스템 평가 결과
```
