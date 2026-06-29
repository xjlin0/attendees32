import time
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import PermissionDenied

from attendees.persons.models import Attendee
from attendees.whereabouts.models import Place
from attendees.whereabouts.serializers import PlaceSerializer
from attendees.whereabouts.services.coordinates_service import CoordinatesService


class ApiDatagridDataPlaceViewSet(
    LoginRequiredMixin, ModelViewSet
):  # from GenericAPIView
    """
    API endpoint that allows Place to be viewed or edited in Attendee update page with HTTP_X_TARGET_ATTENDEE_ID.
    """

    serializer_class = PlaceSerializer

    def retrieve(self, request, *args, **kwargs):
        place_id = self.kwargs.get("pk")
        place = Place.objects.filter(
            pk=place_id, organization=request.user.organization
        ).first()
        serializer = PlaceSerializer(place)
        return Response(serializer.data)

    def get_queryset(
        self,
    ):  # Todo: check if current user are allowed to query this attendee's contact
        querying_place_id = self.kwargs.get("pk")
        return Place.objects.filter(
            pk=querying_place_id, organization=self.request.user.organization
        )

    def perform_update(self, serializer):
        target_attendee = get_object_or_404(
            Attendee, pk=self.request.META.get("HTTP_X_TARGET_ATTENDEE_ID")
        )
        if self.request.user.privileged_to_edit(target_attendee.id):  # checked same org
            instance = serializer.save()
            if instance.address and (instance.address.latitude is None or instance.address.longitude is None):
                CoordinatesService.geocode_address(instance.address.id)
            instance.subject.save(update_fields=['modified'])
            if instance.subject != target_attendee:
                target_attendee.save(update_fields=['modified'])
        else:
            time.sleep(2)
            raise PermissionDenied(
                detail=f"Not allowed to update {Place.__name__}"
            )

    def perform_create(self, serializer):  # privileged_to_edit also checking same org
        target_attendee = get_object_or_404(
            Attendee, pk=self.request.META.get("HTTP_X_TARGET_ATTENDEE_ID")
        )
        if self.request.user.privileged_to_edit(target_attendee.id):  # checked same org
            instance = serializer.save(organization=self.request.user.organization)
            if instance.address and (instance.address.latitude is None or instance.address.longitude is None):
                CoordinatesService.geocode_address(instance.address.id)
            instance.subject.save(update_fields=['modified'])
            if instance.subject != target_attendee:
                target_attendee.save(update_fields=['modified'])
        else:
            time.sleep(2)
            raise PermissionDenied(
                detail=f"Not allowed to create {Place.__name__}"
            )

    def perform_destroy(self, instance):
        target_attendee = get_object_or_404(
            Attendee, pk=self.request.META.get("HTTP_X_TARGET_ATTENDEE_ID")
        )
        if self.request.user.privileged_to_edit(target_attendee.id):  # checked same org
            subject = instance.subject
            instance.delete()
            subject.save(update_fields=['modified'])
            if subject != target_attendee:
                target_attendee.save(update_fields=['modified'])
        else:
            time.sleep(2)
            raise PermissionDenied(
                detail=f"Not allowed to delete {Place.__name__}"
            )


api_datagrid_data_place_viewset = ApiDatagridDataPlaceViewSet
