from rest_framework import permissions


class ReadOnlyOrStaff(permissions.BasePermission):
    """조회는 비로그인 포함 누구나, 생성/수정/삭제는 스태프만.

    도서 목록·공지처럼 로그인 없이 열람해야 하지만 쓰기는 사서만 해야 하는
    엔드포인트에 쓴다.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)


class CreateOnlyOrStaff(permissions.BasePermission):
    """가입(POST)은 누구나, 그 밖의 회원 정보 접근은 스태프만.

    회원 목록/상세는 학번·실명·이메일이 담기므로 비로그인은 물론
    일반 로그인 사용자에게도 열지 않는다.
    """

    def has_permission(self, request, view):
        if request.method == "POST":
            return True
        return bool(request.user and request.user.is_staff)
