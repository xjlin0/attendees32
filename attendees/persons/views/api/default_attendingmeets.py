from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.viewsets import ModelViewSet

from attendees.occasions.models import Meet
from attendees.persons.models import AttendingMeet, Utility, Attending, Attendee, Category
from attendees.users.authorization.route_guard import SpyGuard


@method_decorator([login_required], name='dispatch')
class ApiDefaultAttendingmeetsViewSet(SpyGuard, ModelViewSet):  # from GenericAPIView
    """
    API endpoint that allows AttendingMeet to be created/modified by the default character and attending https://stackoverflow.com/a/70128273/4257237
    """

    def put(self, request, *args, **kwargs):
        is_join = request.data.get('action') == 'join'
        meet = get_object_or_404(Meet, slug=request.data.get("meet"))
        first_attending = Attending.objects.filter(
            attendee=request.META.get("HTTP_X_TARGET_ATTENDEE_ID"),
            price__isnull=True,
        ).order_by('created').first()

        if first_attending and meet.major_character:
            filters = {
                "meet": meet,
                "attending": first_attending,
                "is_removed": False,
            }

            if is_join:
                filters['character'] = meet.major_character

            defaults = {**filters}
            if is_join:
                defaults['finish'] = Utility.now_with_timezone(timedelta(weeks=1040))
                defaults['category'] = Category.objects.get(pk=(request.data.get('category') or meet.infos.get('active_category') or Attendee.SCHEDULED_CATEGORY))
            else:
                defaults['finish'] = Utility.now_with_timezone()

            attendingmeet, created = Utility.update_or_create_last(
                AttendingMeet,
                update=True,
                filters=filters,
                order_key='created',
                defaults=defaults,
            )

            if attendingmeet:
                preview_url = meet.infos.get("preview_url")
                message = {'meet__display_name': meet.display_name, 'id': attendingmeet.id, 'category': attendingmeet.category.id}

                if attendingmeet.infos.get('note'):
                    message['infos__note'] = attendingmeet.infos.get('note')

                if preview_url:
                    message['preview_url'] = preview_url

                attendingmeet.attending.attendee.save(update_fields=['modified'])

                return JsonResponse(
                    message,
                    status=status.HTTP_200_OK,
                    safe=False,
                    json_dumps_params={'ensure_ascii': False},
                )
        return JsonResponse(
            {"error": "Can't find attending or meet's major character!"},
            status=status.HTTP_400_BAD_REQUEST,
        )


api_default_attendingmeets_viewset = ApiDefaultAttendingmeetsViewSet
