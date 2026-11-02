import base64
from email import policy
from email.parser import BytesParser
import importlib.util
import json
from urllib.parse import parse_qs
from unittest.mock import patch

from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings
import requests


BACKEND = 'library.gmail_backend.GmailApiEmailBackend'
SENDER = 'Österreichische Bibliothek HUFS <deutsch@hufs.ac.kr>'
SEND_URL = 'https://gmail.googleapis.com/gmail/v1/users/deutsch%40hufs.ac.kr/messages/send'


@override_settings(
    EMAIL_BACKEND=BACKEND,
    DEFAULT_FROM_EMAIL=SENDER,
    GMAIL_CLIENT_ID='test-client-id',
    GMAIL_CLIENT_SECRET='test-client-secret',
    GMAIL_REFRESH_TOKEN='test-refresh-token',
)
class GmailApiBackendTests(SimpleTestCase):
    def setUp(self):
        self.calls = []
        self.token_status = 200
        self.send_status = 200
        self.token_data = {'access_token': 'test-access-token', 'expires_in': 3600}
        self.send_data = {'id': 'accepted-message-id'}
        self.transport = patch('requests.sessions.Session.send', side_effect=self.respond)
        self.transport.start()
        self.addCleanup(self.transport.stop)

    def respond(self, request, **kwargs):
        self.calls.append((request, kwargs))
        response = requests.Response()
        response.request = request
        response.url = request.url
        if request.url == 'https://oauth2.googleapis.com/token':
            response.status_code = self.token_status
            data = self.token_data
        elif request.url == SEND_URL:
            response.status_code = self.send_status
            data = self.send_data
        else:
            raise AssertionError(f'Unexpected network endpoint: {request.url}')
        response._content = json.dumps(data).encode()
        response.headers['Content-Type'] = 'application/json'
        return response

    def connection(self, **kwargs):
        self.assertIsNotNone(
            importlib.util.find_spec('library.gmail_backend'),
            'Render Free requires a Gmail HTTPS backend rather than SMTP.',
        )
        return mail.get_connection(timeout=3, **kwargs)

    def message(self, connection, **kwargs):
        return mail.EmailMessage(
            subject='정중한 안내 — Freundliche Erinnerung',
            body='안녕하세요. 도서 반납을 부탁드립니다. Vielen Dank für Ihre Unterstützung.',
            from_email=SENDER, to=['reader@example.com'],
            reply_to=['deutsch@hufs.ac.kr'], connection=connection, **kwargs,
        )

    def test_sends_utf8_mime_over_sender_bound_https_with_offline_authorization(self):
        message = self.message(self.connection())

        self.assertEqual(message.send(), 1)

        self.assertEqual(len(self.calls), 2)
        token_request, token_options = self.calls[0]
        self.assertEqual(token_request.method, 'POST')
        self.assertEqual(parse_qs(token_request.body), {
            'client_id': ['test-client-id'], 'client_secret': ['test-client-secret'],
            'refresh_token': ['test-refresh-token'], 'grant_type': ['refresh_token'],
        })
        request, options = self.calls[1]
        self.assertEqual(request.url, SEND_URL)
        self.assertEqual(request.headers['Authorization'], 'Bearer test-access-token')
        for config in (token_options, options):
            self.assertEqual(config['timeout'], 3)
            self.assertFalse(config['allow_redirects'])
        raw = json.loads(request.body)['raw']
        decoded = BytesParser(policy=policy.default).parsebytes(base64.urlsafe_b64decode(raw))
        self.assertEqual(str(decoded['From']), SENDER)
        self.assertEqual(str(decoded['To']), 'reader@example.com')
        self.assertEqual(str(decoded['Reply-To']), 'deutsch@hufs.ac.kr')
        self.assertEqual(str(decoded['Subject']), message.subject)
        self.assertEqual(decoded.get_content().strip(), message.body)

    def test_explicit_connection_reuses_authorization_for_distinct_recipients(self):
        connection = self.connection()
        with connection:
            first = self.message(connection)
            second = self.message(connection)
            second.to = ['other@example.com']
            self.assertEqual(first.send(), 1)
            self.assertEqual(second.send(), 1)

        self.assertEqual([request.url for request, _ in self.calls], [
            'https://oauth2.googleapis.com/token', SEND_URL, SEND_URL,
        ])
        first_raw = json.loads(self.calls[1][0].body)['raw']
        second_raw = json.loads(self.calls[2][0].body)['raw']
        parser = BytesParser(policy=policy.default)
        self.assertEqual(parser.parsebytes(base64.urlsafe_b64decode(first_raw))['To'], 'reader@example.com')
        self.assertEqual(parser.parsebytes(base64.urlsafe_b64decode(second_raw))['To'], 'other@example.com')

    def test_empty_messages_and_missing_recipients_do_not_contact_google(self):
        connection = self.connection()
        self.assertEqual(connection.send_messages([]), 0)
        message = self.message(connection)
        message.to = []
        self.assertEqual(connection.send_messages([message]), 0)
        self.assertEqual(self.calls, [])

    def test_missing_oauth_credentials_fail_before_network_activity(self):
        connection = self.connection()
        with override_settings(GMAIL_REFRESH_TOKEN=''):
            with self.assertRaises(ImproperlyConfigured):
                self.message(connection).send()
        self.assertEqual(self.calls, [])

    def test_different_from_address_cannot_silently_use_another_account(self):
        message = self.message(self.connection())
        message.from_email = 'other-account@example.com'

        with self.assertRaisesMessage(RuntimeError, 'sender'):
            message.send()

        self.assertEqual(self.calls, [])

    def test_authorization_failure_never_sends_and_does_not_expose_credentials(self):
        connection = self.connection()
        self.token_status = 400
        self.token_data = {'error': 'invalid_grant', 'error_description': 'test-client-secret test-refresh-token'}

        with self.assertRaises(RuntimeError) as error:
            self.message(connection).send()

        self.assertEqual(len(self.calls), 1)
        self.assertNotIn('test-client-secret', str(error.exception))
        self.assertNotIn('test-refresh-token', str(error.exception))

    def test_send_failure_is_not_automatically_retried_or_reported_as_success(self):
        self.send_status = 503

        with self.assertRaises(RuntimeError):
            self.message(self.connection()).send()

        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.message(self.connection(fail_silently=True)).send(), 0)
        self.assertEqual(len(self.calls), 4)

    def test_success_status_without_a_message_id_is_not_reported_as_sent(self):
        self.send_data = {}

        with self.assertRaises(RuntimeError):
            self.message(self.connection()).send()

        self.assertEqual(len(self.calls), 2)

    def test_network_error_does_not_expose_authorization_headers(self):
        connection = self.connection()
        with patch('requests.sessions.Session.send', side_effect=requests.Timeout('test-access-token')):
            with self.assertRaises(RuntimeError) as error:
                self.message(connection).send()
        self.assertNotIn('test-access-token', str(error.exception))

    def test_bcc_recipient_is_preserved_in_the_gmail_mime_envelope(self):
        message = self.message(self.connection(), bcc=['private@example.com'])

        self.assertEqual(message.send(), 1)

        raw = json.loads(self.calls[1][0].body)['raw']
        decoded = BytesParser(policy=policy.default).parsebytes(base64.urlsafe_b64decode(raw))
        self.assertEqual(decoded['Bcc'], 'private@example.com')
