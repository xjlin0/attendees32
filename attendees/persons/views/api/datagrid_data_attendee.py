import time

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.postgres.aggregates.general import JSONBAgg
from django.db.models import Func, Value
from django.db.models.expressions import F
from django.db.models.functions import Concat, Trim
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from rest_framework.viewsets import ModelViewSet

from attendees.occasions.models import Gathering, Meet
from attendees.persons.models import (  # , Relationship
    Attendee,
    Folk,
    FolkAttendee,
    Relation,
)
from attendees.persons.serializers import AttendeeMinimalSerializer
from attendees.persons.services import AttendeeService, AttendingMeetService


class ApiDatagridDataAttendeeViewSet(
    LoginRequiredMixin, ModelViewSet
):  # from GenericAPIView
    """
    API endpoint that allows single attendee to be viewed or edited.
    """

    serializer_class = AttendeeMinimalSerializer
    # queryset = Attendee.objects.all()

    # def retrieve(self, request, *args, **kwargs):
    #     attendee_id = self.kwargs.get('pk')
    #     attendee =  Attendee.objects.annotate(
    #                 attendingmeets=JSONBAgg(
    #                     Func(
    #                         Value('attendingmeet_id'), 'attendings__attendingmeet__id',
    #                         Value('attending_finish'), 'attendings__attendingmeet__finish',
    #                         Value('attending_start'), 'attendings__attendingmeet__start',
    #                         Value('meet_name'), 'attendings__meets__display_name',
    #                         function='jsonb_build_object'
    #                     ),
    #                 ),
    #                 # contacts=ArrayAgg('attendings__meets__slug', distinct=True),
    #            ).filter(pk=attendee_id)
    #     serializer = AttendeeMinimalSerializer(attendee)
    #     return Response(serializer.data)

    def get_queryset(self):
        """
        attendingmeets annotation is used by datagrid_assembly_data_attendees.js & datagrid_attendee_update_view.js

        Todo 20210704 rewrite following in DRF nested serializer to avoid manual screening of is_removed
        :return:
        """
        current_user = (
            self.request.user
        )  # Todo: guard this API so only admin or scheduler can call it.
        querying_attendee_id = self.kwargs.get("pk")
        querying_term = self.request.query_params.get("searchValue")

        if querying_attendee_id:
            qs = Attendee.objects.annotate(
                organization_slug=F("division__organization__slug"),
                attendingmeets=JSONBAgg(
                    Func(
                        Value("attending_id"),
                        "attendings__id",
                        Value("attending_is_removed"),
                        "attendings__is_removed",
                        Value("registration_assembly"),
                        "attendings__registration__assembly__display_name",
                        Value("registrant"),
                        Trim(
                            Concat(
                                Trim(
                                    Concat(
                                        "attendings__registration__registrant__first_name",
                                        Value(" "),
                                        "attendings__registration__registrant__last_name",
                                    )
                                ),
                                Value(" "),
                                Trim(
                                    Concat(
                                        "attendings__registration__registrant__last_name2",
                                        "attendings__registration__registrant__first_name2",
                                    )
                                ),
                            )
                        ),
                        function="jsonb_build_object",
                    ),
                ),
                # contacts=ArrayAgg('attendings__meets__slug', distinct=True),
            ).filter(
                division__organization=current_user.organization,
                pk=querying_attendee_id,
            )
        elif querying_term:
            qs = Attendee.objects.filter(
                infos__icontains=querying_term,
            )

        return qs.filter(division__organization=current_user.organization)

    def perform_create(self, serializer):
        """
        Some post processing can be added for a new attendee just created.  Gathering_id is higher priority than meet.
        """
        instance = serializer.save()
        folk_id = self.request.META.get("HTTP_X_ADD_FOLK")
        role_id = self.request.META.get("HTTP_X_FAMILY_ROLE")
        meet_id = self.request.META.get("HTTP_X_JOIN_MEET")
        gathering_id = self.request.META.get("HTTP_X_JOIN_GATHERING")

        meet = Meet.objects.filter(pk=meet_id).first()

        if folk_id and role_id:
            FolkAttendee.objects.create(
                folk=get_object_or_404(Folk, pk=folk_id),
                attendee=instance,
                role=get_object_or_404(Relation, pk=role_id),
            )

        if gathering_id:
            gathering = get_object_or_404(Gathering, pk=gathering_id)
            attendee_to_attendingmeets_cache = AttendingMeetService.flip_attendingmeet_by_existing_attending(self.request.user, [instance], gathering.meet.id, True)
            # AttendanceService.join_attendance([instance], gathering, attendee_to_attendingmeets_cache)
        elif meet and meet.assembly.division.organization == self.request.user.organization:
            AttendingMeetService.flip_attendingmeet_by_existing_attending(self.request.user, [instance], meet_id, True)

    def perform_update(self, serializer):
        target_attendee = get_object_or_404(
            Attendee, pk=self.request.META.get("HTTP_X_TARGET_ATTENDEE_ID")
        )
        if self.request.user.privileged_to_edit(
            target_attendee.id
        ):  # intentionally forbid user delete him/herself
            instance = serializer.save()
            if self.request.META.get("HTTP_X_END_ALL_ATTENDEE_ACTIVITIES"):  # passed away
                AttendeeService.end_all_activities(instance, self.request.user.attendee_uuid_str())

            if self.request.META.get("HTTP_X_ADD_PAST"):
                AttendeeService.add_past(instance, self.request.META.get("HTTP_X_ADD_PAST"))

        else:
            time.sleep(2)
            raise PermissionDenied(
                detail=f"Not allowed to update {target_attendee.__class__.__name__}"
            )

    def perform_destroy(self, instance):
        target_attendee = get_object_or_404(
            Attendee, pk=self.request.META.get("HTTP_X_TARGET_ATTENDEE_ID")
        )
        if self.request.user.privileged_to_edit(
            target_attendee.id
        ):  # intentionally forbid user delete him/herself
            AttendeeService.destroy_with_associations(instance)
        else:
            time.sleep(2)
            raise PermissionDenied(
                detail=f"Not allowed to delete {instance.__class__.__name__}"
            )


api_datagrid_data_attendee_viewset = ApiDatagridDataAttendeeViewSet
