from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager, PermissionsMixin
import logging

logger = logging.getLogger(__name__)

class MemberManager(BaseUserManager):
    def create_user(self, email, name, password=None, **extra_fields):
        if not email:
            raise ValueError("이메일을 입력해주세요.")
        if not password:
            raise ValueError("비밀번호를 입력해주세요.")

        extra_fields.setdefault('is_active', True)

        user = self.model(email=self.normalize_email(email), name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, name, password, **extra_fields)

class Member(AbstractUser, PermissionsMixin):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "활성"
        DORMANT = "DORMANT", "휴면"
        WITHDRAWN = "WITHDRAWN", "탈퇴"
        SUSPENDED = "SUSPENDED", "정지"

    class Role(models.TextChoices):
        PROFESSOR = "PROFESSOR", "교수"
        GRADUATE = "GRADUATE", "대학원생"
        UNDERGRADUATE = "UNDERGRADUATE", "학부생/졸업생"

    # 로그인은 이메일로 하므로 AbstractUser 의 username 필드는 쓰지 않는다.
    username = None

    name = models.CharField("이름", max_length=100)
    email = models.EmailField("이메일", max_length=100, unique=True)
    status = models.CharField("계정 상태", max_length=20, choices=Status.choices, default=Status.ACTIVE)
    role = models.CharField("신분", max_length=20, choices=Role.choices, default=Role.UNDERGRADUATE)

    member_last_activity = models.DateTimeField(auto_now=True)
    join_date = models.DateTimeField(auto_now_add=True)

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    groups = models.ManyToManyField('auth.Group', related_name="member_groups", blank=True)
    user_permissions = models.ManyToManyField('auth.Permission', related_name="member_user_permissions", blank=True)

    class Meta:
        db_table = "MEMBER"
        ordering = ['id']

    objects = MemberManager()

    def __str__(self):
        return f"{self.name}({self.email})"
