from rest_framework import permissions


class NoPermission(permissions.BasePermission):
    message = "You are not allowed to do this!"

    def has_permission(self, request, view):
        return False
