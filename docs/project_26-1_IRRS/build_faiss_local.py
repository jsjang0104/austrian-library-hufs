"""
로컬 GPU에서 임베딩 모델을 직접 로드해
DB의 전체 도서를 임베딩하고 FAISS 인덱스를 빌드한다.

실행:
  cd /home/hufs/Workspace/Austrian-Library-HUFS
  python docs/project_26-1_IRRS/build_faiss_local.py --model e5 --out books.faiss

옵션:
  --model {minilm,e5,bge-m3}  임베딩 모델 선택 (기본값: e5)
  --out FILENAME             저장할 FAISS 인덱스 파일명 (기본값: books.faiss)
"""

import os
import sys
import argparse

BACKEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "backend")
)
sys.path.insert(0, BACKEND_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from library.models import Book
from library.search_service import book_text

MODEL_MAP = {
    "minilm": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "e5": "intfloat/multilingual-e5-large",
    "bge-m3": "BAAI/bge-m3",
}
BATCH_SIZE = 128


def main():
    parser = argparse.ArgumentParser(description="FAISS 인덱스 빌드")
    parser.add_argument(
        "--model",
        choices=list(MODEL_MAP.keys()),
        default="e5",
        help="임베딩 모델 선택 (기본값: e5)",
    )
    parser.add_argument(
        "--out",
        default="books.faiss",
        help="저장할 FAISS 인덱스 파일명 (기본값: books.faiss)",
    )
    args = parser.parse_args()

    model_name = MODEL_MAP[args.model]
    faiss_out = os.path.join(BACKEND_DIR, "media", "search_index", args.out)

    print("모델 로딩 중...", end=" ", flush=True)
    model = SentenceTransformer(model_name, device="cuda")
    print("완료")

    books = list(Book.objects.all().order_by("book_id"))
    print(f"도서 {len(books)}권 임베딩 시작 (배치 크기: {BATCH_SIZE})")

    texts = [book_text(b) for b in books]

    # e5 모델일 때만 "passage: " prefix 추가
    if args.model == "e5":
        texts = ["passage: " + t for t in texts]

    ids = np.array([b.book_id for b in books], dtype="int64")

    vectors = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        normalize_embeddings=True,
        show_progress_bar=True,
        device="cuda",
    ).astype("float32")

    index = faiss.IndexIDMap(faiss.IndexFlatIP(vectors.shape[1]))
    index.add_with_ids(vectors, ids)

    os.makedirs(os.path.dirname(faiss_out), exist_ok=True)
    faiss.write_index(index, faiss_out)
    print(f"\nFAISS 인덱스 저장: {faiss_out} ({index.ntotal}개 벡터)")


if __name__ == "__main__":
    main()
