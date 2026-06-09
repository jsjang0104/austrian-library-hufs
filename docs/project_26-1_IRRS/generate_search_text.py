"""
Qwen2.5-32B-Instruct (Ollama)로 기존 도서 전체의 search_text를 일괄 생성한다.

- Book.search_text 필드에 결과를 저장 (search_text가 없는 도서만 처리 → 재실행 안전)
- 완료 후 embedding_log.csv (title, author, search_text) 를 같은 디렉터리에 저장

실행:
  cd /home/hufs/Workspace/Austrian-Library-HUFS
  python docs/project_26-1_IRRS/generate_search_text.py

Ollama가 localhost:11434 에서 실행 중이어야 하며,
  ollama run qwen2.5:32b
로 모델이 pull 되어 있어야 한다.
"""

import csv
import os
import sys

# --- Django 환경 설정 ---
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, BACKEND_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

import requests
from django.db.models import Q
from library.models import Book

# --- 상수 ---
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:32b"
TIMEOUT = 120  # seconds per request
OUT_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "embedding_log.csv")

PROMPT_TEMPLATE = (
    "write down the short German explanation of the following book. "
    "the explanation sentence should be under 20 words. "
    "The book's information is:\n"
    "  - title: {title},\n"
    "  - author: {author},\n"
    "  - category: {category}\n\n"
    "Add the translated Korean text of your German text. "
    "The translated text should be attached next to the original German text."
)


def generate(title: str, author: str, category: str) -> str:
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": PROMPT_TEMPLATE.format(
            title=title,
            author=author or "",
            category=category or "",
        )}],
        "stream": False,
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


def check_ollama():
    try:
        r = requests.get("http://localhost:11434", timeout=5)
        r.raise_for_status()
    except Exception as exc:
        print(f"[오류] Ollama에 연결할 수 없습니다: {exc}")
        print("  ollama serve 를 실행한 뒤 다시 시도하세요.")
        sys.exit(1)


def main():
    check_ollama()

    books = list(
        Book.objects.filter(Q(search_text__isnull=True) | Q(search_text=""))
        .order_by("book_id")
    )
    total = len(books)
    print(f"search_text 미생성 도서: {total}권")

    log_rows = []
    failed = 0

    for i, book in enumerate(books, 1):
        try:
            text = generate(book.title, book.author or "", book.category or "")
            book.search_text = text
            book.save(update_fields=["search_text"])
            log_rows.append({
                "title": book.title,
                "author": book.author or "",
                "search_text": text,
            })
            if i % 100 == 0 or i == total:
                print(f"  [{i}/{total}] {book.title[:50]}")
        except Exception as exc:
            failed += 1
            print(f"  [{i}/{total}] 실패 — {book.title[:40]}: {exc}")

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["title", "author", "search_text"])
        writer.writeheader()
        writer.writerows(log_rows)

    print(f"\n완료: {total - failed}권 생성, {failed}권 실패")
    print(f"CSV 저장: {OUT_CSV}")


if __name__ == "__main__":
    main()
