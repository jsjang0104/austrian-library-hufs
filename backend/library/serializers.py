from rest_framework import serializers
from .models import Book, Loan, Notice

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = '__all__'
        extra_kwargs = {
            'registrar_manager': {'write_only': True},
            'modification_manager': {'write_only': True},
        }

class LoanSerializer(serializers.ModelSerializer):
    book_title = serializers.ReadOnlyField(source='book.title')
    book_author = serializers.ReadOnlyField(source='book.author')
    overdue_days = serializers.IntegerField(read_only=True)

    class Meta:
        model = Loan
        fields = [
            'loan_id', 
            'member', 
            'book', 
            'book_title',   
            'book_author',  
            'loan_date', 
            'due_date', 
            'return_date', 
            'overdue_days'
        ]
        read_only_fields = fields

class CheckoutSerializer(serializers.Serializer):
    book_id = serializers.IntegerField(min_value=1, max_value=2147483647)


class SmartSearchSerializer(serializers.Serializer):
    q = serializers.CharField(max_length=500)


class NoticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notice
        fields = '__all__'
        extra_kwargs = {'manager': {'write_only': True}}
