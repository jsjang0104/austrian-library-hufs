from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager, PermissionsMixin
from django.db import transaction, IntegrityError
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class MemberManager(BaseUserManager):
    def create_user(self, sid, name, email, password=None, **extra_fields):
        if not sid:
            raise ValueError("학번을 입력해주세요.")
        
        if 'username' not in extra_fields:
            extra_fields['username'] = str(sid)
            
        if not password:
            password = None  # set_password(None) creates an unusable password.
            
        extra_fields.setdefault('is_active', True)
        
        try:
            with transaction.atomic():
                user = self.model(sid=sid, name=name, email=self.normalize_email(email), **extra_fields)
                user.set_password(password)
                user.save(using=self._db)
                return user
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise e

    def create_superuser(self, sid, name, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(sid, name, email, password, **extra_fields)

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


    sid = models.IntegerField("학번", primary_key=True, unique=True)
    name = models.CharField("실명 또는 닉네임", max_length=100)
    email = models.EmailField("이메일", max_length=100, unique=True)
    status = models.CharField("계정 상태", max_length=20, choices=Status.choices, default=Status.ACTIVE)
    role = models.CharField("신분", max_length=20, choices=Role.choices, default=Role.UNDERGRADUATE)
    
    member_last_activity = models.DateTimeField(auto_now=True)
    join_date = models.DateTimeField(auto_now_add=True)

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    USERNAME_FIELD = "sid"
    REQUIRED_FIELDS = ["name", "email"]

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = str(self.sid)
        super().save(*args, **kwargs)

    groups = models.ManyToManyField('auth.Group', related_name="member_groups", blank=True)
    user_permissions = models.ManyToManyField('auth.Permission', related_name="member_user_permissions", blank=True)

    class Meta:
        db_table = "MEMBER"
        ordering = ['sid']

    objects = MemberManager()

    def __str__(self):
        return f"{self.name}({self.sid})"