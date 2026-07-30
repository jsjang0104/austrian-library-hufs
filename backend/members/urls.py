from django.urls import path
from .views import MemberViewSet, CustomTokenObtainPairView

urlpatterns = [
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('', MemberViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='member-list'),
    path('<int:sid>/', MemberViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='member-detail'),
]
