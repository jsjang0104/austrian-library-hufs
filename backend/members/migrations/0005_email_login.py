"""학번(sid) PK 를 제거하고 자동 id PK + 이메일 로그인으로 전환한다.

groups / user_permissions 의 M2M 중간 테이블도 MEMBER.sid 를 참조하므로
PK 교체 전후로 제거했다가 다시 붙여 새 PK 기준으로 재생성한다.
username 은 USERNAME_FIELD 가 email 이 되면서 불필요해져 함께 제거한다.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("members", "0004_alter_member_options_member_username_and_more"),
        ("manager", "0002_delete_manager"),
    ]

    # django_admin_log 가 MEMBER 를 FK 로 참조하므로, admin 테이블이
    # 교체된 PK 기준으로 생성되도록 이 마이그레이션을 먼저 적용한다.
    run_before = [
        ("admin", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="member",
            options={"ordering": ["id"]},
        ),
        migrations.RemoveField(model_name="member", name="groups"),
        migrations.RemoveField(model_name="member", name="user_permissions"),
        migrations.RemoveField(model_name="member", name="username"),
        migrations.RemoveField(model_name="member", name="sid"),
        migrations.AddField(
            model_name="member",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="member",
            name="groups",
            field=models.ManyToManyField(
                blank=True, related_name="member_groups", to="auth.group"
            ),
        ),
        migrations.AddField(
            model_name="member",
            name="user_permissions",
            field=models.ManyToManyField(
                blank=True, related_name="member_user_permissions", to="auth.permission"
            ),
        ),
        migrations.AlterField(
            model_name="member",
            name="name",
            field=models.CharField(max_length=100, verbose_name="이름"),
        ),
    ]
