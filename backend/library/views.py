from django.db import transaction, models
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework import filters
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Book, Loan, Notice, Member
from .serializers import BookSerializer, LoanSerializer, NoticeSerializer


class BookViewSet(viewsets.ModelViewSet):
    """
    도서 정보 관리를 위한 ViewSet
    """
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    def _filter_by_keyword(self, queryset, keyword):
        """
        제목/저자 등에 대해 키워드를 매칭하되, 독일어 움라우트 변환
        (ae→ä, oe→ö, ue→ü, ss→ß)도 함께 시도하는 키워드 매칭 쿼리셋
        """
        if not keyword:
            return queryset

        german_keyword = keyword.replace('ae', 'ä')\
                                .replace('oe', 'ö')\
                                .replace('ue', 'ü')\
                                .replace('ss', 'ß')
        return queryset.filter(
            Q(title__icontains=keyword) |
            Q(title__icontains=german_keyword) |
            Q(author__icontains=keyword) |
            Q(author__icontains=german_keyword) |
            Q(language__icontains=keyword) |
            Q(call_number__icontains=keyword) |
            Q(category__icontains=keyword) |
            Q(location__icontains=keyword)
        )

    def _apply_filters(self, queryset):
        """언어/분야/상태 필터 (search/smart_search 공통)"""
        language_filter = self.request.query_params.get("language")
        if language_filter:
            queryset = queryset.filter(language=language_filter)

        category_filter = self.request.query_params.get("category")
        if category_filter:
            queryset = queryset.filter(category=category_filter)

        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    def get_queryset(self):
        """
        검색어에 독일어 움라우트 변환 기능을 추가한 커스텀 쿼리셋
        """
        queryset = super().get_queryset()
        search_keyword = self.request.query_params.get("search", "")
        queryset = self._filter_by_keyword(queryset, search_keyword)
        queryset = self._apply_filters(queryset)
        return queryset

    @action(detail=False, methods=['get'], url_path='smart_search')
    def smart_search(self, request):
        """
        하이브리드 검색: 키워드 매칭 결과를 우선으로 하고,
        벡터 유사도 검색 결과를 중복 제거 후 이어붙여 반환한다.
        language/category/status 필터는 기존 검색과 동일하게 적용된다.
        """
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response({'error': '검색어(q)를 입력해주세요.'}, status=status.HTTP_400_BAD_REQUEST)

        from . import search_service

        base_qs = self._apply_filters(Book.objects.all())

        keyword_books = list(self._filter_by_keyword(base_qs, query))
        seen_ids = {book.book_id for book in keyword_books}

        vector_ids = [
            book_id for book_id, _score in search_service.vector_search(query, top_k=20)
            if book_id not in seen_ids
        ]
        vector_book_map = base_qs.in_bulk(vector_ids)
        vector_books = [vector_book_map[book_id] for book_id in vector_ids if book_id in vector_book_map]

        serializer = self.get_serializer(keyword_books + vector_books, many=True)
        return Response(serializer.data)

class LoanViewSet(viewsets.ModelViewSet):
    """
    대출 기록 관리를 위한 ViewSet.
    대출(checkout) 및 반납(checkin) 액션을 포함합니다.
    """
    queryset = Loan.objects.all()
    serializer_class = LoanSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            return Loan.objects.filter(member=user)
        return Loan.objects.none()
    @action(detail=False, methods=['post'], url_path='checkout')
    def checkout_book(self, request):
        book_id = request.data.get('book_id')
        member = request.user

        if not book_id:
            return Response({'error': '책의 QR코드를 스캔해주세요.'}, status=status.HTTP_400_BAD_REQUEST)

        if not member.is_authenticated:
            return Response({'error': '로그인이 필요합니다.'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            with transaction.atomic():
                book = Book.objects.select_for_update().get(book_id=book_id)

                if book.status == Book.Status.ON_LOAN:
                    return Response({'error': '이미 대출 중인 도서입니다.'}, status=status.HTTP_400_BAD_REQUEST)

                book.status = Book.Status.ON_LOAN
                book.save()
                due_date = timezone.now() + timedelta(days=14)
                loan = Loan.objects.create(
                    book=book,
                    member=member,
                    due_date=due_date
                )
                serializer = self.get_serializer(loan)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Book.DoesNotExist:
            return Response({'error': '존재하지 않는 도서입니다.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': f'대출 처리 중 오류가 발생했습니다: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='checkin')
    def checkin_book(self, request, pk=None):
        try:
            with transaction.atomic():
                loan = self.get_object()

                if loan.return_date is not None:
                    return Response({'error': '이미 반납 처리된 대출입니다.'}, status=status.HTTP_400_BAD_REQUEST)
                book = loan.book
                book.status = Book.Status.AVAILABLE
                book.save()
                loan.return_date = timezone.now()

                loan.save()

                serializer = self.get_serializer(loan)
                return Response(serializer.data, status=status.HTTP_200_OK)

        except Loan.DoesNotExist:
            return Response({'error': '존재하지 않는 대출 기록입니다.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': f'반납 처리 중 오류가 발생했습니다: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NoticeViewSet(viewsets.ModelViewSet):
    """
    공지사항 정보 관리를 위한 ViewSet
    """
    queryset = Notice.objects.all()
    serializer_class = NoticeSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        Notice.objects.filter(pk=instance.pk).update(view_count=models.F('view_count') + 1)
        instance.refresh_from_db()

        serializer = self.get_serializer(instance)
        return Response(serializer.data)