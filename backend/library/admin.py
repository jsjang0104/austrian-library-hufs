from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib import admin, messages
from django.core import signing
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.utils import timezone
from django.utils.html import format_html
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import Book, Loan, Notice, NoticeImage, OverdueReminderDelivery
from .forms import OverdueEmailForm
from .overdue_email import (
    PREVIEW_MAX_AGE, PREVIEW_SALT, build_overdue_reminders, mail_configuration_error,
    preview_payload, send_confirmed_reminders, sign_preview,
)

class BookResource(resources.ModelResource):
    class Meta:
        model = Book
        fields = (
            'call_number', 'title', 'author', 'status', 
            'language', 'location', 'category'
        )
        import_id_fields = ('call_number',)

class SearchTextFilter(admin.SimpleListFilter):
    title = "맥락 텍스트 유무"
    parameter_name = 'has_search_text'

    def lookups(self, request, model_admin):
        return (
            ('yes', '있음'),
            ('no', '없음'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.exclude(Q(search_text__isnull=True) | Q(search_text__exact=''))
        if self.value() == 'no':
            return queryset.filter(Q(search_text__isnull=True) | Q(search_text__exact=''))
        return queryset

@admin.register(Book)
class BookAdmin(ImportExportModelAdmin):
    resource_class = BookResource
    list_display = ('book_id', 'call_number', 'title', 'author', 'status', 'location', 'search_text_preview')
    search_fields = ('title', 'author', 'call_number')
    list_filter = ('status', 'language', 'category', SearchTextFilter)

    def search_text_preview(self, obj):
        if not obj.search_text:
            return "—"
        text = obj.search_text.strip()
        if not text:
            return "—"
        if len(text) > 40:
            return text[:40] + "..."
        return text
    search_text_preview.short_description = "맥락 텍스트"

@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ('loan_id', 'get_book_title', 'get_member_info', 'loan_date', 'due_date', 'return_date', 'is_overdue')
    search_fields = ('book__title', 'member__name', 'member__sid')
    list_filter = ('loan_date', 'return_date')
    readonly_fields = ('due_date', 'loan_date')
    autocomplete_fields = ('book', 'member')
    actions = ('extend_due_date', 'send_overdue_reminders')

    @admin.action(description="연체 안내 메일 발송 (언어 선택·미리보기)", permissions=['change'])
    def send_overdue_reminders(self, request, queryset):
        form = OverdueEmailForm({'language': request.POST.get('language', 'ko')})
        language = form.cleaned_data['language'] if form.is_valid() else 'ko'
        confirmed = None
        if form.is_valid() and ('confirmation_token' in request.POST or request.POST.get('confirm') == '1'):
            try:
                confirmed = signing.loads(
                    request.POST.get('confirmation_token', ''),
                    salt=PREVIEW_SALT, max_age=PREVIEW_MAX_AGE,
                )
                if confirmed['user_id'] != request.user.pk:
                    raise signing.BadSignature('Different administrator')
            except signing.BadSignature:
                self.message_user(
                    request, '미리보기가 만료되었거나 유효하지 않습니다. 내용을 다시 확인해 주세요.',
                    messages.WARNING,
                )
                return HttpResponseRedirect(request.get_full_path())
            # The signed selection avoids thousands of checkbox fields when the
            # librarian selects all records across multiple changelist pages.
            queryset = self.get_queryset(request).filter(pk__in=confirmed['selected_ids'])
        reminders, skipped_count = build_overdue_reminders(queryset, language)
        selected_ids = list(queryset.values_list('pk', flat=True))
        payload = preview_payload(request.user.pk, language, selected_ids, reminders)
        configuration_error = mail_configuration_error()
        if request.POST.get('confirm') == '1' and confirmed is not None:
            if any(confirmed.get(key) != value for key, value in payload.items()):
                self.message_user(
                    request, '미리보기를 갱신했습니다. 내용을 다시 확인해 주세요.', messages.WARNING,
                )
            elif not configuration_error and reminders:
                result = send_confirmed_reminders(
                    reminders, confirmed['batch_id'], language, request.user,
                )
                for loan in queryset.filter(pk__in=result['sent_loan_ids']):
                    self.log_change(request, loan, f'연체 안내 메일 발송 ({language})')
                if result['sent']:
                    self.message_user(
                        request, f"{result['sent']}명에게 연체 안내 메일을 발송했습니다.", messages.SUCCESS,
                    )
                if result['failed']:
                    self.message_user(
                        request,
                        f"{result['failed']}명의 메일 발송을 완료하지 못했습니다. "
                        '발송 기록과 메일 서비스에서 결과를 확인한 후 다시 진행해 주세요.',
                        messages.ERROR,
                    )
                if result['duplicate']:
                    self.message_user(
                        request,
                        f"이미 처리된 {result['duplicate']}명의 발송 요청은 건너뛰었습니다.",
                        messages.WARNING,
                    )
                if result['deferred']:
                    self.message_user(
                        request,
                        f"처리 시간 제한으로 {result['deferred']}명의 발송을 시작하지 못했습니다. "
                        '발송 기록을 확인하고 해당 회원을 다시 선택해 진행해 주세요.',
                        messages.WARNING,
                    )
                return HttpResponseRedirect(request.get_full_path())
        return TemplateResponse(request, 'admin/library/loan/overdue_email.html', {
            **self.admin_site.each_context(request),
            'title': '연체 안내 메일 — 언어 선택 및 미리보기',
            'opts': self.model._meta,
            'form': form,
            'language': language,
            'reminders': reminders,
            'skipped_count': skipped_count,
            'selected_ids': selected_ids,
            'sender': settings.DEFAULT_FROM_EMAIL,
            'reply_to': settings.LIBRARY_CONTACT_EMAIL,
            'confirmation_token': sign_preview(payload),
            'configuration_error': configuration_error,
            'can_send': not configuration_error,
        })

    @admin.action(description="반납기한연장 (기존 예정일 + 3개월)", permissions=['change'])
    def extend_due_date(self, request, queryset):
        extended = 0
        skipped = 0
        with transaction.atomic():
            for loan in queryset.select_for_update(of=('self',)):
                if loan.return_date is not None or loan.due_date is None:
                    skipped += 1
                    continue

                previous_due_date = timezone.localtime(loan.due_date)
                loan.due_date = previous_due_date + relativedelta(months=3)
                loan.save(update_fields=['due_date'])
                self.log_change(
                    request, loan,
                    f"반납 예정일 연장: {previous_due_date.isoformat()} → {loan.due_date.isoformat()}",
                )
                extended += 1

        if extended:
            self.message_user(request, f"{extended}건의 반납 예정일을 3개월 연장했습니다.", messages.SUCCESS)
        if skipped:
            self.message_user(
                request,
                f"반납이 완료되었거나 반납 예정일이 없는 {skipped}건은 건너뛰었습니다.",
                messages.WARNING,
            )

    def get_book_title(self, obj):
        return obj.book.title
    get_book_title.short_description = "도서명"

    def get_member_info(self, obj):
        return f"{obj.member.name} ({obj.member.get_role_display()})"
    get_member_info.short_description = "회원(신분)"

    def is_overdue(self, obj):
        return obj.overdue_days > 0
    is_overdue.boolean = True
    is_overdue.short_description = "연체"

class NoticeImageInline(admin.TabularInline):
    model = NoticeImage
    extra = 1
    fields = ('image', 'order', 'preview')
    readonly_fields = ('preview',)

    def preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:80px; border-radius:4px;" />', obj.image.url)
        return "-"
    preview.short_description = "미리보기"

@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ('notice_id', 'title', 'manager', 'post_date', 'view_count')
    search_fields = ('title', 'content')
    inlines = [NoticeImageInline]


@admin.register(OverdueReminderDelivery)
class OverdueReminderDeliveryAdmin(admin.ModelAdmin):
    list_display = ('recipient_email', 'language', 'status', 'sent_by', 'created_at', 'sent_at')
    list_filter = ('language', 'status', 'created_at')
    search_fields = ('recipient_email', 'member__name')
    readonly_fields = ('id', 'member', 'sent_by', 'recipient_email', 'language', 'status', 'created_at', 'sent_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
