"""번역 필드(translated_title, translated_author, search_text)를 JSON 파일에서 로드해
기존 도서 레코드의 해당 3개 필드만 업데이트한다. 다른 필드는 변경하지 않는다."""
import json
import os

from django.core.management.base import BaseCommand

from library.models import Book

FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "fixtures", "translated_fields.json"
)
BATCH_SIZE = 200


class Command(BaseCommand):
    help = "translated_title / translated_author / search_text 3개 필드만 JSON에서 로드해 업데이트"

    def handle(self, *args, **options):
        with open(FIXTURE_PATH, encoding="utf-8") as f:
            data = json.load(f)

        id_to_data = {item["book_id"]: item for item in data}
        books = list(Book.objects.filter(book_id__in=id_to_data.keys()))

        for book in books:
            row = id_to_data[book.book_id]
            book.translated_title = row.get("translated_title")
            book.translated_author = row.get("translated_author")
            book.search_text = row.get("search_text")

        Book.objects.bulk_update(
            books,
            ["translated_title", "translated_author", "search_text"],
            batch_size=BATCH_SIZE,
        )
        self.stdout.write(self.style.SUCCESS(f"{len(books)}권 번역 필드 업데이트 완료"))
