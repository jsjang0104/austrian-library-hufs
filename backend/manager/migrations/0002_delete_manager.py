"""Manager 는 PK 자체가 Member 를 가리키는 FK 라서, Member PK 교체 전에 제거한다.

manager/0003 에서 member 필드로 재생성된다.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("manager", "0001_initial"),
        ("library", "0013_drop_manager_fks"),
    ]

    operations = [
        migrations.DeleteModel(name="Manager"),
    ]
