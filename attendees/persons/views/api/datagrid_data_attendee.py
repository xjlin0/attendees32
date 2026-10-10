import time, pytz
from django.conf import settings
from django.contrib.postgres.aggregates.general import JSONBAgg
from django.db.models import Func, Value
from django.db.models.expressions import F
from django.db.models.functions import Concat, Trim
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from urllib import parse
import logging

logger = logging.getLogger(__name__)

from attendees.occasions.models import Gathering, Meet
from attendees.persons.models import (  # , Relationship
    Attendee,
    Folk,
    FolkAttendee,
    Relation,
)
from attendees.persons.serializers import AttendeeMinimalSerializer
from attendees.persons.services import (
    AttendeeMergeService,
    AttendeeService,
    AttendingMeetService,
    MergeRefused,
)


class AttendeeMergedAway(APIException):
    """410 with ``merged_into``: the record lives on under another id."""

    status_code = status.HTTP_410_GONE
    default_code = "merged_away"

    def __init__(self, merged_into):
        super().__init__(
            {
                "detail": "That attendee was merged into another record.",
                "merged_into": str(merged_into),
            }
        )


class AttendeeGone(APIException):
    """410 without a forwarding address: merged, and the primary is gone."""

    status_code = status.HTTP_410_GONE
    default_code = "gone"
    default_detail = "That attendee is gone, and no record holds them now."


class ApiDatagridDataAttendeeViewSet(ModelViewSet):  # from GenericAPIView
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

    def retrieve(self, request, *args, **kwargs):
        """A merge tombstone answers 410; everything else, a plain deletion
        included, is served as before."""
        held = Attendee.all_objects.filter(
            pk=self.kwargs.get("pk"),
            division__organization=request.user.organization,
        ).first()
        if (
            held is not None
            and held.is_removed
            and held.merged_into_id is not None
        ):
            primary = AttendeeMergeService.primary_of(held)
            if primary is None or primary.is_removed:
                raise AttendeeGone()
            raise AttendeeMergedAway(primary.pk)

        return super().retrieve(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="merge")
    def merge(self, request, pk=None):
        """``POST .../<duplicate>/merge/`` with ``{"primary": "<uuid>", "keep": {...}}``.

        Posted to the duplicate because that is the record being changed.
        ``keep`` is what the merge screen chose, see ``AttendeeMergeService.merge``;
        without it the primary's details stay and every phone and email is kept.
        Guarded like unmerge: the organization's ``groups_see_all_meets_attendees``.
        ``privileged_to_edit`` would refuse a duplicate that is soft-deleted.
        """
        primary_id = request.data.get("primary")
        if not primary_id:
            raise ValidationError({"primary": "Name the attendee to merge into."})
        keep = request.data.get("keep")
        if keep is not None and not isinstance(keep, dict):
            raise ValidationError({"keep": "Send the details to keep as an object."})

        organization = request.user.organization
        duplicate = get_object_or_404(
            Attendee.all_objects, pk=pk, division__organization=organization
        )
        primary = get_object_or_404(
            Attendee.all_objects, pk=primary_id, division__organization=organization
        )

        if not request.user.belongs_to_groups_of(
            organization.infos.get("groups_see_all_meets_attendees", [])
        ):
            time.sleep(2)
            raise PermissionDenied(detail="Not allowed to merge that attendee.")

        try:
            AttendeeMergeService.merge(
                duplicate, primary, by=request.user.attendee_uuid_str() or None, keep=keep
            )
        except MergeRefused as refusal:
            raise ValidationError({"detail": str(refusal)})

        return Response(
            {"merged_into": str(primary.pk)}, status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["post"], url_path="unmerge")
    def unmerge(self, request, pk=None):
        """``POST .../<duplicate>/unmerge/``: puts back what the merge moved, once."""
        organization = request.user.organization
        duplicate = get_object_or_404(
            Attendee.all_objects, pk=pk, division__organization=organization
        )
        # privileged_to_edit only sees live attendees; a tombstone gets the
        # same groups check without that.
        if not request.user.belongs_to_groups_of(
            organization.infos.get("groups_see_all_meets_attendees", [])
        ):
            time.sleep(2)
            raise PermissionDenied(detail="Not allowed to unmerge that attendee.")

        try:
            AttendeeMergeService.unmerge(duplicate)
        except MergeRefused as refusal:
            raise ValidationError({"detail": str(refusal)})

        return Response({"restored": str(duplicate.pk)}, status=status.HTTP_200_OK)

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
            qs = Attendee.all_objects.annotate(
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
        else:  # a bare list: the whole organization, ordered so pages are stable
            qs = Attendee.objects.order_by("id")

        return qs.filter(division__organization=current_user.organization)

    def perform_create(self, serializer):
        """
        Some post processing can be added for a new attendee just created.  Gathering_id is higher priority than meet.
        """
        instance = serializer.save()
        raw_folk_id = self.request.META.get("HTTP_X_ADD_FOLK")
        role_id = self.request.META.get("HTTP_X_FOLK_ROLE")
        meet_id = self.request.META.get("HTTP_X_JOIN_MEET")
        character_slug = self.request.META.get("HTTP_X_JOIN_CHARACTER")
        gathering_id = self.request.META.get("HTTP_X_JOIN_GATHERING")

        meet = Meet.objects.filter(pk=meet_id).first()

        if raw_folk_id == "new" and role_id:
            folk = Folk.objects.create(
                category_id=0,  # family
                division=instance.division,
                display_name=f'{(instance.last_name + " ") if instance.last_name else ""}{instance.infos.get("names", {}).get("original", "")} family'
            )
            folk_id = folk.id
        else:
            folk_id = raw_folk_id

        if folk_id and role_id:
            FolkAttendee.objects.create(
                folk=get_object_or_404(Folk, pk=folk_id),
                attendee=instance,
                role=get_object_or_404(Relation, pk=role_id),
            )

        if gathering_id:  # elif is needed since using the very same function to add attendingmeet by gathering or meet
            gathering = get_object_or_404(Gathering, pk=gathering_id)
            attendee_to_attendingmeets_cache = AttendingMeetService.flip_attendingmeet_by_existing_attending(self.request.user, [instance], gathering.meet.id, True, None)
            # AttendanceService.join_attendance([instance], gathering, attendee_to_attendingmeets_cache)
        elif meet and meet.assembly.division.organization == self.request.user.organization:
            AttendingMeetService.flip_attendingmeet_by_existing_attending(self.request.user, [instance], meet_id, True, character_slug)

    def perform_update(self, serializer):
        target_attendee = get_object_or_404(
            Attendee, pk=self.request.META.get("HTTP_X_TARGET_ATTENDEE_ID")
        )
        tzname = (
            self.request.COOKIES.get("timezone")
            or target_attendee.division.organization.infos.get("default_time_zone")
            or settings.CLIENT_DEFAULT_TIME_ZONE
        )

        if self.request.user.privileged_to_edit(
            target_attendee.id
        ):  # intentionally forbid user delete him/herself
            try:
                instance = serializer.save()
                if self.request.META.get("HTTP_X_END_ALL_ATTENDEE_ACTIVITIES"):  # passed away
                    AttendeeService.end_all_activities(instance, self.request.user.attendee_uuid_str())

                if self.request.META.get("HTTP_X_ADD_PAST"):
                    AttendeeService.add_past(instance, self.request.META.get("HTTP_X_ADD_PAST"), pytz.timezone(parse.unquote(tzname)))
            except Exception as e:
                logger.error(f"Error updating attendee {target_attendee.id}: {e}", exc_info=True)
                raise

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
