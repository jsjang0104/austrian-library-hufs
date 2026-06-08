from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Book


@receiver(post_save, sender=Book)
def index_new_book(sender, instance, created, **kwargs):
    """신규 도서가 DB에 저장되는 시점에 해당 도서 1건만 임베딩해 검색 인덱스에 추가한다."""
    if not created:
        return
    from . import search_service
    search_service.add_book(instance)
