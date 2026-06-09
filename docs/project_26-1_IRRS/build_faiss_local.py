"""
로컬 GPU에서 paraphrase-multilingual-MiniLM-L12-v2를 직접 로드해
DB의 전체 도서를 임베딩하고 FAISS 인덱스를 빌드한다.

실행:
  cd /home/hufs/Workspace/Austrian-Library-HUFS
  python docs/project_26-1_IRRS/build_faiss_local.py
"""

import os
import sys

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

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
FAISS_OUT = os.path.join(BACKEND_DIR, "media", "search_index", "books.faiss")
BATCH_SIZE = 128


def book_text(book) -> str:
    parts = [book.title, book.author or "", book.category or "", book.search_text or ""]
    return " ".join(p for p in parts if p).strip()


def main():
    print("모델 로딩 중...", end=" ", flush=True)
    model = SentenceTransformer(MODEL_NAME, device="cuda")
    print("완료")

    books = list(Book.objects.all().order_by("book_id"))
    print(f"도서 {len(books)}권 임베딩 시작 (배치 크기: {BATCH_SIZE})")

    texts = [book_text(b) for b in books]
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

    os.makedirs(os.path.dirname(FAISS_OUT), exist_ok=True)
    faiss.write_index(index, FAISS_OUT)
    print(f"\nFAISS 인덱스 저장: {FAISS_OUT} ({index.ntotal}개 벡터)")


if __name__ == "__main__":
    main()
