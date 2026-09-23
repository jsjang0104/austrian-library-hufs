from unittest.mock import patch

import numpy as np
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from library import search_service
from library.models import Book, Loan, Notice
from library.test_utils import IsolatedSearchIndexMixin
from manager.models import Manager
from members.models import Member


class LibrarySecurityTests(IsolatedSearchIndexMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.member = Member.objects.create_user(
            sid=101, name='Reader', email='reader@example.com', password='Random-passphrase-42!'
        )
        self.other = Member.objects.create_user(
            sid=102, name='Other', email='other@example.com', password='Random-passphrase-42!'
        )
        self.manager = Manager.objects.create(manager_sid=self.other)
        self.book = Book.objects.create(
            call_number='SEC-1', title='Security book', registrar_manager=self.manager,
            modification_manager=self.manager,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.member)
        self.hf.reset_mock()
        cache.clear()

    def test_generic_create_cannot_attribute_loan_to_another_member(self):
        response = self.client.post('/api/loans/', {
            'member': self.other.pk, 'book': self.book.pk,
        })
        self.assertEqual(response.status_code, 405)
        self.assertFalse(Loan.objects.exists())
        self.book.refresh_from_db()
        self.assertEqual(self.book.status, Book.Status.AVAILABLE)

    def test_generic_update_and_delete_cannot_tamper_with_loan_history(self):
        loan = Loan.objects.create(member=self.member, book=self.book)
        original_due_date = loan.due_date
        for method in ('patch', 'put', 'delete'):
            with self.subTest(method=method):
                response = getattr(self.client, method)(f'/api/loans/{loan.pk}/', {
                    'member': self.other.pk, 'book': self.book.pk,
                    'due_date': '2099-01-01T00:00:00Z',
                })
                self.assertEqual(response.status_code, 405)
        loan.refresh_from_db()
        self.assertEqual(loan.member_id, self.member.pk)
        self.assertEqual(loan.due_date, original_due_date)

    def test_other_members_checkin_is_not_found(self):
        loan = Loan.objects.create(member=self.other, book=self.book)
        response = self.client.post(f'/api/loans/{loan.pk}/checkin/')
        self.assertEqual(response.status_code, 404)
        loan.refresh_from_db()
        self.assertIsNone(loan.return_date)

    def test_invalid_book_ids_return_validation_error(self):
        for book_id in ('not-a-number', -1, 0, True, 1.5, [], {}, 2**64):
            with self.subTest(book_id=book_id):
                response = self.client.post('/api/loans/checkout/', {'book_id': book_id}, format='json')
                self.assertEqual(response.status_code, 400)
        self.assertFalse(Loan.objects.exists())

    def test_lost_book_cannot_be_checked_out(self):
        Book.objects.filter(pk=self.book.pk).update(status=Book.Status.LOST)
        response = self.client.post('/api/loans/checkout/', {'book_id': self.book.pk})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Loan.objects.exists())

    def test_checkout_and_checkin_preserve_state_without_external_inference(self):
        response = self.client.post('/api/loans/checkout/', {'book_id': self.book.pk})
        self.assertEqual(response.status_code, 201)
        loan = Loan.objects.get(pk=response.data['loan_id'])
        self.assertEqual(loan.member_id, self.member.pk)
        self.assertEqual((loan.due_date - loan.loan_date).days, 13)
        self.book.refresh_from_db()
        self.assertEqual(self.book.status, Book.Status.ON_LOAN)
        duplicate = self.client.post('/api/loans/checkout/', {'book_id': self.book.pk})
        self.assertEqual(duplicate.status_code, 400)
        response = self.client.post(f'/api/loans/{loan.pk}/checkin/')
        self.assertEqual(response.status_code, 200)
        self.book.refresh_from_db()
        loan.refresh_from_db()
        self.assertEqual(self.book.status, Book.Status.AVAILABLE)
        self.assertIsNotNone(loan.return_date)
        self.assertEqual(self.client.post(f'/api/loans/{loan.pk}/checkin/').status_code, 400)
        self.assertEqual(self.hf.call_count, 0)

    def test_embedding_text_changes_still_refresh_the_index(self):
        self.book.title = 'Changed title'
        self.book.save(update_fields=['title'])
        self.assertEqual(search_service.get_index().ntotal, 1)
        self.assertEqual(self.hf.call_count, 1)

    def test_public_catalog_and_notices_do_not_disclose_staff_student_ids(self):
        notice = Notice.objects.create(title='Library news', content='Opening hours', manager=self.manager)
        self.client.force_authenticate(None)
        book_response = self.client.get(f'/api/books/{self.book.pk}/')
        notice_response = self.client.get(f'/api/notices/{notice.pk}/')
        self.assertEqual(book_response.status_code, 200)
        self.assertEqual(notice_response.status_code, 200)
        self.assertNotIn('registrar_manager', book_response.data)
        self.assertNotIn('modification_manager', book_response.data)
        self.assertNotIn('manager', notice_response.data)

    def test_smart_search_rejects_oversized_input_before_inference(self):
        self.client.force_authenticate(None)
        response = self.client.get('/api/books/smart_search/', {'q': 'x' * 501})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.hf.call_count, 0)

    def test_smart_search_rate_limit_blocks_repeated_anonymous_inference(self):
        self.client.force_authenticate(None)
        from rest_framework.throttling import ScopedRateThrottle
        with patch.dict(ScopedRateThrottle.THROTTLE_RATES, {'smart_search': '2/min'}):
            first = self.client.get('/api/books/smart_search/', {'q': 'security'})
            second = self.client.get('/api/books/smart_search/', {'q': 'security'})
            third = self.client.get('/api/books/smart_search/', {'q': 'security'})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(third.status_code, 429)
        self.assertEqual(self.hf.call_count, 2)

    def test_hf_requests_have_a_bounded_timeout(self):
        configured_timeouts = []

        def inference(client, texts, **kwargs):
            configured_timeouts.append(client.timeout)
            return np.ones((len(texts), 1024), dtype='float32')

        self.hf.side_effect = inference
        vectors = search_service.embed_texts(['A query'], kind='query')
        self.assertEqual(vectors.shape, (1, 1024))
        self.assertEqual(len(configured_timeouts), 1)
        self.assertIsNotNone(configured_timeouts[0])
        self.assertLessEqual(configured_timeouts[0], 10)
