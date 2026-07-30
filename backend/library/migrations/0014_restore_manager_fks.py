"""새 Manager/Member PK 기준으로 FK 를 복원한다."""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("library", "0013_drop_manager_fks"),
        ("manager", "0003_recreate_manager"),
        ("members", "0005_email_login"),
    ]

    operations = [
        migrations.AddField(
            model_name="book",
            name="registrar_manager",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="registered_books",
                to="manager.manager",
                verbose_name="최초 등록 관리자",
            ),
        ),
        migrations.AddField(
            model_name="book",
            name="modification_manager",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="modified_books",
                to="manager.manager",
                verbose_name="최종 수정 관리자",
            ),
        ),
        # 빈 테이블에 추가되므로 nullable 로 붙인 뒤 모델과 동일하게 NOT NULL 로 맞춘다.
        migrations.AddField(
            model_name="loan",
            name="member",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
                verbose_name="대출 회원",
            ),
        ),
        migrations.AlterField(
            model_name="loan",
            name="member",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
                verbose_name="대출 회원",
            ),
        ),
        migrations.AddField(
            model_name="loan",
            name="loan_manager",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="manager.manager",
                verbose_name="업무 처리 관리자",
            ),
        ),
        migrations.AddField(
            model_name="notice",
            name="manager",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="manager.manager",
                verbose_name="작성 관리자",
            ),
        ),
    ]
