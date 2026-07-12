"""
검색 시스템 성능 평가 스크립트

사용법:
  python search_eval.py keyword                          # 키워드 검색
  python search_eval.py hybrid                           # 하이브리드 검색 (로컬 임베딩 + FAISS)
  python search_eval.py hybrid --model e5 --index books.faiss

옵션:
  --model {minilm,e5,bge-m3}  임베딩 모델 선택 (기본값: e5)
  --index PATH               FAISS 인덱스 파일 경로

- labels.py의 전체 쿼리를 자동으로 순회
- K 값은 아래 TOP_K 상수로 조정
"""

import argparse
import csv
import os
import sys

# --- Django 환경 설정 ---
BACKEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend")
)
sys.path.insert(0, BACKEND_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.db.models import Q
from library.models import Book

# --- 상수 ---
TOP_K = 30
MODEL_MAP = {
    "minilm": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "e5": "intfloat/multilingual-e5-large",
    "bge-m3": "BAAI/bge-m3",
}
DEFAULT_FAISS_PATH = os.path.join(BACKEND_DIR, "media", "search_index", "books.faiss")


# --- 검색 함수 ---

def keyword_search(query: str, top_k: int) -> list[Book]:
    return list(
        Book.objects.filter(
            Q(title__icontains=query)
            | Q(author__icontains=query)
            | Q(call_number__icontains=query)
        )[:top_k]
    )


def hybrid_search(query: str, top_k: int, model, index, query_prefix: str = "") -> list[Book]:
    import numpy as np

    keyword_results = keyword_search(query, top_k)
    seen_ids = {b.book_id for b in keyword_results}

    vec = model.encode([query_prefix + query], normalize_embeddings=True).astype("float32")
    scores, ids = index.search(vec, top_k)

    vector_ids = [
        int(i) for i in ids[0]
        if i != -1 and int(i) not in seen_ids
    ]
    vector_books = list(Book.objects.filter(book_id__in=vector_ids))

    return keyword_results + vector_books


# --- Recall@K ---

def recall_at_k(result_ids: list[int], relevant_ids: list[int], k: int) -> float:
    if not relevant_ids:
        return 0.0
    hits = len(set(result_ids[:k]) & set(relevant_ids))
    return hits / len(relevant_ids)


# --- 출력 ---

def print_results(results: list[Book], query: str, labels: dict, mode: str):
    print(f"\n[{mode}] '{query}' 검색 결과 {len(results)}건")
    print(f"{'':>4} {'book_id':>7}  {'제목':<45} {'저자':<20} 분야")
    print("-" * 90)
    for i, b in enumerate(results, 1):
        title = (b.title[:43] + "..") if len(b.title) > 45 else b.title
        author = (b.author or "-")[:18]
        print(f"  {i:>2}. [{b.book_id:>5}]  {title:<45} {author:<20} {b.category}")

    if query in labels:
        relevant_ids = [book_id for book_id, _ in labels[query]]
        result_ids = [b.book_id for b in results]
        r = recall_at_k(result_ids, relevant_ids, TOP_K)
        hits = len(set(result_ids[:TOP_K]) & set(relevant_ids))
        print(f"\n  Recall@{TOP_K}: {r:.3f}  ({hits}/{len(relevant_ids)} relevant found)")
    else:
        print(f"\n  (labels.py에 '{query}' 없음 → Recall 계산 생략)")
    print()


# --- 메인 ---

def main():
    parser = argparse.ArgumentParser(description="검색 성능 평가")
    parser.add_argument(
        "mode",
        choices=["keyword", "hybrid"],
        help="검색 모드",
    )
    parser.add_argument(
        "--model",
        choices=list(MODEL_MAP.keys()),
        default="e5",
        help="임베딩 모델 선택 (기본값: e5)",
    )
    parser.add_argument(
        "--index",
        default=DEFAULT_FAISS_PATH,
        help="FAISS 인덱스 파일 경로 (기본값: books.faiss)",
    )
    args = parser.parse_args()

    mode = args.mode

    # ground truth 로드 (없어도 동작)
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from labels import LABELS
    except Exception:
        LABELS = {}

    # hybrid 모드: 모델/인덱스 미리 로드
    model = index = None
    query_prefix = ""
    if mode == "hybrid":
        if not os.path.exists(args.index):
            print(f"[오류] FAISS 인덱스 없음: {args.index}")
            print("  build_faiss_local.py 를 먼저 실행하세요.")
            sys.exit(1)
        print("모델 로딩 중...", end=" ", flush=True)
        from sentence_transformers import SentenceTransformer
        import faiss
        model_name = MODEL_MAP[args.model]
        model = SentenceTransformer(model_name, device="cuda")
        index = faiss.read_index(args.index)
        print(f"완료 ({index.ntotal}개 벡터)")

        # e5 모델일 때만 "query: " prefix 사용
        if args.model == "e5":
            query_prefix = "query: "

    print(f"\n모드: {mode} | 모델: {args.model} | K={TOP_K} | 쿼리 {len(LABELS)}개\n")

    recalls = []
    csv_rows = []

    for query, label_items in LABELS.items():
        if mode == "keyword":
            results = keyword_search(query, TOP_K)
        else:
            results = hybrid_search(query, TOP_K, model, index, query_prefix)

        print_results(results, query, LABELS, mode)

        relevant_ids = [book_id for book_id, _ in label_items]
        result_ids = [b.book_id for b in results]
        r = recall_at_k(result_ids, relevant_ids, TOP_K)
        recalls.append(r)

        for b in results:
            csv_rows.append({
                "query": query,
                f"recall@{TOP_K}": f"{r:.3f}",
                "relevant_returned": len(set(result_ids[:TOP_K]) & set(relevant_ids)),
                "returned_book": f"{b.title} / {b.author or '-'}",
                "relevance": 1 if b.book_id in set(relevant_ids) else 0,
            })

    if recalls:
        avg = sum(recalls) / len(recalls)
        print(f"\n평균 Recall@{TOP_K}: {avg:.3f}  (쿼리 {len(recalls)}개)")

    if csv_rows:
        out_path = os.path.join(
            os.path.dirname(__file__), f"results_{mode}.csv"
        )
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["query", "relevant_returned", f"recall@{TOP_K}", "returned_book", "relevance"])
            writer.writeheader()
            writer.writerows(csv_rows)
        print(f"CSV 저장: {out_path}")


if __name__ == "__main__":
    main()
