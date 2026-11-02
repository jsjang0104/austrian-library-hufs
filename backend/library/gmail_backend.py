"""Django email delivery through Gmail HTTPS, including on Render Free."""
import base64
from email.utils import parseaddr
from threading import RLock
from time import monotonic
from urllib.parse import quote

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import sanitize_address
import requests


class GmailApiError(RuntimeError):
    """A sanitized error: provider responses and credentials must not be logged."""


class GmailApiEmailBackend(BaseEmailBackend):
    def __init__(self, fail_silently=False, timeout=None, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.timeout = timeout if timeout is not None else settings.EMAIL_TIMEOUT
        self._lock = RLock()
        self._session = None
        self._access_token = None
        self._token_expires_at = 0

    def open(self):
        with self._lock:
            if self._session is not None:
                return False
            self._session = requests.Session()
            return True

    def close(self):
        with self._lock:
            if self._session is not None:
                self._session.close()
            self._session = None
            self._access_token = None
            self._token_expires_at = 0

    def _post_json(self, url, **kwargs):
        try:
            response = self._session.post(
                url, timeout=self.timeout, allow_redirects=False, **kwargs,
            )
        except requests.RequestException:
            raise GmailApiError('Gmail API connection failed; check the account connection.') from None
        if not 200 <= response.status_code < 300:
            if response.status_code == 401:
                self._access_token = None
            raise GmailApiError(f'Gmail API request failed (HTTP {response.status_code}).')
        try:
            data = response.json()
        except ValueError:
            raise GmailApiError('Gmail API returned an invalid response.') from None
        if not isinstance(data, dict):
            raise GmailApiError('Gmail API returned an invalid response.')
        return data

    def _get_access_token(self):
        if self._access_token and monotonic() < self._token_expires_at:
            return self._access_token
        if not all((settings.GMAIL_CLIENT_ID, settings.GMAIL_CLIENT_SECRET, settings.GMAIL_REFRESH_TOKEN)):
            raise ImproperlyConfigured('Google OAuth client credentials and a refresh token are required.')
        data = self._post_json('https://oauth2.googleapis.com/token', data={
            'client_id': settings.GMAIL_CLIENT_ID,
            'client_secret': settings.GMAIL_CLIENT_SECRET,
            'refresh_token': settings.GMAIL_REFRESH_TOKEN,
            'grant_type': 'refresh_token',
        })
        token = data.get('access_token')
        if not isinstance(token, str) or not token or any(char.isspace() for char in token):
            raise GmailApiError('Google authorization did not return a valid access token.')
        try:
            lifetime = float(data.get('expires_in', 3600))
        except (TypeError, ValueError):
            raise GmailApiError('Google authorization returned an invalid token lifetime.') from None
        self._access_token = token
        self._token_expires_at = monotonic() + max(0, lifetime - 30)
        return token

    def _send(self, message):
        sender = parseaddr(settings.DEFAULT_FROM_EMAIL)[1]
        if not sender or parseaddr(message.from_email)[1].casefold() != sender.casefold():
            raise GmailApiError('The message sender must match the configured library sender.')
        mime = message.message()
        # Gmail obtains recipients from MIME headers, unlike SMTP's separate
        # envelope. Include Bcc for Gmail to process and remove before delivery.
        if message.bcc:
            bcc = ', '.join(sanitize_address(address, message.encoding or settings.DEFAULT_CHARSET)
                            for address in message.bcc)
            if 'Bcc' in mime:
                mime.replace_header('Bcc', bcc)
            else:
                mime['Bcc'] = bcc
        raw = base64.urlsafe_b64encode(mime.as_bytes(linesep='\r\n')).decode('ascii')
        token = self._get_access_token()
        data = self._post_json(
            f'https://gmail.googleapis.com/gmail/v1/users/{quote(sender, safe="")}/messages/send',
            headers={'Authorization': f'Bearer {token}'}, json={'raw': raw},
        )
        if not isinstance(data.get('id'), str) or not data['id']:
            raise GmailApiError('Gmail API did not confirm message acceptance.')

    def send_messages(self, email_messages):
        messages = [message for message in (email_messages or []) if message.recipients()]
        if not messages:
            return 0
        with self._lock:
            opened_here = self.open()
            sent = 0
            try:
                for message in messages:
                    try:
                        self._send(message)
                    except (GmailApiError, ImproperlyConfigured, ValueError):
                        if not self.fail_silently:
                            raise
                    else:
                        sent += 1
            finally:
                if opened_here:
                    self.close()
            return sent
