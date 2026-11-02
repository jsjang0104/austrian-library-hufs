from datetime import datetime
from zoneinfo import ZoneInfo

from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from library.models import Book, Loan
from library.test_utils import IsolatedSearchIndexMixin
from members.models import Member


class LoanAdminExtensionTests(IsolatedSearchIndexMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.admin = Member.objects.create_superuser(
            sid=301, name='Librarian', email='librarian@example.com',
            password='Test-password-42!',
        )
        self.book = Book.objects.create(call_number='ADMIN-1', title='Admin test book')
        self.loan = Loan.objects.create(member=self.admin, book=self.book)
        self.url = reverse('admin:library_loan_changelist')
        self.client.force_login(self.admin)

    def extend(self, *loans):
        return self.client.post(self.url, {
            'action': 'extend_due_date',
            '_selected_action': [loan.pk for loan in loans],
        }, follow=True)

    def test_selected_loan_extends_from_existing_due_date_and_records_audit_log(self):
        seoul = ZoneInfo('Asia/Seoul')
        original_due = datetime(2026, 6, 15, 14, 30, tzinfo=seoul)
        Loan.objects.filter(pk=self.loan.pk).update(due_date=original_due)
        unselected = Loan.objects.create(member=self.admin, book=self.book)
        unselected_due = unselected.due_date
        original_loan_date = self.loan.loan_date

        response = self.extend(self.loan)

        self.assertEqual(response.status_code, 200)
        self.loan.refresh_from_db()
        unselected.refresh_from_db()
        self.book.refresh_from_db()
        self.assertEqual(self.loan.due_date, datetime(2026, 9, 15, 14, 30, tzinfo=seoul))
        self.assertEqual(self.loan.loan_date, original_loan_date)
        self.assertIsNone(self.loan.return_date)
        self.assertEqual(self.book.status, Book.Status.ON_LOAN)
        self.assertEqual(unselected.due_date, unselected_due)
        self.assertContains(response, '1건의 반납 예정일을 3개월 연장했습니다.')
        entry = LogEntry.objects.get(object_id=str(self.loan.pk), action_flag=CHANGE)
        self.assertEqual(entry.user, self.admin)
        self.assertIn('2026-06-15', entry.change_message)
        self.assertIn('2026-09-15', entry.change_message)

    def test_calendar_month_extension_handles_month_ends_leap_year_and_seoul_date(self):
        seoul = ZoneInfo('Asia/Seoul')
        cases = (
            ((2026, 1, 31, 0, 30), (2026, 4, 30, 0, 30)),
            ((2026, 11, 30, 18, 15), (2027, 2, 28, 18, 15)),
            ((2027, 11, 30, 18, 15), (2028, 2, 29, 18, 15)),
        )
        for original, expected in cases:
            with self.subTest(original=original):
                Loan.objects.filter(pk=self.loan.pk).update(
                    due_date=datetime(*original, tzinfo=seoul),
                )

                self.extend(self.loan)

                self.loan.refresh_from_db()
                self.assertEqual(self.loan.due_date, datetime(*expected, tzinfo=seoul))

    def test_mixed_selection_skips_returned_loans_and_missing_due_dates(self):
        returned_book = Book.objects.create(call_number='ADMIN-2', title='Returned book')
        returned = Loan.objects.create(member=self.admin, book=returned_book)
        returned.return_date = timezone.now()
        returned.save(update_fields=['return_date'])
        returned_due = returned.due_date
        undated = Loan.objects.create(member=self.admin, book=self.book)
        Loan.objects.filter(pk=undated.pk).update(due_date=None)

        response = self.extend(self.loan, returned, undated)

        returned.refresh_from_db()
        undated.refresh_from_db()
        returned_book.refresh_from_db()
        self.assertEqual(returned.due_date, returned_due)
        self.assertIsNone(undated.due_date)
        self.assertEqual(returned_book.status, Book.Status.AVAILABLE)
        self.assertContains(response, '1건의 반납 예정일을 3개월 연장했습니다.')
        self.assertContains(response, '반납이 완료되었거나 반납 예정일이 없는 2건은 건너뛰었습니다.')
        self.assertEqual(LogEntry.objects.filter(action_flag=CHANGE).count(), 1)

    def test_staff_with_view_permission_cannot_extend_loans(self):
        viewer = Member.objects.create_user(
            sid=302, name='Viewer', email='viewer@example.com',
            password='Test-password-42!', is_staff=True,
        )
        viewer.user_permissions.add(Permission.objects.get(codename='view_loan'))
        self.client.force_login(viewer)
        original_due = self.loan.due_date

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'value="extend_due_date"')
        self.extend(self.loan)

        self.loan.refresh_from_db()
        self.assertEqual(self.loan.due_date, original_due)
        self.assertFalse(LogEntry.objects.exists())

    def test_staff_with_change_permission_can_run_extension_action(self):
        staff = Member.objects.create_user(
            sid=303, name='Staff', email='staff@example.com',
            password='Test-password-42!', is_staff=True,
        )
        staff.user_permissions.add(Permission.objects.get(codename='change_loan'))
        self.client.force_login(staff)
        original_due = datetime(2026, 7, 10, 12, tzinfo=ZoneInfo('Asia/Seoul'))
        Loan.objects.filter(pk=self.loan.pk).update(due_date=original_due)

        response = self.client.get(self.url)
        self.assertContains(response, 'value="extend_due_date"')
        self.extend(self.loan)

        self.loan.refresh_from_db()
        self.assertEqual(
            self.loan.due_date,
            datetime(2026, 10, 10, 12, tzinfo=ZoneInfo('Asia/Seoul')),
        )
