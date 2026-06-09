from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("library", "0010_book_search_text"),
    ]

    operations = [
        migrations.AddField(
            model_name="book",
            name="translated_title",
            field=models.TextField(blank=True, null=True, verbose_name="제목 번역"),
        ),
        migrations.AddField(
            model_name="book",
            name="translated_author",
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name="저자 번역"),
        ),
    ]
