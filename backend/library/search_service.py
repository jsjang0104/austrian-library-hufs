"""
도서 제목/저자 기반 의미 유사도 검색 서비스.

경량 다국어 문장 임베딩 모델(MiniLM)로 도서를 벡터화하고,
FAISS 인덱스에 저장해 유사도 검색을 수행한다.
모델·인덱스는 프로세스당 1회만 로드되는 싱글턴으로 관리한다.
"""
import os
import threading

import faiss
import numpy as np
from django.conf import settings
from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

INDEX_DIR = os.path.join(settings.MEDIA_ROOT, "search_index")
INDEX_PATH = os.path.join(INDEX_DIR, "books.faiss")

# 모델 로딩과 인덱스 로딩이 서로를 호출하므로 재진입 가능한 락을 사용한다.
_lock = threading.RLock()
_model = None
_index = None


def get_model():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


def book_text(title, author):
    """임베딩 대상 텍스트: 제목 + 저자"""
    return f"{title} {author}".strip() if author else title


def embed_texts(texts):
    """텍스트 배치를 (mean-pooling + L2 정규화된) 임베딩 행렬로 변환"""
    vectors = get_model().encode(
        texts,
        batch_size=32,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return vectors.astype("float32")


def _empty_index():
    dim = get_model().get_embedding_dimension()
    return faiss.IndexIDMap(faiss.IndexFlatIP(dim))


def get_index():
    global _index
    if _index is None:
        with _lock:
            if _index is None:
                if os.path.exists(INDEX_PATH):
                    _index = faiss.read_index(INDEX_PATH)
                else:
                    _index = _empty_index()
    return _index


def save_index():
    os.makedirs(INDEX_DIR, exist_ok=True)
    faiss.write_index(get_index(), INDEX_PATH)


def reset_index():
    """빈 인덱스로 교체 (전체 재구축 시 사용)"""
    global _index
    with _lock:
        _index = _empty_index()
    return _index


def add_books(books):
    """
    여러 도서의 임베딩을 계산해 인덱스에 추가한다.
    대량 적재(전체 재구축) 시 사용하며, 디스크 저장은 호출자가 마지막에 save_index()로 한 번에 처리한다.
    """
    if not books:
        return
    texts = [book_text(book.title, book.author) for book in books]
    vectors = embed_texts(texts)
    ids = np.array([book.book_id for book in books], dtype="int64")
    with _lock:
        get_index().add_with_ids(vectors, ids)


def add_book(book):
    """신규 도서 1건의 임베딩을 계산해 인덱스에 추가하고 즉시 디스크에 저장한다."""
    add_books([book])
    save_index()


def vector_search(query, top_k=20):
    """쿼리와 유사한 도서 top_k를 (book_id, 유사도 점수) 리스트로 반환한다."""
    index = get_index()
    if index.ntotal == 0:
        return []
    query_vector = embed_texts([query])
    scores, ids = index.search(query_vector, top_k)
    return [
        (int(book_id), float(score))
        for book_id, score in zip(ids[0], scores[0])
        if book_id != -1
    ]
