"""Django DB의 전체 도서를 임베딩하여 검색용 FAISS 인덱스를 새로 구축한다."""
from django.core.management.base import BaseCommand

from library import search_service
from library.models import Book

BATCH_SIZE = 64


class Command(BaseCommand):
    help = "전체 도서(title + author)를 임베딩해 FAISS 인덱스를 처음부터 다시 구축한다."

    def handle(self, *args, **options):
        total = Book.objects.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("등록된 도서가 없어 인덱스를 구축하지 않았습니다."))
            return

        search_service.reset_index()

        indexed = 0
        batch = []
        for book in Book.objects.all().iterator(chunk_size=BATCH_SIZE):
            batch.append(book)
            if len(batch) >= BATCH_SIZE:
                search_service.add_books(batch)
                indexed += len(batch)
                self.stdout.write(f"  {indexed}/{total}권 임베딩 완료")
                batch = []
        if batch:
            search_service.add_books(batch)
            indexed += len(batch)

        search_service.save_index()
        self.stdout.write(self.style.SUCCESS(
            f"총 {indexed}권을 임베딩하여 인덱스를 구축했습니다 → {search_service.INDEX_PATH}"
        ))
