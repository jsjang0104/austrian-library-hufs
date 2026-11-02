"""Build individual, explicitly previewed overdue reminders."""
from datetime import datetime, time
from email.utils import parseaddr
import hashlib
import json
import logging
from time import monotonic
from uuid import UUID, uuid4, uuid5

from django.conf import settings
from django.core import mail, signing
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.template.loader import render_to_string
from django.utils import timezone

from .models import OverdueReminderDelivery


logger = logging.getLogger(__name__)
PREVIEW_SALT = 'library.overdue-email-preview'
PREVIEW_MAX_AGE = 30 * 60
SEND_TIME_BUDGET_SECONDS = 10

SUBJECTS = {
    'ko': '[한국외국어대학교 오스트리아 도서관] 대출 도서 반납 일정 확인 부탁드립니다',
    'de': '[Österreichische Bibliothek der HUFS] Freundliche Erinnerung an die Rückgabe Ihrer Bücher',
}


def build_overdue_reminders(queryset, language):
    tz = timezone.get_default_timezone()
    today = timezone.localdate(timezone=tz)
    cutoff = timezone.make_aware(datetime.combine(today, time.min), tz)
    total = queryset.count()
    groups = {}
    eligible = queryset.filter(
        return_date__isnull=True, due_date__lt=cutoff,
    ).select_related('member', 'book').order_by('member_id', 'due_date', 'loan_id')
    for loan in eligible:
        try:
            validate_email(loan.member.email)
        except ValidationError:
            continue
        group = groups.setdefault(loan.member_id, {
            'member_id': loan.member_id,
            'name': loan.member.name,
            'email': loan.member.email,
            'loan_ids': [],
            'books': [],
        })
        due_date = timezone.localtime(loan.due_date, tz)
        group['loan_ids'].append(loan.pk)
        group['books'].append({
            'title': loan.book.title,
            'call_number': loan.book.call_number,
            'due_date': due_date.strftime('%Y-%m-%d' if language == 'ko' else '%d.%m.%Y'),
            'overdue_days': (today - due_date.date()).days,
        })

    reminders = []
    for group in groups.values():
        body = render_to_string(f'library/emails/overdue_{language}.txt', {
            **group,
            'contact_email': settings.LIBRARY_CONTACT_EMAIL,
        }).strip()
        reminders.append({
            key: group[key] for key in ('member_id', 'name', 'email', 'loan_ids')
        } | {'subject': SUBJECTS[language], 'body': body})
    return reminders, total - sum(len(item['loan_ids']) for item in reminders)


def mail_configuration_error():
    if not settings.OVERDUE_EMAIL_ENABLED:
        return '메일 발송이 아직 활성화되지 않았습니다. 발신 계정 설정 후 이용해 주세요.'
    try:
        validate_email(parseaddr(settings.DEFAULT_FROM_EMAIL)[1])
        validate_email(settings.LIBRARY_CONTACT_EMAIL)
    except ValidationError:
        return '유효한 발신 주소와 도서관 회신 주소를 설정해 주세요.'
    if settings.EMAIL_BACKEND == 'library.gmail_backend.GmailApiEmailBackend':
        if not all((settings.GMAIL_CLIENT_ID, settings.GMAIL_CLIENT_SECRET, settings.GMAIL_REFRESH_TOKEN)):
            return 'Google 메일 계정 연결 설정을 완료한 후 발송할 수 있습니다.'
    if settings.EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend':
        if not settings.EMAIL_HOST:
            return '메일 서버 설정을 완료한 후 발송할 수 있습니다.'
        if settings.EMAIL_USE_TLS and settings.EMAIL_USE_SSL:
            return '메일 서버의 보안 연결 설정을 확인해 주세요. TLS와 SSL은 동시에 사용할 수 없습니다.'
    return ''


def preview_payload(user_id, language, selected_ids, reminders):
    content = json.dumps({
        'reminders': reminders,
        'sender': settings.DEFAULT_FROM_EMAIL,
        'reply_to': settings.LIBRARY_CONTACT_EMAIL,
    }, sort_keys=True, ensure_ascii=False)
    return {
        'user_id': user_id,
        'language': language,
        'selected_ids': sorted(selected_ids),
        'fingerprint': hashlib.sha256(content.encode()).hexdigest(),
    }


def sign_preview(payload):
    return signing.dumps({**payload, 'batch_id': uuid4().hex}, salt=PREVIEW_SALT, compress=True)


def send_confirmed_reminders(reminders, batch_id, language, sent_by):
    result = {'sent': 0, 'failed': 0, 'duplicate': 0, 'deferred': 0, 'sent_loan_ids': []}
    started = monotonic()
    connection = mail.get_connection(timeout=min(settings.EMAIL_TIMEOUT, 5))
    try:
        for index, reminder in enumerate(reminders):
            # Keep manual batches short enough to report outcomes in the web
            # request. Deferred recipients have no claim and can be resumed.
            if monotonic() - started >= SEND_TIME_BUDGET_SECONDS:
                result['deferred'] = len(reminders) - index
                break
            # Commit the unique claim before calling the mail provider. Repeated
            # POSTs cannot send again, even if the delivery outcome was uncertain.
            delivery, created = OverdueReminderDelivery.objects.get_or_create(
                pk=uuid5(UUID(batch_id), str(reminder['member_id'])),
                defaults={
                    'member_id': reminder['member_id'], 'sent_by': sent_by,
                    'recipient_email': reminder['email'], 'language': language,
                },
            )
            if not created:
                result['duplicate'] += 1
                continue
            try:
                connection.open()
                accepted = mail.EmailMessage(
                    subject=reminder['subject'], body=reminder['body'],
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[reminder['email']], reply_to=[settings.LIBRARY_CONTACT_EMAIL],
                    connection=connection,
                ).send(fail_silently=False)
                if accepted != 1:
                    raise RuntimeError('The email backend did not accept the message.')
            except Exception:
                delivery.status = OverdueReminderDelivery.Status.FAILED
                delivery.save(update_fields=['status'])
                result['failed'] += 1
                logger.exception('연체 메일 발송 처리 실패 (회원 ID %s)', reminder['member_id'])
            else:
                delivery.status = OverdueReminderDelivery.Status.SENT
                delivery.sent_at = timezone.now()
                delivery.save(update_fields=['status', 'sent_at'])
                result['sent'] += 1
                result['sent_loan_ids'].extend(reminder['loan_ids'])
    finally:
        connection.close()
    return result
