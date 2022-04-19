import pghistory
from django.db import models
import django.utils.timezone
import model_utils.fields
from model_utils.models import SoftDeletableModel, TimeStampedModel


class MessageTemplate(TimeStampedModel, SoftDeletableModel):
    id = models.BigAutoField(
        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
    )
    organization = models.ForeignKey(
        "whereabouts.Organization", null=False, blank=False, on_delete=models.SET(0)
    )
    templates = models.JSONField(
        null=True,
        blank=True,
        default=dict,
        help_text='Example: {"body": "Dear {name}: Hello!"}. Whatever in curly braces will be interpolated by '
        "variables, Please keep {} here even no data",
    )
    defaults = models.JSONField(
        null=True,
        blank=True,
        default=dict,
        help_text='Example: {"name": "John", "Date": "08/31/2020"}. Please keep {} here even no data',
    )
    type = models.SlugField(
        max_length=50,
        blank=False,
        null=False,
        unique=False,
        help_text="format: Organization_slug-prefix-message-type-name",
    )

    class Meta:
        db_table = "occasions_message_templates"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "type"],
                condition=models.Q(is_removed=False),
                name="organization_type",
            ),
        ]

    def __str__(self):
        return "%s %s" % (self.organization, self.type)


class MessageTemplatesHistory(pghistory.get_event_model(
    MessageTemplate,
    pghistory.Snapshot('messagetemplate.snapshot'),
    name='MessageTemplatesHistory',
    related_name='history',
)):
    pgh_id = models.BigAutoField(primary_key=True, serialize=False)
    pgh_created_at = models.DateTimeField(auto_now_add=True)
    pgh_label = models.TextField(help_text='The event label.')
    pgh_obj = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='history', to='occasions.messagetemplate')
    id = models.BigIntegerField(db_index=True)
    created = model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')
    modified = model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')
    is_removed = models.BooleanField(default=False)
    organization = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='whereabouts.organization')
    templates = models.JSONField(blank=True, default=dict, help_text='Example: {"body": "Dear {name}: Hello!"}. Whatever in curly braces will be interpolated by variables, Please keep {} here even no data', null=True)
    defaults = models.JSONField(blank=True, default=dict, help_text='Example: {"name": "John", "Date": "08/31/2020"}. Please keep {} here even no data', null=True)
    type = models.SlugField(db_index=False, help_text='format: Organization_slug-prefix-message-type-name')
    pgh_context = models.ForeignKey(db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')

    class Meta:
        db_table = 'occasions_message_templateshistory'

# from django.db import models
# from django.contrib.postgres.fields.jsonb import JSONField
# from model_utils.models import TimeStampedModel, SoftDeletableModel
#
# from attendees.persons.models import Utility
#
#
# class Message(TimeStampedModel, SoftDeletableModel, Utility):
#     id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
#     obfuscated = models.BooleanField(null=False, blank=False, default=False)
#     template = models.ForeignKey(to='occasions.MessageTemplate')
#     summary = models.CharField(max_length=50, blank=False, null=False, unique=False)
#     last_processed = models.DateTimeField(null=True, blank=True)
#     status = models.CharField(max_length=50)
#     variables = models.JSONField(
#         null=True,
#         blank=True,
#         default=dict,
#         help_text='Example: {"name": "John", "Date": "08/31/2020"}. Please keep {} here even no data'
#     )
#
#     class Meta:
#         db_table = 'occasions_messages'
#         constraints = [
#             models.UniqueConstraint(
#                 fields=['organization', 'type'],
#                 condition=models.Q(is_removed=False),
#                 name='organization_type'
#             ),
#         ]
#
#     def __str__(self):
#         return '%s %s %s %s' % (self.organization, self.type, self.status, self.last_processed)
