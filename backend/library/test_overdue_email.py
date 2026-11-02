from datetime import datetime, time, timedelta
from html import unescape
import re
from smtplib import SMTPException
from urllib.parse import urlencode
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.apps import apps
from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.auth.models import Permission
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from library.models import Book, Loan
from library.test_utils import IsolatedSearchIndexMixin
from members.models import Member


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    OVERDUE_EMAIL_ENABLED=True,
    DEFAULT_FROM_EMAIL='HUFS Library <library@example.com>',
    LIBRARY_CONTACT_EMAIL='contact@example.com',
)
class OverdueEmailAdminTests(IsolatedSearchIndexMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.admin = Member.objects.create_superuser(
            sid=401, name='Librarian', email='librarian@example.com', password='Test-42!',
        )
        self.reader = Member.objects.create_user(
            sid=402, name='Kim & Co', email='reader@example.com', password='Test-42!',
        )
        self.other = Member.objects.create_user(
            sid=403, name='Other Reader', email='other@example.com', password='Test-42!',
        )
        self.today = timezone.localdate()
        self.yesterday = self.at(self.today - timedelta(days=1), time(23, 30))
        self.loan = self.make_loan(self.reader, 'Ein Buch & <Mehr>', self.yesterday)
        self.url = reverse('admin:library_loan_changelist')
        self.client.force_login(self.admin)

    def at(self, day, clock):
        return datetime.combine(day, clock, tzinfo=ZoneInfo('Asia/Seoul'))

    def make_loan(self, member, title, due_date, returned=False):
        book = Book.objects.create(call_number=f'EMAIL-{Book.objects.count() + 1}', title=title)
        loan = Loan.objects.create(member=member, book=book)
        Loan.objects.filter(pk=loan.pk).update(
            due_date=due_date,
            return_date=timezone.now() if returned else None,
        )
        loan.refresh_from_db()
        return loan

    def preview(self, loans=None, **extra):
        return self.client.post(self.url, {
            'action': 'send_overdue_reminders',
            '_selected_action': [loan.pk for loan in (loans or [self.loan])],
            **extra,
        })

    def confirm(self, preview, loans=None, **extra):
        token = preview.context.get('confirmation_token')
        self.assertTrue(token, 'Explicit confirmation must be bound to a signed preview.')
        return self.client.post(self.url, {
            'action': 'send_overdue_reminders',
            '_selected_action': [loan.pk for loan in (loans or [self.loan])],
            'language': preview.context['language'],
            'confirmation_token': token,
            'confirm': '1',
            **extra,
        }, follow=True)

    def test_action_opens_korean_preview_and_never_sends_on_selection(self):
        response = self.preview()

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/library/loan/overdue_email.html')
        self.assertEqual(list(response.context['form'].fields['language'].choices), [
            ('ko', '한국어'), ('de', 'Deutsch (독일어)'),
        ])
        reminder = response.context['reminders'][0]
        self.assertEqual(reminder['email'], 'reader@example.com')
        self.assertEqual(reminder['loan_ids'], [self.loan.pk])
        self.assertIn('Kim & Co', reminder['body'])
        self.assertIn('Ein Buch & <Mehr>', reminder['body'])
        self.assertIn('반납 예정일', reminder['body'])
        self.assertContains(response, '&lt;Mehr&gt;')
        self.assertNotContains(response, '<Mehr>')
        self.assertEqual(len(mail.outbox), 0)

    def test_language_can_be_changed_to_german_before_confirmation(self):
        response = self.preview(language='de', preview='1')

        self.assertTemplateUsed(response, 'admin/library/loan/overdue_email.html')
        reminder = response.context['reminders'][0]
        self.assertIn('Guten Tag Kim & Co', reminder['body'])
        self.assertIn('Mit freundlichen Grüßen', reminder['body'])
        self.assertIn(self.yesterday.strftime('%d.%m.%Y'), reminder['body'])
        self.assertNotIn('반납 예정일', reminder['body'])
        self.assertContains(response, 'value="de" selected')
        self.assertEqual(len(mail.outbox), 0)

    def test_only_selected_unreturned_loans_due_before_today_are_grouped_per_reader(self):
        second = self.make_loan(self.reader, 'Second overdue book', self.yesterday)
        other = self.make_loan(self.other, 'Other overdue book', self.yesterday)
        due_today = self.make_loan(self.reader, 'Due today', self.at(self.today, time(0, 1)))
        future = self.make_loan(self.reader, 'Due later', timezone.now() + timedelta(days=7))
        undated = self.make_loan(self.reader, 'No due date', None)
        returned = self.make_loan(self.reader, 'Already returned', self.yesterday, returned=True)
        self.make_loan(self.reader, 'Unselected overdue book', self.yesterday)

        response = self.preview([self.loan, second, other, due_today, future, undated, returned])

        self.assertTemplateUsed(response, 'admin/library/loan/overdue_email.html')
        reminders = response.context['reminders']
        self.assertEqual(len(reminders), 2)
        self.assertEqual(reminders[0]['loan_ids'], [self.loan.pk, second.pk])
        self.assertIn('Second overdue book', reminders[0]['body'])
        self.assertNotIn('Other overdue book', reminders[0]['body'])
        for title in ('Due today', 'Due later', 'No due date', 'Already returned', 'Unselected overdue book'):
            self.assertNotIn(title, reminders[0]['body'])
        self.assertEqual(response.context['skipped_count'], 4)
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_recipient_is_excluded_without_hiding_valid_recipients(self):
        Member.objects.filter(pk=self.other.pk).update(email='not-an-email')
        other = self.make_loan(self.other, 'Invalid address book', self.yesterday)

        response = self.preview([self.loan, other])

        self.assertTemplateUsed(response, 'admin/library/loan/overdue_email.html')
        self.assertEqual([item['email'] for item in response.context['reminders']], ['reader@example.com'])
        self.assertEqual(response.context['skipped_count'], 1)
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_language_shows_validation_error_and_does_not_send(self):
        response = self.preview(language='fr', confirm='1')

        self.assertTemplateUsed(response, 'admin/library/loan/overdue_email.html')
        self.assertIn('language', response.context['form'].errors)
        self.assertEqual(len(mail.outbox), 0)

    def test_view_only_staff_cannot_preview_or_send(self):
        self.reader.is_staff = True
        self.reader.save(update_fields=['is_staff'])
        self.reader.user_permissions.add(Permission.objects.get(codename='view_loan'))
        self.client.force_login(self.reader)

        response = self.client.get(self.url)
        self.assertNotContains(response, 'value="send_overdue_reminders"')
        response = self.preview(confirm='1')

        self.assertTemplateNotUsed(response, 'admin/library/loan/overdue_email.html')
        self.assertEqual(len(mail.outbox), 0)

    def test_confirmation_sends_private_german_messages_and_preserves_loan_state(self):
        second = self.make_loan(self.reader, 'Second overdue book', self.yesterday)
        other = self.make_loan(self.other, 'Other overdue book', self.yesterday)
        selected = [self.loan, second, other]
        original_due = self.loan.due_date
        preview = self.preview(selected, language='de')

        response = self.confirm(preview, selected, email='attacker@example.com')

        self.assertEqual(len(mail.outbox), 2)
        for message, recipient in zip(mail.outbox, ['reader@example.com', 'other@example.com']):
            self.assertEqual(message.to, [recipient])
            self.assertEqual(message.cc, [])
            self.assertEqual(message.bcc, [])
            self.assertEqual(message.from_email, 'HUFS Library <library@example.com>')
            self.assertEqual(message.reply_to, ['contact@example.com'])
            self.assertIn('Freundliche Erinnerung', message.subject)
            self.assertIn('Guten Tag', message.body)
        self.assertEqual(mail.outbox[0].body, preview.context['reminders'][0]['body'])
        self.assertIn('Ein Buch & <Mehr>', mail.outbox[0].body)
        self.assertIn('Second overdue book', mail.outbox[0].body)
        self.assertNotIn('Other overdue book', mail.outbox[0].body)
        self.loan.refresh_from_db()
        self.loan.book.refresh_from_db()
        self.assertEqual(self.loan.due_date, original_due)
        self.assertIsNone(self.loan.return_date)
        self.assertEqual(self.loan.book.status, Book.Status.ON_LOAN)
        self.assertContains(response, '2명에게 연체 안내 메일을 발송했습니다.')
        delivery = apps.get_model('library', 'OverdueReminderDelivery')
        self.assertEqual(delivery.objects.filter(status='SENT').count(), 2)
        self.assertEqual(LogEntry.objects.filter(action_flag=CHANGE).count(), 3)

    def test_repeated_confirmation_does_not_send_again(self):
        preview = self.preview()

        self.confirm(preview)
        response = self.confirm(preview)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('반납 일정', mail.outbox[0].subject)
        self.assertContains(response, '이미 처리된 1명의 발송 요청은 건너뛰었습니다.')
        delivery = apps.get_model('library', 'OverdueReminderDelivery')
        self.assertEqual(delivery.objects.count(), 1)

    def test_changed_language_requires_new_preview_before_sending(self):
        preview = self.preview()

        refreshed = self.confirm(preview, language='de')

        self.assertEqual(len(mail.outbox), 0)
        self.assertContains(refreshed, '미리보기를 갱신했습니다. 내용을 다시 확인해 주세요.')
        self.assertIn('Guten Tag', refreshed.context['reminders'][0]['body'])
        self.confirm(refreshed)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Freundliche Erinnerung', mail.outbox[0].subject)

    def test_return_or_extension_after_preview_requires_confirmation_again(self):
        for change in (
            {'return_date': timezone.now()},
            {'return_date': None, 'due_date': timezone.now() + timedelta(days=90)},
        ):
            with self.subTest(change=change):
                Loan.objects.filter(pk=self.loan.pk).update(return_date=None, due_date=self.yesterday)
                preview = self.preview()
                Loan.objects.filter(pk=self.loan.pk).update(**change)

                response = self.confirm(preview)

                self.assertEqual(len(mail.outbox), 0)
                self.assertEqual(response.context['reminders'], [])
                self.assertContains(response, '미리보기를 갱신했습니다. 내용을 다시 확인해 주세요.')

    def test_recipient_change_after_preview_does_not_send_to_unconfirmed_address(self):
        preview = self.preview()
        Member.objects.filter(pk=self.reader.pk).update(email='changed@example.com')

        response = self.confirm(preview)

        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(response.context['reminders'][0]['email'], 'changed@example.com')
        self.assertContains(response, '미리보기를 갱신했습니다. 내용을 다시 확인해 주세요.')

    def test_sender_change_after_preview_requires_new_confirmation(self):
        preview = self.preview()

        with override_settings(DEFAULT_FROM_EMAIL='changed-sender@example.com'):
            response = self.confirm(preview)

        self.assertEqual(len(mail.outbox), 0)
        self.assertContains(response, '미리보기를 갱신했습니다. 내용을 다시 확인해 주세요.')

    def test_preview_token_cannot_be_used_by_another_administrator(self):
        preview = self.preview()
        another = Member.objects.create_superuser(
            sid=404, name='Other admin', email='admin2@example.com', password='Test-42!',
        )
        self.client.force_login(another)

        response = self.confirm(preview)

        self.assertEqual(len(mail.outbox), 0)
        self.assertContains(response, '미리보기가 만료되었거나 유효하지 않습니다.')

    def test_missing_tampered_and_expired_tokens_do_not_send(self):
        preview = self.preview()
        for token in ('', preview.context.get('confirmation_token', '') + 'tampered'):
            with self.subTest(token=token):
                response = self.confirm(preview, confirmation_token=token)
                self.assertEqual(len(mail.outbox), 0)
                self.assertContains(response, '미리보기가 만료되었거나 유효하지 않습니다.')
        with patch('django.core.signing.time.time', return_value=timezone.now().timestamp() - 1900):
            expired = self.preview()

        response = self.confirm(expired)

        self.assertEqual(len(mail.outbox), 0)
        self.assertContains(response, '미리보기가 만료되었거나 유효하지 않습니다.')

    def test_mail_configuration_is_required_but_preview_remains_available(self):
        for settings in (
            {'OVERDUE_EMAIL_ENABLED': False},
            {'DEFAULT_FROM_EMAIL': ''},
            {'DEFAULT_FROM_EMAIL': 'invalid-address'},
            {'EMAIL_BACKEND': 'django.core.mail.backends.smtp.EmailBackend', 'EMAIL_HOST': ''},
        ):
            with self.subTest(settings=settings), override_settings(**settings):
                preview = self.preview()
                self.assertFalse(preview.context['can_send'])
                self.assertTrue(preview.context.get('configuration_error'))

                response = self.confirm(preview)

                self.assertEqual(len(mail.outbox), 0)
                self.assertTemplateUsed(response, 'admin/library/loan/overdue_email.html')

    def test_one_smtp_failure_does_not_hide_other_success_or_retry_same_request(self):
        other = self.make_loan(self.other, 'Other overdue book', self.yesterday)
        selected = [self.loan, other]
        preview = self.preview(selected)
        real_send = mail.EmailMessage.send

        def fail_first(message, *args, **kwargs):
            if message.to == ['reader@example.com']:
                raise SMTPException('Mail service unavailable')
            return real_send(message, *args, **kwargs)

        with self.assertLogs('library.overdue_email', level='ERROR'), patch(
            'django.core.mail.message.EmailMessage.send', autospec=True, side_effect=fail_first,
        ):
            response = self.confirm(preview, selected)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['other@example.com'])
        self.assertContains(response, '1명에게 연체 안내 메일을 발송했습니다.')
        self.assertContains(response, '1명의 메일 발송을 완료하지 못했습니다.')
        delivery = apps.get_model('library', 'OverdueReminderDelivery')
        self.assertEqual(delivery.objects.filter(status='SENT').count(), 1)
        self.assertEqual(delivery.objects.filter(status='FAILED').count(), 1)

        self.confirm(preview, selected)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(LogEntry.objects.filter(action_flag=CHANGE).count(), 1)

    def test_final_confirmation_requires_csrf(self):
        preview = self.preview()
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)

        response = client.post(self.url, {
            'action': 'send_overdue_reminders', '_selected_action': [self.loan.pk],
            'language': 'ko', 'confirm': '1',
            'confirmation_token': preview.context.get('confirmation_token', ''),
        })

        self.assertEqual(response.status_code, 403)
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(DATA_UPLOAD_MAX_NUMBER_FIELDS=12)
    def test_select_all_uses_a_compact_signed_selection_for_refresh_and_confirmation(self):
        for number in range(10):
            self.make_loan(self.reader, f'Historical loan {number}', self.yesterday)
        preview = self.preview(select_across='1')

        def submit_rendered_form(response, button):
            fields = re.findall(
                r'<input type="hidden" name="([^"]+)" value="([^"]*)">',
                response.content.decode(),
            )
            data = [(key, unescape(value)) for key, value in fields]
            data.extend([('language', 'de'), (button, '1')])
            return self.client.post(
                self.url, urlencode(data), content_type='application/x-www-form-urlencoded', follow=True,
            )

        refreshed = submit_rendered_form(preview, 'preview')

        self.assertEqual(refreshed.status_code, 200)
        self.assertTemplateUsed(refreshed, 'admin/library/loan/overdue_email.html')
        self.assertEqual(len(refreshed.context['reminders'][0]['loan_ids']), 11)
        self.assertEqual(len(mail.outbox), 0)

        response = submit_rendered_form(refreshed, 'confirm')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Historical loan 9', mail.outbox[0].body)
        self.assertIn('Freundliche Erinnerung', mail.outbox[0].subject)

    def test_slow_batch_reports_unattempted_recipients_and_can_resume_without_duplicates(self):
        third = Member.objects.create_user(
            sid=405, name='Third Reader', email='third@example.com', password='Test-42!',
        )
        other = self.make_loan(self.other, 'Other overdue book', self.yesterday)
        third_loan = self.make_loan(third, 'Third overdue book', self.yesterday)
        selected = [self.loan, other, third_loan]
        preview = self.preview(selected)

        with patch('library.overdue_email.monotonic', side_effect=[0, 0, 20], create=True):
            response = self.confirm(preview, selected)

        self.assertEqual(len(mail.outbox), 1)
        self.assertContains(response, '처리 시간 제한으로 2명의 발송을 시작하지 못했습니다.')
        delivery = apps.get_model('library', 'OverdueReminderDelivery')
        self.assertEqual(delivery.objects.count(), 1)

        self.confirm(preview, selected)

        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual([message.to for message in mail.outbox], [
            ['reader@example.com'], ['other@example.com'], ['third@example.com'],
        ])
        self.assertEqual(delivery.objects.filter(status='SENT').count(), 3)
