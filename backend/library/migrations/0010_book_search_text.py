from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("library", "0009_normalize_category_to_korean"),
    ]

    operations = [
        migrations.AddField(
            model_name="book",
            name="search_text",
            field=models.TextField(blank=True, null=True, verbose_name="LLM 생성 맥락 텍스트"),
        ),
    ]
