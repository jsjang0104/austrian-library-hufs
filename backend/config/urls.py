from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from members.views import CustomTokenObtainPairView, CustomTokenRefreshView, LogoutView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("manager/", include("manager.urls")),
    path("api/", include("library.urls")),
    path("api/members/", include("members.urls")),
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/logout/', LogoutView.as_view(), name='token_logout'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)