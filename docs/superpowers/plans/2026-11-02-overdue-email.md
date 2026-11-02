# Manual Overdue Email Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Add courteous Korean/German manual reminders with language selection and explicit preview confirmation.

**Architecture:** A loan admin action builds grouped messages using text templates. Signed previews bind confirmation to visible content; persistent delivery records prevent repeated submissions. SMTP is configured through environment variables and defaults to disabled.

**Tech Stack:** Django 5.2, Django forms/templates/mail/signing, existing database.

**Spec:** `docs/superpowers/specs/2026-11-02-overdue-email-design.md`

## Global Constraints

Use Asia/Seoul calendar dates, separate messages per recipient, loan change permission, CSRF, and explicit confirmation. No scheduled or live test sending. Preserve the pre-existing deletion of `backend/.env.example` outside this change.

## Review Focus

- Returned, extended, undated, today-due, and invalid-address loans must never receive stale reminders.
- Language, recipient, administrator, sender, or content changes invalidate confirmation.
- Repeated confirmation must not send another copy; partial failures must remain visible.
- HTML-looking names/titles must display safely and remain literal in plain text mail.
- Missing SMTP settings must allow preview without attempting network delivery.

## Task 1: Preview and templates

Files: `backend/library/overdue_email.py`, `backend/library/forms.py`, `backend/library/admin.py`, `backend/library/templates/library/emails/overdue_{ko,de}.txt`, `backend/library/templates/admin/library/loan/overdue_email.html`, `backend/library/test_overdue_email.py`.

- [x] Write and run failing integration tests for permission, eligibility, grouping, language choice, and preview without sending.
- [x] Implement `build_overdue_reminders(queryset, language)` returning rendered recipient messages plus skipped count; integrate a ChoiceField form and admin preview page.
- [x] Verify tests pass for real admin POSTs, Seoul date boundaries, and escaped previews.

## Task 2: Confirmed delivery and operations

Files: same admin/service/tests, `backend/library/models.py`, new schema migration, `backend/config/settings.py`, `docs/management/overdue-email.md`.

- [x] Write and run failing tests for explicit confirmation, changed/invalid previews, sender configuration, private delivery, repeat suppression, partial failure, and unchanged loan state.
- [x] Implement signed 30-minute previews and per-recipient delivery records. Persist the claim before SMTP and do not retry the same confirmation automatically.
- [x] Add environment configuration, sender/reply-to headers, and courteous bilingual templates; document manual use and mail examples.
- [x] Run `manage.py test --settings=config.test_settings --noinput`, Django checks, and migration consistency checks; review the final diff independently.

Independent review identified excessive POST fields for large selections and unbounded sequential SMTP work. Both were reproduced by failing integration tests and fixed using signed selection restoration, connection reuse, and a time budget with explicit unattempted counts. Final backend suite: 61/61 passed; Django checks and migration consistency checks passed.

Delivery: commit only this change and push the current branch as authorized by the original request; report remote confirmation in the conversation. Live sender setup remains pending the user's account/service information.
