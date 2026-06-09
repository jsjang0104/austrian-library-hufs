import logging
import os

import requests
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Book

logger = logging.getLogger(__name__)

_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta"
    "/models/gemini-2.0-flash-lite:generateContent"
)

_PROMPT_TEMPLATE = (
    "write down the short German explanation of the following book. "
    "the explanation sentence should be under 20 words. "
    "The book's information is:\n"
    "  - title: {title},\n"
    "  - author: {author},\n"
    "  - category: {category}\n\n"
    "Add the translated Korean text of your German text. "
    "The translated text should be attached next to the original German text."
)


def _generate_search_text(book) -> str | None:
    from django.conf import settings
    api_key = getattr(settings, "GEMINI_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return None
    prompt = _PROMPT_TEMPLATE.format(
        title=book.title,
        author=book.author or "",
        category=book.category or "",
    )
    resp = requests.post(
        f"{_GEMINI_URL}?key={api_key}",
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


@receiver(post_save, sender=Book)
def index_new_book(sender, instance, created, **kwargs):
    """신규 도서가 DB에 저장되는 시점에 search_text를 생성하고 FAISS 인덱스에 추가한다."""
    if not created:
        return

    # Gemini API로 search_text 생성
    try:
        search_text = _generate_search_text(instance)
        if search_text:
            Book.objects.filter(pk=instance.pk).update(search_text=search_text)
            instance.search_text = search_text
    except Exception as exc:
        logger.warning("신규 도서(%s) search_text 생성 실패: %s", instance.book_id, exc)

    # FAISS 인덱스에 추가
    from . import search_service
    try:
        search_service.add_book(instance)
    except Exception as exc:
        logger.warning("신규 도서(%s) 인덱싱 실패 (벡터 검색에서 제외됨): %s", instance.book_id, exc)
