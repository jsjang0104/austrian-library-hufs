# Manual overdue reminders

The librarian selects loans in Django admin, chooses Korean or German, previews each recipient's subject and body, and explicitly confirms sending. This extends the already agreed manual preview/confirmation workflow. Each recipient receives a separate message containing only their selected overdue loans. Both templates use courteous language, offer contact about extension/return difficulties, and acknowledge returns not yet reflected in the records.

## Approach

Use an intermediate Django admin action page rather than separate language actions: the language and the actual messages are visible together before sending. Use Django's mail abstraction and a Gmail HTTPS backend with the existing requests dependency, because the confirmed Render Free hosting blocks SMTP. Unconfigured installations retain preview access but cannot send.

### Confirmed hosting and sender

The user confirmed the sender/reply address `deutsch@hufs.ac.kr` and corrected the hosting plan to Render Free. HUFS officially uses Google Workspace; Render Free blocks SMTP ports. Therefore use a Django email backend that calls Gmail API over HTTPS with a Google OAuth refresh token. Use the send-only `gmail.send` scope and a sender-specific Gmail API URL so credentials from a different account cannot silently send under the wrong identity. Keep sending disabled until the user completes Google authorization and enters credentials into Render environment variables. Keep SMTP available as an explicit alternative for other hosting environments.

## Constraints

- Use Asia/Seoul calendar dates: only unreturned loans due before today qualify; omit missing dates and invalid email addresses.
- Require loan change permission, CSRF, and a signed, expiring preview bound to the administrator, language, selected loans, sender, recipients, and rendered content. Changed previews must be confirmed again.
- Keep each recipient private. Record per-recipient attempts with unique request IDs to suppress repeated submission of the same confirmation, including failed attempts whose SMTP outcome may be uncertain.
- Report partial failures, record successful sends in loan history, and leave loan/book state unchanged.
- Carry large selections in the signed preview rather than expanding checkbox fields. Reuse one mail connection; stop starting recipients after a 10-second work budget, cap individual SMTP waits at 5 seconds, and report recipients not yet attempted.
- No scheduled sending or live test emails. Tests use the in-memory backend. SMTP credentials remain deployment environment variables.

## Builder decisions

Group only the selected eligible loans by member. Default the preview language to Korean. An administrator can start a new preview to intentionally send again. SMTP acceptance is recorded as sent; final inbox delivery cannot be guaranteed by the application.
