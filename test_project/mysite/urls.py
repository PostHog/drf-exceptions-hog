from django.urls import path

from ..test_app.views import ExceptionView, HedgehogView, NoPermissionView

urlpatterns = [
    path("hedgehogs", HedgehogView.as_view({"post": "create"})),
    path("hedgehogs/<int:pk>", HedgehogView.as_view({"get": "retrieve"})),
    path("denied", NoPermissionView.as_view({"get": "list"})),
    path("exception", ExceptionView.as_view()),
]
