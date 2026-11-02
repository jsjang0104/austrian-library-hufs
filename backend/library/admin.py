from dateutil.relativedelta import relativedelta
from django.contrib import admin, messages
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.html import format_html
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import Book, Loan, Notice, NoticeImage

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
    actions = ('extend_due_date',)

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
