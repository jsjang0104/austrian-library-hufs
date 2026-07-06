from django.db import models
from django.core.validators import RegexValidator
from members.models import Member
from manager.models import Manager
from django.utils import timezone
from datetime import timedelta 

# -----------------------------------------------------------------------------
# BOOK (물리적 도서)
# -----------------------------------------------------------------------------
class Book(models.Model):
    """
    물리적 도서 테이블 (BOOK)
    """
    class Status(models.TextChoices):
        AVAILABLE = 'AVAILABLE', '대출 가능'
        ON_LOAN = 'ON_LOAN', '대출 중'
        LOST = 'LOST', '분실'

    class Category(models.TextChoices):
        LITERATUR = 'Literatur', '문학'
        SPRACHWISSENSCHAFT = 'Sprachwissenschaft', '어학'
        GESCHICHTE = 'Geschichte', '역사'
        SOZIALWISSENSCHAFTEN = 'Sozialwissenschaften', '사회과학'
        SONSTIGES = 'Sonstiges', '기타'

    class Language(models.TextChoices):
        KOREAN = 'KR', '한국어'
        GERMAN = 'DE', '독일어'
        ENGLISH = 'EN', '영어'
        OTHER = 'ETC', '기타'

    book_id = models.AutoField("도서 고유 ID (바코드)", primary_key=True)
    call_number = models.CharField("고유 청구기호", max_length=50, unique=True)
    title = models.CharField("도서 제목", max_length=255)
    author = models.CharField("저자", max_length=255, null=True, blank=True)
    status = models.CharField(
        "현재 상태", max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    language = models.CharField(
        "언어", max_length=5, choices=Language.choices, default=Language.GERMAN
    )
    
    location_validator = RegexValidator(
        regex=r'^[A-D]\d+-\d+$',
        message="도서 위치는 'A~D(숫자)-(숫자)' 형식이어야 합니다. (예: A1-4)"
    )
    location = models.CharField(
        "도서 위치", 
        max_length=10, 
        validators=[location_validator],
        null=True, blank=True,
        help_text="도서 위치 형식: A~D(숫자)-(숫자) (예: A1-4)"
    )
    
    category = models.CharField(
        "분야", max_length=20, choices=Category.choices, default=Category.SONSTIGES
    )
    search_text = models.TextField("LLM 생성 맥락 텍스트", null=True, blank=True)
    translated_title = models.TextField("제목 번역", null=True, blank=True)
    translated_author = models.CharField("저자 번역", max_length=255, null=True, blank=True)

    registrar_manager = models.ForeignKey(
        Manager, on_delete=models.SET_NULL, null=True, verbose_name="최초 등록 관리자", related_name="registered_books"
    )
    registration_date = models.DateTimeField("최초 등록 시각", auto_now_add=True)
    
    modification_manager = models.ForeignKey(
        Manager, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="최종 수정 관리자", related_name="modified_books"
    )
    modification_date = models.DateTimeField("최종 수정 시각", null=True, blank=True)

    class Meta:
        db_table = 'BOOK'
        verbose_name = '도서'
        verbose_name_plural = '도서 목록'
        ordering = ['title', 'call_number']

    def __str__(self):
        return f"{self.title} ({self.call_number})"

    def save(self, *args, **kwargs):
        if self.pk:
            self.modification_date = timezone.now()
        super(Book, self).save(*args, **kwargs)

# -----------------------------------------------------------------------------
# LOAN (대출 기록 트랜잭션)
# -----------------------------------------------------------------------------
class Loan(models.Model):
    """
    대출 기록 트랜잭션 테이블 (LOAN)
    """
    loan_id = models.AutoField("대출 트랜잭션 고유 ID", primary_key=True)
    member = models.ForeignKey(Member, on_delete=models.CASCADE, verbose_name="대출 회원")
    book = models.ForeignKey(Book, on_delete=models.PROTECT, verbose_name="대출 도서")
    
    loan_date = models.DateTimeField("대출 시작 시각", auto_now_add=True)
    due_date = models.DateTimeField("반납 예정일", blank=True, null=True)
    return_date = models.DateTimeField("실제 반납 완료 시각", null=True, blank=True)
    
    loan_manager = models.ForeignKey(
        Manager, on_delete=models.SET_NULL, null=True, verbose_name="업무 처리 관리자")
    
    @property
    def overdue_days(self):
        if self.return_date:
            if self.return_date.date() > self.due_date.date():
                return (self.return_date.date() - self.due_date.date()).days
            return 0
        else:
            if self.due_date and timezone.now().date() > self.due_date.date():
                return (timezone.now().date() - self.due_date.date()).days
            return 0

    class Meta:
        db_table = 'LOAN'
        verbose_name = '대출 기록'
        verbose_name_plural = '대출 기록 목록'
        ordering = ['-loan_date']

    def __str__(self):
        return f"대출 ID {self.loan_id} ({self.member.sid} -> {self.book.title})"

    def save(self, *args, **kwargs):
        if not self.pk:
            if self.member.role == Member.Role.PROFESSOR:
                days = 90
            elif self.member.role == Member.Role.GRADUATE:
                days = 30
            else:
                days = 14
        
            self.due_date = timezone.now() + timedelta(days=days)
            self.book.status = Book.Status.ON_LOAN
            self.book.save()

        if self.return_date:
            self.book.status = Book.Status.AVAILABLE
            self.book.save()

        super().save(*args, **kwargs)

# -----------------------------------------------------------------------------
# NOTICE (공지사항)
# -----------------------------------------------------------------------------
class Notice(models.Model):
    notice_id = models.AutoField("공지사항 고유 ID", primary_key=True)
    manager = models.ForeignKey(
        Manager, on_delete=models.SET_NULL, null=True, verbose_name="작성 관리자"
    )
    title = models.CharField("게시글 제목", max_length=255)
    content = models.TextField("게시글 본문 내용")
    post_date = models.DateTimeField("게시글 최초 작성일", auto_now_add=True)
    view_count = models.IntegerField("조회수", default=0)

    class Meta:
        db_table = 'NOTICE'
        verbose_name = '공지사항'
        verbose_name_plural = '공지사항 목록'
        ordering = ['-post_date'] 

    def __str__(self):
        return self.title


# -----------------------------------------------------------------------------
# NOTICE IMAGE (공지사항 첨부 이미지)
# -----------------------------------------------------------------------------
class NoticeImage(models.Model):
    notice = models.ForeignKey(
        Notice, on_delete=models.CASCADE, related_name='images', verbose_name="공지사항"
    )
    image = models.ImageField("이미지", upload_to='notice_images/')
    order = models.PositiveSmallIntegerField("순서", default=0)

    class Meta:
        db_table = 'NOTICE_IMAGE'
        verbose_name = '공지 이미지'
        verbose_name_plural = '공지 이미지 목록'
        ordering = ['order']

    def __str__(self):
        return f"{self.notice.title} - 이미지 {self.order}"