"""Member PK 교체(학번 → 자동 id)를 위해 Manager/Member 를 향한 FK 를 일시 제거한다.

이 체인(library 0013 → manager 0002 → members 0005 → manager 0003 → library 0014)은
빈 DB 에 순서대로 적용되는 것을 전제로 한다. 운영 반영 절차는 docs/migration_email_login.md 참고.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("library", "0012_load_translated_fields"),
    ]

    operations = [
        migrations.RemoveField(model_name="book", name="registrar_manager"),
        migrations.RemoveField(model_name="book", name="modification_manager"),
        migrations.RemoveField(model_name="loan", name="loan_manager"),
        migrations.RemoveField(model_name="loan", name="member"),
        migrations.RemoveField(model_name="notice", name="manager"),
    ]
