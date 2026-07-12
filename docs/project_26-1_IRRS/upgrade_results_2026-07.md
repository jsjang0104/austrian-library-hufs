# AI 검색 시스템 개편 결과 보고 (2026-07-12)

의미 유사도 기반 검색 시스템(Austrian Library AI Project #2)의 2차 개편 결과 정리.
이전 보고서(`정보검색및추천시스템_202400420장지수.pdf`)의 후속 작업이며, 보고서 5.2.1에서
제시한 개선 방향("다국어 도메인에서 더 좋은 LLM으로 맥락 텍스트 재생성")을 실행한 것이다.

## 1. 변경 요약

| 구성 요소 | 기존 (25-1) | 개편 (26-07) |
|---|---|---|
| 맥락 텍스트 생성 LLM | Qwen2.5-14B (Ollama) | **Qwen3.6-27B-FP8** (vLLM, RTX 5090 ×2) |
| 출력 형식 | 자유 텍스트 → regex 후처리 | **structured output (JSON schema 강제)** |
| 품질 검증 | 없음 | 언어 오염 자동 검출(한자·아랍·키릴·가나) + 최대 3회 재생성 |
| 관용 번역 제목 | LLM 재량 (마의 산 실패 사례) | **수동 override 테이블** (양철북·마의 산 등 10권) + LLM |
| 임베딩 모델 | paraphrase-multilingual-MiniLM-L12-v2 (384차원) | **intfloat/multilingual-e5-large** (1024차원, query/passage prefix) |
| 신규 도서 맥락 텍스트 | Gemini API 자동 생성 | **사서가 admin에서 직접 입력** (수정 시 FAISS 자동 재인덱싱) |
| 제목/저자 번역 (기존 도서) | Gemini/Qwen2.5 (프롬프트 누출·오역 다수) | Qwen3.6으로 전량 재생성 |

- 배포 제약(Render 무료 티어, RAM 512MB)은 그대로 유지: 쿼리·신규 도서 임베딩은 HF Inference API 호출,
  백엔드에는 추론 모델이 절대 로드되지 않음. requirements.txt에 torch/sentence-transformers 없음.
- HF API 임베딩과 로컬 SentenceTransformer 임베딩의 벡터 일치 확인: cosine = 1.000000 (e5-large, BGE-M3 모두).
- 전체 4,328권 재생성 완료 (언어 오염 0건, 누락 0건). 운영 DB(Neon)에 직접 반영.

## 2. 평가 방법

- 지표: Recall@30, 도구: `system_comparison/search_eval.py`, 쿼리셋: `labels.py` (29개 쿼리 유효)
- **중요 — ground truth 재매핑**: 기존 labels.py의 book_id는 옛 개발 머신 로컬 DB 기준이어서
  운영(Neon) DB와 ID 공간이 달랐음 (이 때문에 운영 환경에서 기존 하이브리드 검색의 실측 Recall이
  보고서 수치 0.330이 아니라 0.031이었음). 2026-07-12에 제목 exact match로 Neon ID에 재매핑함.
  미매칭 115건은 labels.py 하단 주석에 보존. 따라서 아래 수치는 이전 보고서 수치와 직접 비교 불가하며,
  **같은 재매핑 labels로 측정한 세 시스템 간 비교가 유효한 비교임**.

## 3. 결과 (동일 도구·동일 labels, 29개 쿼리)

| 시스템 | 평균 Recall@30 | 비고 |
|---|---|---|
| 키워드 단일 | 0.023 | |
| 하이브리드 (구): Qwen2.5 텍스트 + MiniLM | 0.031 | 개편 전 운영 상태 |
| **하이브리드 (신): Qwen3.6 텍스트 + e5-large** | **0.339** | 구 대비 **×10.9**, 키워드 대비 ×14.7 |

### 3.1 Ablation (기여도 분리, 통합 GT 28개 쿼리 기준*)

| 조건 | 텍스트 | 임베딩 | Recall@30 |
|---|---|---|---|
| A | 구 (Qwen2.5) | MiniLM | 0.036 |
| B | **신 (Qwen3.6)** | MiniLM | 0.172 (×4.8) |
| **C** | **신** | **e5-large** | **0.438 (×12.2)** |
| D | 신 | BGE-M3 | 0.420 (×11.7) |

*ablation은 쿼리별 관련 제목의 Neon ID 집합(중복 제거)을 GT로 사용해 분모가 3절과 다름.
조건 간 상대 비교용. e5-large가 BGE-M3를 근소하게 앞서 최종 채택.

### 3.2 대표 쿼리별 개선 (A → C)

| 쿼리 | 구 시스템 | 신 시스템 | 비고 |
|---|---|---|---|
| 마의 산 | 0.00 | **1.00** | 이전 보고서의 대표 실패 사례 (관용 번역 제목) |
| 귄터 그라스 | 0.00 | **0.86** | 이전 보고서 Recall 0 사례 |
| 토마스 만 | 0.00 | **0.82** | |
| 베를린 장벽 | 0.00 | **1.00** | |
| 독일 통일 | 0.20 | **1.00** | |
| 독일어 인명 사전 | 0.00 | **0.50** | 보고서 Figure 1의 실제 민원 사례 |
| 독일어 사전 | 0.00 | **0.88** | |
| 파우스트 | 0.17 | **0.66** | |
| 화용론 | 0.00 | **0.50** | |
| 독일문화원 | 0.00 | 0.00 | GT 2권, 여전히 실패 (한계) |

## 4. 한계 및 향후 과제

1. **관용 번역 제목**: Qwen3.6도 한국 출판계 관용 제목을 안정적으로 회상하지 못함
   (예: Die Blechtrommel → '양철북' 실패, thinking mode로도 불가). override 테이블
   (`generate_search_text.py`의 `KNOWN_KOREAN_TITLES`)로 보완했으며, 사서가 필요 시 추가하는 운영 방식.
2. **제목 음차**: 학술서·사전류 제목이 의미 번역 대신 음차되는 사례 잔존 (프롬프트로 완화, 완전 해결은 아님).
3. **GT 품질**: labels 재매핑 과정에서 115건 미매칭(제목 표기 변경 추정), 2개 쿼리 탈락.
   차기 평가에서 GT 재구축 권장 (이전 보고서 5.2.2의 annotator 문제와 동일 맥락).
4. **광범위 쿼리**(현대 문학·고전 소설 등)는 여전히 낮음 — GT가 크고 분산된 실험 설계 문제 (보고서 4.2.3 참고).

## 5. 재현 방법

```bash
# 1) 맥락 텍스트 재생성 (5090 서버, vLLM)
bash docs/project_26-1_IRRS/serve_qwen.sh          # 별도 터미널
python docs/project_26-1_IRRS/generate_search_text.py --overwrite --workers 6

# 2) FAISS 인덱스 빌드 (로컬 GPU)
python docs/project_26-1_IRRS/build_faiss_local.py --model e5 --out books.faiss

# 3) 평가
python docs/project_26-1_IRRS/system_comparison/search_eval.py keyword
python docs/project_26-1_IRRS/system_comparison/search_eval.py hybrid --model e5
```
