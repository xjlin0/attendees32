from typing import Optional

from django.db.models.signals import post_save
from django.dispatch import receiver
from schedule.models import Occurrence

from attendees.occasions.models import Gathering, Meet


@receiver(post_save, sender=Gathering)
def post_save_handler_for_gathering_to_update_occurrence(sender, **kwargs):
    if not kwargs.get("raw"):  # to skip extra creation in loaddata seed
        gathering: Optional[Gathering] = kwargs.get("instance")
        meet = gathering.meet
        event_relation = meet.event_relations.filter(distinction='source').first()
        if event_relation:
            occurrences = gathering.occurrences()
            description = f'{gathering.site.__class__.__name__.lower()}#{gathering.site.pk}'
            title = f'{gathering.__class__.__name__.lower()}#{gathering.pk}'
            if occurrences:
                for occurrence in occurrences:
                    if gathering.is_removed:
                        occurrence.delete()
                    else:
                        occurrence.description = description
                        occurrence.start = gathering.start
                        occurrence.end = gathering.finish
                        occurrence.save()
            else:
                if not gathering.is_removed and gathering.infos.get('created_reason') != 'batch created':  # prevent duplicates from GatheringService.batch_create()
                    occurrence = Occurrence(
                        event=event_relation.event,
                        title=title,
                        description=description,
                        start=gathering.start,
                        end=gathering.finish,
                        original_start=gathering.start,
                        original_end=gathering.finish,
                    )
                    occurrence.save()


# @receiver(post_save, sender=Meet)
# def post_save_handler_for_meet_to_update_event_location(sender, **kwargs):
#     # Todo 20220923 remove this once the meet editing UI implemented
#     if not kwargs.get("raw"):  # to skip extra creation in loaddata seed
#         meet = kwargs.get("instance")
#         # Todo 20220927 need to update location's event too
#         for event_relation in meet.event_relations.filter(distinction='source'):
#             description = f'{meet.site.__class__.__name__.lower()}#{meet.site.pk}'
#             event = event_relation.event
#             event.description = description
#             event.save()
