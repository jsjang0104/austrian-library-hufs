"""Manager 를 새 Member PK(id) 기준으로 재생성한다."""
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("manager", "0002_delete_manager"),
        ("members", "0005_email_login"),
    ]

    operations = [
        migrations.CreateModel(
            name="Manager",
            fields=[
                (
                    "member",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        serialize=False,
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="관리자 회원",
                    ),
                ),
                (
                    "manager_type",
                    models.CharField(
                        choices=[
                            ("LIBRARIAN", "사서"),
                            ("ADMIN", "시스템 관리자"),
                            ("STAFF", "일반 직원"),
                        ],
                        default="LIBRARIAN",
                        max_length=20,
                        verbose_name="관리자 유형",
                    ),
                ),
                (
                    "manager_last_activity",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                        verbose_name="관리자 권한 최종 사용 시각",
                    ),
                ),
                (
                    "join_date",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="관리자 역할 부여 시각"
                    ),
                ),
            ],
            options={
                "verbose_name": "관리자",
                "verbose_name_plural": "관리자 목록",
                "db_table": "MANAGER",
            },
        ),
    ]
