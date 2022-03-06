from django.db import transaction
from rest_framework.exceptions import APIException
from rest_framework.generics import GenericAPIView
from rest_framework.viewsets import ModelViewSet

from .models import Hedgehog
from .permissions import NoPermission
from .serializers import GroupSerializer, HedgehogSerializer


class HedgehogView(ModelViewSet):
    serializer_class = HedgehogSerializer
    queryset = Hedgehog.objects.all()


class NoPermissionView(ModelViewSet):
    serializer_class = HedgehogSerializer
    queryset = Hedgehog.objects.all()
    permission_classes = (NoPermission,)


class ExceptionView(GenericAPIView):
    def post(self, request, *args, **kwargs):
        """
        Sample view to raise unhandled exception.
        """
        exception_type: str = request.POST.get("type", "")

        if exception_type == "assertion_error":
            assert (
                1 == 0
            ), "Set a custom message and make sure it isn't leaked in the response."
        elif exception_type == "arithmetic_error":
            1 / 0
        elif exception_type == "key_error":
            sample_dict = {"a": 1}
            sample_dict["b"]
        elif exception_type == "api_error":
            raise APIException()
        elif exception_type == "nested_list_on_serializer":
            s = GroupSerializer()
            s.create({"hedgehogs": [{"id": 1}]})
        elif exception_type == "atomic_transaction":
            Hedgehog.objects.create(name="One")

            with transaction.atomic():
                Hedgehog.objects.create(name="Two")
                raise APIException()

        raise Exception("Shouldn't be included in the response.")
