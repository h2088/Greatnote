from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsNotebookOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class IsPageOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.notebook.user == request.user


class CanAccessPage(BasePermission):
    def has_object_permission(self, request, view, obj):
        if obj.notebook.user == request.user:
            return True
        if request.method in SAFE_METHODS:
            return obj.user_shares.filter(user=request.user).exists()
        return False
