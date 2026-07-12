from django.contrib import admin
from django.db.models import Q
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