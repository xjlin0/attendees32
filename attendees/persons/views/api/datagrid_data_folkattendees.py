from datetime import datetime, timezone

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from rest_framework import viewsets

from attendees.persons.models import Attendee, FolkAttendee, Utility, Past
from attendees.persons.serializers import FolkAttendeeSerializer
from attendees.persons.services import AttendingMeetService
from attendees.users.authorization.route_guard import SpyGuard


@method_decorator([login_required], name='dispatch')
class ApiDatagridDataFolkAttendeesViewsSet(SpyGuard, viewsets.ModelViewSet
):
    """
    API endpoint that allows FamiliesAttendees of a single Attendee in headers to be viewed or edited.
    For example, if Alice, Bob & Charlie are in a family, passing Alice's attendee id in headers (key:
    X-TARGET-ATTENDEE-ID) will return all 3 FamilyAttendee objects of Alice, Bob & Charlie. Also,
    attaching Bob's FamilyAttendee id at the end of the endpoint will return Bob's FamilyAttendee only.

    scope: counsellors see all, coworkers see all families and drivers, others see their own familis only.

    Note: If Dick is not in the family, passing Dick's attendee id in headers plus Bob's FamilyAttendee
    id at the end of the endpoint will return nothing.
    """

    serializer_class = FolkAttendeeSerializer

    def get_queryset(self):
        target_attendee = get_object_or_404(
            Attendee, pk=self.request.META.get("HTTP_X_TARGET_ATTENDEE_ID")
        )
        target_folkattendee_id = self.kwargs.get("pk")
        category = self.request.query_params.get("categoryId")  # string so '0' is truthy
        qs = FolkAttendee.objects if self.request.user.privileged_to_edit(target_attendee.id) else self.request.user.attendee.folkattendee_set
        target_attendee_all_folks = target_attendee.folks.filter(folkattendee__is_removed=False)
        target_attendee_other_folks = target_attendee_all_folks.exclude(category=Attendee.FAMILY_CATEGORY).filter(folkattendee__role=Attendee.HIDDEN_ROLE, folkattendee__attendee=target_attendee)
        target_attendee_in_others_other_folks = target_attendee_all_folks.exclude(category=Attendee.FAMILY_CATEGORY).exclude(pk__in=target_attendee_other_folks)
        filters = Q(folk__in=target_attendee_all_folks)

        if target_folkattendee_id:
            filters.add(Q(pk=target_folkattendee_id), Q.AND)

        if self.request.user.is_counselor():  # see both family and all other
            if category:
                filters.add(Q(folk__category=category), Q.AND)
        elif self.request.user.is_a(Past.COWORKER):  # sees family and driver only
            if category == '0':     # family type
                filters.add(Q(folk__category=Attendee.FAMILY_CATEGORY), Q.AND)
            elif category == '25':  # other type
                filters.add(Q(role__title="driver"), Q.AND)
            else:  # no category passed in to query both types
                filters.add(Q(Q(folk__category=Attendee.FAMILY_CATEGORY) | Q(role__title="driver")), Q.AND)
        else:  # ordinary attendee only see families, not even drivers since traffic arrangement is internal
            filters.add(Q(folk__category=Attendee.FAMILY_CATEGORY), Q.AND)

        if not self.request.user.privileged():  # ordinary users don't see past
            filters.add(Q(Q(finish__isnull=True) | Q(finish__gte=datetime.now(timezone.utc))), Q.AND)

        return qs.filter(filters).exclude(
                role=Attendee.HIDDEN_ROLE,
               ).exclude(  # Todo 20230502 optimize to exclude rows in other attendee's other folks
                ~Q(attendee=target_attendee),
                folk__in=target_attendee_in_others_other_folks,
               ).order_by(
                "folk",
                "folk__display_order",
                "display_order",
                "role__display_order",
               )

    def perform_update(self, serializer):  # Todo 20220706 respond for joining and families count
        instance = serializer.save()
        Utility.add_update_attendee_in_infos(instance, self.request.user.attendee_uuid_str())
        print_directory = instance.folk.infos.get('print_directory') and instance.folk.category_id == 0  # family
        directory_meet_id = self.request.user.organization.infos.get('settings', {}).get('default_directory_meet')
        AttendingMeetService.flip_attendingmeet_by_existing_attending(self.request.user, [instance.attendee], directory_meet_id, print_directory)

    def perform_create(self, serializer):
        instance = serializer.save()
        Utility.add_update_attendee_in_infos(instance, self.request.user.attendee_uuid_str())
        print_directory = instance.folk.infos.get('print_directory') and instance.folk.category_id == 0  # family
        directory_meet_id = self.request.user.organization.infos.get('settings', {}).get('default_directory_meet')
        AttendingMeetService.flip_attendingmeet_by_existing_attending(self.request.user, [instance.attendee], directory_meet_id, print_directory)

    def perform_destroy(self, instance):  # Todo 20221203 should it flip_attendingmeet_by_existing_attending?
        Utility.add_update_attendee_in_infos(instance, self.request.user.attendee_uuid_str())
        instance.delete()


api_datagrid_data_folkattendees_viewset = ApiDatagridDataFolkAttendeesViewsSet
