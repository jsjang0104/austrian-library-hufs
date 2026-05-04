from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from members.views import CustomTokenObtainPairView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("manager/", include("manager.urls")),
    path("api/", include("library.urls")),
    path("api/members/", include("members.urls")),
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]