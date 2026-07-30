from django.db import models
from members.models import Member
from django.utils import timezone
class Manager(models.Model):
    """
    관리자 역할 테이블 (MANAGER)
    회원(MEMBER)에게 관리자 권한을 부여하는 1:1 관계의 테이블
    """
    class ManagerType(models.TextChoices):
        LIBRARIAN = 'LIBRARIAN', '사서'
        ADMIN = 'ADMIN', '시스템 관리자'
        STAFF = 'STAFF', '일반 직원'

    member = models.OneToOneField(
        Member,
        on_delete=models.CASCADE,
        primary_key=True,
        verbose_name="관리자 회원",
        )
    manager_type = models.CharField(
        "관리자 유형", max_length=20, choices=ManagerType.choices, default=ManagerType.LIBRARIAN
        )
    manager_last_activity = models.DateTimeField(
        "관리자 권한 최종 사용 시각", default=timezone.now
        )
    join_date = models.DateTimeField(
        "관리자 역할 부여 시각", auto_now_add=True
        )    

    class Meta:
        db_table = "MANAGER"
        verbose_name = "관리자"
        verbose_name_plural = "관리자 목록"

    def __str__(self):
        return f"관리자: {self.member.name} 직책: {self.get_manager_type_display()}"
    
    def update_last_activity(self):
        self.manager_last_activity = timezone.now()
        self.save(update_fields=['manager_last_activity'])