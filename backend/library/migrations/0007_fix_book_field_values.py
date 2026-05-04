from django.db import migrations


CATEGORY_FIX = {
    '문학': 'Literatur',
    '어학': 'Sprachwissenschaft',
    '역사': 'Geschichte',
    '사회과학': 'Sozialwissenschaften',
    'Sozial과학': 'Sozialwissenschaften',
    '기타': 'Sonstiges',
}

STATUS_FIX = {
    '대출 가능': 'AVAILABLE',
    'available': 'AVAILABLE',
    'loaned': 'ON_LOAN',
}


def fix_book_field_values(apps, schema_editor):
    Book = apps.get_model('library', 'Book')
    for old, new in CATEGORY_FIX.items():
        Book.objects.filter(category=old).update(category=new)
    for old, new in STATUS_FIX.items():
        Book.objects.filter(status=old).update(status=new)


class Migration(migrations.Migration):

    dependencies = [
        ('library', '0006_alter_loan_due_date'),
    ]

    operations = [
        migrations.RunPython(fix_book_field_values, migrations.RunPython.noop),
    ]
