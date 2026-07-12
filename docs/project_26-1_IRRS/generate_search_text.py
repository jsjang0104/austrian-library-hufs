"""
Qwen/Qwen3.6-27B-FP8 (vLLM, OpenAI 호환 서버)로 기존 도서 전체의
translated_title / translated_author / search_text 를 일괄 생성한다.

- 한 번의 LLM 호출(response_format=json_schema)로 4개 필드
  (translated_title, translated_author, german_description, korean_description)
  를 동시에 생성한다.
- search_text = german_description + " " + korean_description
- KNOWN_KOREAN_TITLES 에 등록된 책은 LLM 결과와 무관하게 한국어 정식 제목으로
  translated_title 을 강제 보정한다.
- 실행 전 DB 스냅샷을 docs/project_26-1_IRRS/backups/ 에 백업한다.
- 완료 후 DB 저장 + backend/library/fixtures/translated_fields.json 갱신 +
  docs/project_26-1_IRRS/embedding_log.csv 저장.

실행:
  cd /home/hufs/Workspace/Austrian-Library-HUFS
  python docs/project_26-1_IRRS/generate_search_text.py [--overwrite | --only-missing] [--limit N] [--dry-run] [--workers N] [--min-book-id N]

vLLM이 localhost:8000 에서 OpenAI 호환 엔드포인트로 떠 있어야 한다.
  bash docs/project_26-1_IRRS/serve_qwen.sh
"""

import argparse
import concurrent.futures
import csv
import json
import os
import re
import sys
from datetime import datetime

# --- Django 환경 설정 ---
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, BACKEND_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

import requests
from django.db.models import Q
from library.models import Book

# --- 경로 ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_DIR = os.path.join(SCRIPT_DIR, "backups")
OUT_CSV = os.path.join(SCRIPT_DIR, "embedding_log.csv")
FIXTURE_PATH = os.path.join(BACKEND_DIR, "library", "fixtures", "translated_fields.json")

# --- vLLM 접속 정보 ---
VLLM_BASE_URL = "http://localhost:8000"
VLLM_CHAT_URL = f"{VLLM_BASE_URL}/v1/chat/completions"
VLLM_HEALTH_URL = f"{VLLM_BASE_URL}/health"
MODEL = "Qwen/Qwen3.6-27B-FP8"
TIMEOUT = 180  # seconds per request — 27B 모델 + tensor-parallel 이라 기존보다 여유를 둠
MAX_TOKENS = 1024  # --max-model-len 4096 서버에서 2048은 400 에러 발생, 1024면 충분
BATCH_SIZE = 200
MAX_ATTEMPTS = 3  # JSON 파싱 실패 + 언어 오염 재시도 예산 공유 (총 3회)

RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "book_context",
        "schema": {
            "type": "object",
            "properties": {
                "translated_title": {"type": "string"},
                "translated_author": {"type": "string"},
                "german_description": {"type": "string"},
                "korean_description": {"type": "string"},
            },
            "required": ["translated_title", "translated_author", "german_description", "korean_description"],
            "additionalProperties": False,
        },
        "strict": True,
    },
}

SYSTEM_PROMPT = (
    "You are a meticulous bilingual (German/Korean) library cataloging assistant. "
    "You generate concise, factual search metadata for library books. You must be "
    "honest about uncertainty and must never invent details you do not know. You "
    "must output only German and Korean text -- never Chinese, Arabic, Cyrillic, "
    "or any other language or script, in any field."
)

USER_PROMPT_TEMPLATE = """Book information:
  - title: {title}
  - author: {author}
  - category: {category}
  - language: {language}

Generate exactly these four fields:

1. german_description: A German description of the book in 1-2 sentences (about 25 words total). Mention its likely genre, subject matter, and historical/cultural setting, using vocabulary a library patron might search for. If you do not actually know this specific book's plot or content, do not invent it -- write a conservative description based only on the title, author, and category given above.

2. korean_description: The Korean translation of german_description. If the book has a well-established, idiomatic Korean title used in published translations, work it naturally into the description (for example, Thomas Mann's "Der Zauberberg" is conventionally known in Korean as "마의 산").

3. translated_title: A translation of the title. If language is "KR", translate it into German; otherwise translate it into Korean. Use the established, official published translation ONLY if you are confident you know the correct one. If you are not certain an idiomatic translation exists or what it is, do NOT confidently guess a famous-sounding title -- instead give a careful, literal translation that preserves the key nouns of the original title. Translate the meaning of the title into natural Korean; do NOT merely transliterate German words into Korean sounds. Transliteration is acceptable only for proper names (people, places). Common German catalog nouns must be translated by meaning, e.g. Wörterbuch → 사전, Grammatik → 문법, Geschichte → 역사, Einführung → 입문, Lehrbuch → 교재, Märchen → 동화.

4. translated_author: A translation/transliteration of the author's name, using the same direction and the same confidence rule as translated_title.

Output only German and Korean text in every field -- never Chinese, Arabic, Cyrillic, or any other language or script."""

# 중국어(한자) / 아랍 문자 / 키릴 문자 / 일본어 가나 오염 검사용
_HAN = re.compile(r"[一-鿿]")
_ARABIC = re.compile(r"[؀-ۿ]")
_CYRILLIC = re.compile(r"[Ѐ-ӿ]")
_JAPANESE_KANA = re.compile(r"[぀-ヿ]")  # U+3040–U+30FF: 히라가나 + 가타카나 (중점 ・ 포함)
_CONTAMINATION_PATTERNS = (_HAN, _ARABIC, _CYRILLIC, _JAPANESE_KANA)

# 모델이 붙이는 단어 수 주석 제거 (예: "(24 Wörter)", "(23 단어)")
_WORD_COUNT_PATTERN = re.compile(r"\s*\((?:약\s*)?\d+\s*(?:Wörter?n?|단어|words?)\)\.?")

# LLM이 놓치기 쉬운, 이미 확립된 한국어 정식 제목 (원어 → 한국어 방향에만 적용)
KNOWN_KOREAN_TITLES = {
    "die blechtrommel": "양철북",
    "der zauberberg": "마의 산",
    "die verwandlung": "변신",
    "der process": "소송",
    "der proceß": "소송",
    "das schloss": "성",
    "das schloß": "성",
    "siddhartha": "싯다르타",
    "der steppenwolf": "황야의 이리",
    "die leiden des jungen werther": "젊은 베르테르의 슬픔",
    "faust": "파우스트",
    "im westen nichts neues": "서부 전선 이상 없다",
}


def _is_contaminated(result: dict) -> bool:
    for field in ("translated_title", "translated_author", "german_description", "korean_description"):
        value = result.get(field, "")
        for pattern in _CONTAMINATION_PATTERNS:
            if pattern.search(value):
                return True
    return False


def _strip_word_count_notes(result: dict) -> None:
    """생성 결과에서 단어 수 주석(예: "(24 Wörter)", "(23 단어)")을 제거한다.

    german_description과 korean_description 필드에만 적용한다.
    """
    for field in ("german_description", "korean_description"):
        if field in result:
            result[field] = _WORD_COUNT_PATTERN.sub("", result[field]).strip()


def _apply_known_title_override(book: Book, result: dict) -> None:
    """이미 확립된 한국어 정식 제목이 있으면 translated_title을 강제로 덮어쓴다.

    language == "KR" 인 책(한국어→독일어 방향)은 건드리지 않는다.
    """
    if book.language == "KR":
        return

    title_lower = (book.title or "").lower()
    for known_title_de, known_title_kr in KNOWN_KOREAN_TITLES.items():
        if known_title_de in title_lower:
            result["translated_title"] = known_title_kr
            if known_title_kr not in result["korean_description"]:
                result["korean_description"] += f" 한국어 정식 제목은 '{known_title_kr}'이다."
            return


def generate(title: str, author: str, category: str, language: str) -> dict:
    """vLLM을 호출해 4개 필드를 JSON으로 받아온다. 파싱된 dict를 반환한다."""
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": USER_PROMPT_TEMPLATE.format(
                    title=title or "",
                    author=author or "",
                    category=category or "",
                    language=language or "",
                ),
            },
        ],
        "max_tokens": MAX_TOKENS,
        "response_format": RESPONSE_FORMAT,
    }
    resp = requests.post(VLLM_CHAT_URL, json=payload, timeout=TIMEOUT)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    return json.loads(content)


def generate_with_retry(book: Book) -> dict | None:
    """최대 MAX_ATTEMPTS 회 시도. JSON 파싱 실패/HTTP 오류/언어 오염은 모두 실패로 취급하고
    다음 시도로 넘어간다. 실패 사유를 로그로 남기고, 모두 소진되면 None을 반환한다."""
    last_reason = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            result = generate(book.title, book.author, book.category, book.language)
        except Exception as exc:
            last_reason = f"vLLM 호출/파싱 실패: {exc}"
            print(f"    (시도 {attempt}/{MAX_ATTEMPTS}) {last_reason}")
            continue

        if _is_contaminated(result):
            last_reason = "언어 오염 감지 (중국어/아랍어/키릴 문자/일본어 가나)"
            print(f"    (시도 {attempt}/{MAX_ATTEMPTS}) {last_reason}")
            continue

        _strip_word_count_notes(result)
        return result

    print(f"  [건너뜀] {book.title[:40]} — {MAX_ATTEMPTS}회 시도 모두 실패 ({last_reason})")
    return None


def check_vllm():
    try:
        r = requests.get(VLLM_HEALTH_URL, timeout=5)
        r.raise_for_status()
    except Exception as exc:
        print(f"[오류] vLLM 서버에 연결할 수 없습니다: {exc}")
        print("  bash docs/project_26-1_IRRS/serve_qwen.sh 를 먼저 실행한 뒤 다시 시도하세요.")
        sys.exit(1)


def backup_current_state():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"backup_{timestamp}.json")

    rows = list(
        Book.objects.all()
        .order_by("book_id")
        .values("book_id", "translated_title", "translated_author", "search_text")
    )
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    print(f"백업 저장: {backup_path} ({len(rows)}권)")


def select_target_books(overwrite: bool, limit: int | None, min_book_id: int | None = None):
    qs = Book.objects.all()
    if not overwrite:
        qs = qs.filter(Q(search_text__isnull=True) | Q(search_text=""))
    if min_book_id is not None:
        qs = qs.filter(book_id__gt=min_book_id)
    qs = qs.order_by("book_id")

    books = list(qs)
    if limit is not None:
        books = books[:limit]
    return books


def save_fixture():
    rows = list(
        Book.objects.all()
        .order_by("book_id")
        .values("book_id", "translated_title", "translated_author", "search_text")
    )
    os.makedirs(os.path.dirname(FIXTURE_PATH), exist_ok=True)
    with open(FIXTURE_PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f"fixture 저장: {FIXTURE_PATH} ({len(rows)}권)")


def save_embedding_log(log_rows: list):
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["book_id", "title", "author", "translated_title", "translated_author", "search_text"],
        )
        writer.writeheader()
        writer.writerows(log_rows)
    print(f"CSV 저장: {OUT_CSV} ({len(log_rows)}권)")


def parse_args():
    parser = argparse.ArgumentParser(description="vLLM(Qwen3.6-27B-FP8)로 도서 번역/검색텍스트 일괄 생성")
    parser.add_argument("--overwrite", action="store_true", help="search_text 유무와 상관없이 전체 도서를 재생성")
    parser.add_argument("--only-missing", action="store_true", help="search_text가 없는 도서만 생성 (기본값)")
    parser.add_argument("--limit", type=int, default=None, help="처리할 최대 도서 수")
    parser.add_argument("--dry-run", action="store_true", help="DB/파일에 저장하지 않고 결과만 콘솔에 출력")
    parser.add_argument("--workers", type=int, default=6, help="vLLM 요청 동시 처리 스레드 수")
    parser.add_argument(
        "--min-book-id", type=int, default=None,
        help="book_id가 N보다 큰 도서만 대상 (크래시 후 마지막 [저장] 로그의 book_id로 재개할 때 사용)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    check_vllm()
    backup_current_state()

    books = select_target_books(overwrite=args.overwrite, limit=args.limit, min_book_id=args.min_book_id)
    total = len(books)
    mode = "전체 재생성" if args.overwrite else "미생성분만"
    print(f"대상 도서 ({mode}): {total}권 (workers={args.workers})" + (" [dry-run]" if args.dry_run else ""))

    log_rows = []
    chunk_books = []
    success = 0
    skipped = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        for i, (book, result) in enumerate(zip(books, executor.map(generate_with_retry, books)), 1):
            if result is None:
                skipped += 1
            else:
                _apply_known_title_override(book, result)

                book.translated_title = result["translated_title"]
                book.translated_author = result["translated_author"]
                book.search_text = result["german_description"] + " " + result["korean_description"]

                success += 1
                if not args.dry_run:
                    chunk_books.append(book)
                    log_rows.append({
                        "book_id": book.book_id,
                        "title": book.title,
                        "author": book.author or "",
                        "translated_title": book.translated_title,
                        "translated_author": book.translated_author,
                        "search_text": book.search_text,
                    })

            if i % 100 == 0 or i == total:
                print(f"  [{i}/{total}] {book.title[:50]}")

            if not args.dry_run and chunk_books and (i % 100 == 0 or i == total):
                Book.objects.bulk_update(
                    chunk_books,
                    ["translated_title", "translated_author", "search_text"],
                    batch_size=BATCH_SIZE,
                )
                print(f"  [저장] ~book_id {book.book_id}까지 {len(chunk_books)}권")
                chunk_books = []

    if args.dry_run:
        print("\n[dry-run] DB/fixture/CSV 저장을 건너뜁니다.")
    else:
        save_fixture()
        save_embedding_log(log_rows)

    print(f"\n완료: {success}권 생성, {skipped}권 건너뜀 (전체 대상 {total}권)")


if __name__ == "__main__":
    main()
