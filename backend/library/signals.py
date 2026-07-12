import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Book

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Book)
def index_book(sender, instance, created, **kwargs):
    """도서 저장 시 FAISS 인덱스를 갱신한다.

    신규 도서는 인덱스에 추가하고, 기존 도서는(주로 admin에서 search_text를
    수정한 경우) 기존 벡터를 제거한 뒤 다시 추가해 재인덱싱한다.
    """
    from . import search_service

    if created:
        try:
            search_service.add_book(instance)
        except Exception as exc:
            logger.warning("신규 도서(%s) 인덱싱 실패 (벡터 검색에서 제외됨): %s", instance.book_id, exc)
    else:
        try:
            search_service.remove_book(instance.book_id)
            search_service.add_book(instance)
        except Exception as exc:
            logger.warning("도서(%s) 재인덱싱 실패 (벡터 검색 결과가 최신이 아닐 수 있음): %s", instance.book_id, exc)
