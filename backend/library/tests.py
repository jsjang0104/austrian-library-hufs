from django.test import TestCase
from django.utils import timezone
from library.models import Book
from manager.models import Manager
from members.models import Member
from library.models import Loan
from library.test_utils import IsolatedSearchIndexMixin

class BookModelTest(IsolatedSearchIndexMixin, TestCase):
    def setUp(self):
        """Test case setup"""
        super().setUp()
        self.member = Member.objects.create_user(
            sid=20210001,
            name='Test Member',
            email='testmember@example.com',
            password='password123'
        )

        self.manager = Manager.objects.create(
            manager_sid=self.member,
            manager_type=Manager.ManagerType.LIBRARIAN
        )

        self.book = Book.objects.create(
            call_number='TS123.45 .B67 2025',
            title='Test Book Title',
            author='Test Author',
            status=Book.Status.AVAILABLE,
            registrar_manager=self.manager,
        )

    def test_book_creation(self):
        """Test if a Book instance is created successfully."""
        self.assertIsInstance(self.book, Book)
        self.assertEqual(self.book.title, 'Test Book Title')
        self.assertEqual(self.book.author, 'Test Author')
        self.assertEqual(self.book.status, 'AVAILABLE')
        self.assertEqual(self.book.registrar_manager, self.manager)

    def test_book_str_method(self):
        """Test the __str__ method of the Book model."""
        expected_str = f"{self.book.title} ({self.book.call_number})"
        self.assertEqual(str(self.book), expected_str)

    def test_update_modi_date(self):
        """Book.save()가 기존 도서의 modification_date를 갱신하는지 확인한다."""
        self.assertIsNone(self.book.modification_date)
        self.book.title = "Updated Test Book Title"
        self.book.save()

        updated_book = Book.objects.get(pk=self.book.pk)

        self.assertIsNotNone(updated_book.modification_date)

class LoanModelTest(IsolatedSearchIndexMixin, TestCase):
    def setUp(self):
        """Test case setup"""
        super().setUp()
        self.member = Member.objects.create_user(
            sid=20210002,
            name='Loan Test Member',
            email='loanmember@example.com',
            password='password123'
        )
        self.manager = Manager.objects.create(
            manager_sid = self.member,
            manager_type = Manager.ManagerType.LIBRARIAN,
        )
        self.book = Book.objects.create(
            call_number='TS123.45 .L67 2025',
            title='Loan Test Book Title',
            author='Loan Test Author',
            status=Book.Status.AVAILABLE,
            registrar_manager=self.manager,
        )
        self.loan = Loan.objects.create(
            member=self.member,
            book=self.book,
            due_date = timezone.now() + timezone.timedelta(days=14),
            loan_manager = self.manager,
        )

    def test_loan_creation(self):
        self.assertIsInstance(self.loan, Loan)
        self.assertEqual(self.loan.member, self.member)
        self.assertEqual(self.loan.book, self.book)
        self.assertEqual(self.loan.loan_manager, self.manager)
        self.assertIsNone(self.loan.return_date)

    def test_overdue_days_property_not_overdue(self):
        self.assertEqual(self.loan.overdue_days, 0)

    def test_overdue_days_property_overdue(self):
        self.loan.due_date = timezone.now() - timezone.timedelta(days = 7)
        self.loan.save()
        self.assertEqual(self.loan.overdue_days, 7)
    
    def test_overdue_days_property_returned_on_time(self):
        self.loan.due_date = timezone.now() - timezone.timedelta(days = 5)
        self.loan.return_date = timezone.now()
        self.loan.save()
        self.assertEqual(self.loan.overdue_days, 5)
