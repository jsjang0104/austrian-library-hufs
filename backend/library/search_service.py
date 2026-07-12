"""
도서 제목/저자 기반 의미 유사도 검색 서비스.

HF Inference API(intfloat/multilingual-e5-large)로 임베딩을 계산하고
FAISS 인덱스에 저장해 유사도 검색을 수행한다.
모델은 Render 서버 메모리에 로드되지 않는다.
"""
import logging
import os
import threading
import time

import faiss
import numpy as np
from django.conf import settings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-large"
EMBEDDING_DIM = 1024  # multilingual-e5-large 출력 차원

# 나중에 모델을 교체할 때(예: BGE-M3) EMBEDDING_MODEL_NAME/EMBEDDING_DIM과
# 이 플래그만 같이 바꾸면 되도록 분리해둔 것. e5 계열은 쿼리/문서에
# 서로 다른 prefix("query: "/"passage: ")가 필요하다.
_USE_E5_PREFIX = True

_HF_BATCH_SIZE = 32

INDEX_DIR = os.path.join(settings.MEDIA_ROOT, "search_index")
INDEX_PATH = os.path.join(INDEX_DIR, "books.faiss")

_lock = threading.RLock()
_index = None


def embed_texts(texts, kind="passage"):
    """
    HF InferenceClient으로 텍스트 배치를 L2 정규화된 임베딩 행렬(float32)로 변환한다.
    e5 계열 모델은 비대칭 prefix가 필요해 kind("query"/"passage")에 맞춰 붙인다.
    429/503 응답에는 지수 백오프로 최대 3회 재시도한다.
    실패 시 예외를 발생시킨다.
    """
    from huggingface_hub import InferenceClient

    if _USE_E5_PREFIX:
        prefix = "query: " if kind == "query" else "passage: "
        texts = [prefix + t for t in texts]

    token = getattr(settings, "HF_API_TOKEN", None) or os.environ.get("HF_API_TOKEN")
    client = InferenceClient(provider="hf-inference", api_key=token)
    all_vectors = []

    for i in range(0, len(texts), _HF_BATCH_SIZE):
        batch = texts[i:i + _HF_BATCH_SIZE]
        for attempt in range(3):
            try:
                result = client.feature_extraction(batch, model=EMBEDDING_MODEL_NAME)
                break
            except Exception as e:
                status_code = getattr(getattr(e, "response", None), "status_code", 0)
                if status_code in (429, 503) and attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                logger.warning("HF InferenceClient 오류: %s", e)
                raise

        arr = np.array(result, dtype="float32")
        if arr.ndim == 3:
            arr = arr.mean(axis=1)
        elif arr.ndim == 1:
            arr = arr.reshape(1, -1)
        all_vectors.extend(arr.tolist())

    vectors = np.array(all_vectors, dtype="float32")
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return vectors / norms


_CATEGORY_TRANSLATION = {
    "문학": "Literatur", "어학": "Sprachwissenschaft",
    "역사": "Geschichte", "사회과학": "Sozialwissenschaften", "기타": "Sonstiges",
}


def book_text(book) -> str:
    """
    임베딩 입력 텍스트:
    title + title(번역) + author + author(번역) + category + category(번역) + 맥락
    """
    parts = [
        book.title,
        book.translated_title or "",
        book.author or "",
        book.translated_author or "",
        book.category or "",
        _CATEGORY_TRANSLATION.get(book.category, ""),
        book.search_text or "",
    ]
    return " ".join(p for p in parts if p).strip()


def _empty_index():
    return faiss.IndexIDMap(faiss.IndexFlatIP(EMBEDDING_DIM))


def get_index():
    global _index
    if _index is None:
        with _lock:
            if _index is None:
                if os.path.exists(INDEX_PATH):
                    _index = faiss.read_index(INDEX_PATH)
                    if _index.d != EMBEDDING_DIM:
                        logger.warning(
                            "인덱스 차원(%d)이 현재 임베딩 모델 차원(%d)과 달라 빈 인덱스로 교체합니다.",
                            _index.d, EMBEDDING_DIM,
                        )
                        _index = _empty_index()
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
    여러 도서의 임베딩을 HF API로 계산해 인덱스에 추가한다.
    디스크 저장은 호출자가 마지막에 save_index()로 한 번에 처리한다.
    """
    if not books:
        return
    texts = [book_text(book) for book in books]
    vectors = embed_texts(texts, kind="passage")
    ids = np.array([book.book_id for book in books], dtype="int64")
    with _lock:
        get_index().add_with_ids(vectors, ids)


def add_book(book):
    """신규 도서 1건의 임베딩을 HF API로 계산해 인덱스에 추가하고 즉시 저장한다."""
    add_books([book])
    save_index()


def remove_book(book_id):
    """인덱스에서 해당 도서의 벡터를 제거한다. 저장은 호출자가 처리한다."""
    with _lock:
        get_index().remove_ids(np.array([book_id], dtype="int64"))


def vector_search(query, top_k=20):
    """쿼리와 유사한 도서 top_k를 (book_id, 유사도 점수) 리스트로 반환한다."""
    index = get_index()
    if index.ntotal == 0:
        return []
    query_vector = embed_texts([query], kind="query")
    scores, ids = index.search(query_vector, top_k)
    return [
        (int(book_id), float(score))
        for book_id, score in zip(ids[0], scores[0])
        if book_id != -1
    ]
