from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase

from library.models import Book


class BookKeywordSearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # bulk_create avoids embedding requests; these tests exercise keyword SQL.
        Book.objects.bulk_create([
            Book(call_number='KO-JOINED', title='독일문인들'),
            Book(call_number='KO-SPACED', title='독일 문인들'),
            Book(call_number='KO-SCATTERED', title='독서 일기와 문학 인물들'),
            Book(call_number='KO-PARTIAL', title='독일 역사'),
            Book(call_number='DE-JOINED', title='DeutscheSchriftsteller'),
            Book(call_number='DE-SPACED', title='Deutsche Schriftsteller'),
            Book(call_number='DE-SCATTERED', title='Deutliche Sprache schafft stille Leser'),
            Book(call_number='DE-OTHER', title='Deutsche Geschichte'),
            Book(call_number='DE-AUTHOR', title='Die Verwandlung', author='Franz Kafka'),
            Book(call_number='DE-UMLAUT', title='Über die schönen Bücher'),
            Book(call_number='TRANSLATED', title='Originaltitel',
                 translated_title='독일 문인들', translated_author='프란츠 카프카'),
        ])

    def setUp(self):
        cache.clear()

    def search(self, query, smart=False, **filters):
        path = '/api/books/smart_search/' if smart else '/api/books/'
        key = 'q' if smart else 'search'
        with patch('library.search_service.vector_search', return_value=[]):
            response = self.client.get(path, {key: query, **filters})
        self.assertEqual(response.status_code, 200)
        return {book['call_number'] for book in response.json()}

    def test_korean_spacing_matches_in_both_directions(self):
        for query in ('독일 문인들', '독일문인들', '  독일\t\n문인들  '):
            with self.subTest(query=query):
                self.assertEqual(self.search(query), {'KO-JOINED', 'KO-SPACED'})

    def test_german_spacing_and_case_match_in_both_directions(self):
        for query in ('deutsche schriftsteller', 'DeutscheSchriftsteller',
                      '  DEUTSCHE\tSchriftsteller  '):
            with self.subTest(query=query):
                self.assertEqual(self.search(query), {'DE-JOINED', 'DE-SPACED'})

    def test_all_words_are_required_without_splitting_into_characters(self):
        self.assertEqual(self.search('문인들 독일'), {'KO-JOINED', 'KO-SPACED'})
        self.assertEqual(self.search('schriftsteller deutsche'), {'DE-JOINED', 'DE-SPACED'})
        self.assertEqual(self.search('문독인일들'), set())
        self.assertEqual(self.search('deutsche missing'), set())

    def test_words_can_match_across_title_and_author(self):
        self.assertEqual(self.search('Kafka Verwandlung'), {'DE-AUTHOR'})

    def test_german_ascii_umlaut_variants_still_match(self):
        for query in ('schoene Buecher', 'SCHOENE BUECHER', 'Über schöne Bücher'):
            with self.subTest(query=query):
                self.assertEqual(self.search(query), {'DE-UMLAUT'})

    def test_catalog_filters_still_apply(self):
        Book.objects.filter(call_number='KO-SPACED').update(language='KR', status='ON_LOAN')
        self.assertEqual(self.search('독일 문인들', language='KR', status='ON_LOAN'), {'KO-SPACED'})
        self.assertEqual(self.search('독일 문인들', category='Literatur'), set())

    def test_blank_search_keeps_the_full_catalog(self):
        self.assertEqual(len(self.search(' \t\n ')), 11)

    def test_stored_whitespace_is_normalized(self):
        Book.objects.filter(call_number='KO-SPACED').update(title='독일\t\n문인들')
        Book.objects.filter(call_number='DE-SPACED').update(title='Deutsche\u00a0Schriftsteller')
        self.assertEqual(self.search('독일문인들'), {'KO-JOINED', 'KO-SPACED'})
        self.assertEqual(self.search('DeutscheSchriftsteller'), {'DE-JOINED', 'DE-SPACED'})

    def test_smart_search_uses_word_matching_for_original_and_translated_fields(self):
        for query in ('독일문인들', '문인들 독일'):
            with self.subTest(query=query):
                self.assertEqual(self.search(query, smart=True),
                                 {'KO-JOINED', 'KO-SPACED', 'TRANSLATED'})
        self.assertEqual(self.search('카프카 프란츠', smart=True), {'TRANSLATED'})
        self.assertEqual(self.search('schoene Buecher', smart=True), {'DE-UMLAUT'})

    def test_smart_search_keeps_keyword_priority_and_deduplicates_vector_results(self):
        translated = Book.objects.get(call_number='TRANSLATED')
        vector = Book.objects.get(call_number='DE-OTHER')
        with patch('library.search_service.vector_search',
                   return_value=[(translated.pk, 0.9), (vector.pk, 0.8)]):
            response = self.client.get('/api/books/smart_search/', {'q': '독일 문인들'})
        self.assertEqual(response.status_code, 200)
        results = [book['call_number'] for book in response.json()]
        self.assertEqual(set(results[:2]), {'KO-JOINED', 'KO-SPACED'})
        self.assertEqual(results[2:], ['TRANSLATED', 'DE-OTHER'])
