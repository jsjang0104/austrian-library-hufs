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

_CONTEXT_PROMPT = (
    "write down the short German explanation of the following book. "
    "the explanation sentence should be under 20 words. "
    "The book's information is:\n"
    "  - title: {title},\n"
    "  - author: {author},\n"
    "  - category: {category}\n\n"
    "Add the translated Korean text of your German text. "
    "The translated text should be attached next to the original German text."
)

_TRANSLATION_PROMPT_TO_KR = (
    "Translate the following book title and author from German (or English) to Korean. "
    "Reply with ONLY the translated title on line 1 and translated author on line 2. "
    "No explanations.\n"
    "Title: {title}\n"
    "Author: {author}"
)

_TRANSLATION_PROMPT_TO_DE = (
    "Translate the following book title and author from Korean to German. "
    "Reply with ONLY the translated title on line 1 and translated author on line 2. "
    "No explanations.\n"
    "제목: {title}\n"
    "저자: {author}"
)


def _gemini(api_key: str, prompt: str) -> str:
    resp = requests.post(
        f"{_GEMINI_URL}?key={api_key}",
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


def _get_api_key() -> str:
    from django.conf import settings
    return getattr(settings, "GEMINI_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")


@receiver(post_save, sender=Book)
def index_new_book(sender, instance, created, **kwargs):
    """신규 도서 등록 시 search_text·번역 생성 후 FAISS 인덱스에 추가한다."""
    if not created:
        return

    api_key = _get_api_key()
    update_fields = {}

    # 맥락 텍스트 생성
    if api_key:
        try:
            update_fields["search_text"] = _gemini(api_key, _CONTEXT_PROMPT.format(
                title=instance.title,
                author=instance.author or "",
                category=instance.category or "",
            ))
        except Exception as exc:
            logger.warning("신규 도서(%s) search_text 생성 실패: %s", instance.book_id, exc)

    # 제목/저자 번역 생성
    if api_key:
        try:
            to_korean = instance.language != "KR"
            tmpl = _TRANSLATION_PROMPT_TO_KR if to_korean else _TRANSLATION_PROMPT_TO_DE
            lines = [l.strip() for l in _gemini(api_key, tmpl.format(
                title=instance.title, author=instance.author or ""
            )).splitlines() if l.strip()]
            if lines:
                update_fields["translated_title"] = lines[0]
            if len(lines) > 1:
                update_fields["translated_author"] = lines[1]
        except Exception as exc:
            logger.warning("신규 도서(%s) 번역 생성 실패: %s", instance.book_id, exc)

    if update_fields:
        Book.objects.filter(pk=instance.pk).update(**update_fields)
        for k, v in update_fields.items():
            setattr(instance, k, v)

    # FAISS 인덱스에 추가
    from . import search_service
    try:
        search_service.add_book(instance)
    except Exception as exc:
        logger.warning("신규 도서(%s) 인덱싱 실패 (벡터 검색에서 제외됨): %s", instance.book_id, exc)
