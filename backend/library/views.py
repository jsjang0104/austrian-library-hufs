import logging

from django.db import transaction, models
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import APIException
from rest_framework.throttling import ScopedRateThrottle
from .models import Book, Loan, Notice
from .serializers import BookSerializer, LoanSerializer, NoticeSerializer, CheckoutSerializer, SmartSearchSerializer
from common.permissions import ReadOnlyOrStaff


logger = logging.getLogger(__name__)


class BookViewSet(viewsets.ModelViewSet):
    """
    도서 정보 관리를 위한 ViewSet
    """
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [ReadOnlyOrStaff]
    throttle_scope = None

    def _german_variant(self, keyword):
        return keyword.replace('ae', 'ä').replace('oe', 'ö').replace('ue', 'ü').replace('ss', 'ß')

    def _filter_by_keyword(self, queryset, keyword):
        """일반 검색: 원본 필드(제목/저자/청구기호 등) keyword 매칭 + 독일어 움라우트 변환"""
        if not keyword:
            return queryset
        g = self._german_variant(keyword)
        return queryset.filter(
            Q(title__icontains=keyword) |
            Q(title__icontains=g) |
            Q(author__icontains=keyword) |
            Q(author__icontains=g) |
            Q(call_number__icontains=keyword) |
            Q(language__icontains=keyword) |
            Q(category__icontains=keyword) |
            Q(location__icontains=keyword)
        )

    def _filter_by_translated_keyword(self, queryset, keyword):
        """AI 검색 전용: 번역 제목/저자 keyword 매칭"""
        if not keyword:
            return queryset
        return queryset.filter(
            Q(translated_title__icontains=keyword) |
            Q(translated_author__icontains=keyword)
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

    @action(
        detail=False, methods=['get'], url_path='smart_search',
        throttle_classes=[ScopedRateThrottle], throttle_scope='smart_search',
    )
    def smart_search(self, request):
        """
        하이브리드 검색: 키워드 매칭 결과를 우선으로 하고,
        벡터 유사도 검색 결과를 중복 제거 후 이어붙여 반환한다.
        language/category/status 필터는 기존 검색과 동일하게 적용된다.
        """
        search_input = SmartSearchSerializer(data=request.query_params)
        search_input.is_valid(raise_exception=True)
        query = search_input.validated_data['q']

        from . import search_service

        base_qs = self._apply_filters(Book.objects.all())

        # 1단계: 원본 필드 keyword
        direct_books = list(self._filter_by_keyword(base_qs, query))
        seen_ids = {b.book_id for b in direct_books}

        # 2단계: 번역 필드 keyword (1단계 결과 제외)
        translated_books = list(
            self._filter_by_translated_keyword(base_qs.exclude(book_id__in=seen_ids), query)
        )
        seen_ids.update(b.book_id for b in translated_books)

        # 3단계: 벡터 검색 (1·2단계 결과 제외)
        try:
            vector_ids = [
                book_id for book_id, _score in search_service.vector_search(query, top_k=30)
                if book_id not in seen_ids
            ]
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("vector_search 실패, 키워드 결과만 반환: %s", exc)
            vector_ids = []

        vector_book_map = base_qs.in_bulk(vector_ids)
        vector_books = [vector_book_map[bid] for bid in vector_ids if bid in vector_book_map]

        serializer = self.get_serializer(direct_books + translated_books + vector_books, many=True)
        return Response(serializer.data)

class LoanViewSet(viewsets.ReadOnlyModelViewSet):
    """회원 자신의 대출 조회와 검증된 대출/반납 액션만 허용한다."""

    queryset = Loan.objects.all()
    serializer_class = LoanSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            return Loan.objects.filter(member=user).select_related('book')
        return Loan.objects.none()

    @action(detail=False, methods=['post'], url_path='checkout')
    def checkout_book(self, request):
        checkout_input = CheckoutSerializer(data=request.data)
        checkout_input.is_valid(raise_exception=True)
        book_id = checkout_input.validated_data['book_id']

        try:
            with transaction.atomic():
                book = Book.objects.select_for_update().get(book_id=book_id)
                if book.status != Book.Status.AVAILABLE:
                    return Response({'error': '대출 가능한 도서가 아닙니다.'}, status=status.HTTP_400_BAD_REQUEST)
                loan = Loan.objects.create(book=book, member=request.user)
                return Response(self.get_serializer(loan).data, status=status.HTTP_201_CREATED)
        except Book.DoesNotExist:
            return Response({'error': '존재하지 않는 도서입니다.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            logger.exception('대출 처리 실패')
            return Response({'error': '대출 처리 중 오류가 발생했습니다.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='checkin')
    def checkin_book(self, request, pk=None):
        try:
            with transaction.atomic():
                # 잠금 이후 최신 반납 상태를 확인해 중복 반납 요청을 직렬화한다.
                loan = get_object_or_404(self.get_queryset().select_for_update(), pk=pk)
                self.check_object_permissions(request, loan)
                if loan.return_date is not None:
                    return Response({'error': '이미 반납 처리된 대출입니다.'}, status=status.HTTP_400_BAD_REQUEST)
                loan.book = Book.objects.select_for_update().get(pk=loan.book_id)
                loan.return_date = timezone.now()
                loan.save(update_fields=['return_date'])
                return Response(self.get_serializer(loan).data)
        except (Http404, APIException):
            raise
        except Exception:
            logger.exception('반납 처리 실패')
            return Response({'error': '반납 처리 중 오류가 발생했습니다.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NoticeViewSet(viewsets.ModelViewSet):
    """
    공지사항 정보 관리를 위한 ViewSet
    """
    queryset = Notice.objects.all()
    serializer_class = NoticeSerializer
    permission_classes = [ReadOnlyOrStaff]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        Notice.objects.filter(pk=instance.pk).update(view_count=models.F('view_count') + 1)
        instance.refresh_from_db()

        serializer = self.get_serializer(instance)
        return Response(serializer.data)