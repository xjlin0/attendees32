# Generated by Django 3.2.11 on 2022-04-09 00:26

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import pgtrigger.compiler
import pgtrigger.migrations
from attendees.persons.models import Utility


class Migration(migrations.Migration):

    dependencies = [
        ('pghistory', '0004_auto_20220906_1625'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('schedule', '0014_use_autofields_for_pk'),
        ('occasions', '0015_rule_history'),
    ]

    operations = [
        migrations.CreateModel(
            name='EventProxy',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('schedule.event',),
        ),
        migrations.CreateModel(
            name='EventHistory',
            fields=[
                ('pgh_id', models.AutoField(primary_key=True, serialize=False)),
                ('pgh_created_at', models.DateTimeField(auto_now_add=True)),
                ('pgh_obj', models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.DO_NOTHING, related_name='history', to='schedule.event')),
                ('id', models.IntegerField()),
                ('created_on', models.DateTimeField(auto_now_add=True, verbose_name='created on')),
                ('updated_on', models.DateTimeField(auto_now=True, verbose_name='updated on')),
                ('start', models.DateTimeField(verbose_name='start')),
                ('end', models.DateTimeField(help_text='The end time must be later than the start time.', verbose_name='end')),
                ('calendar', models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='schedule.calendar', verbose_name='calendar')),
                ('rule', models.ForeignKey(blank=True, db_constraint=False, help_text="Select '----' for a one time only event.", null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='schedule.rule', verbose_name='rule')),
                ('creator', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to=settings.AUTH_USER_MODEL, verbose_name='creator')),
                ('end_recurring_period', models.DateTimeField(blank=True, help_text='This date is ignored for one time only events.', null=True, verbose_name='end recurring period')),
                ('pgh_label', models.TextField(help_text='The event label.')),
                ('title', models.CharField(max_length=255, verbose_name='title')),
                ('color_event', models.CharField(blank=True, max_length=10, verbose_name='Color event')),
                ('pgh_context', models.ForeignKey(db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')),
                ('description', models.TextField(blank=True, verbose_name='description')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.RunSQL(Utility.pgh_default_sql('occasions_eventhistory', index_on_id=True, original_model_table='schedule_event')),
        pgtrigger.migrations.AddTrigger(
            model_name='eventproxy',
            trigger=pgtrigger.compiler.Trigger(name='event_snapshot_insert', sql=pgtrigger.compiler.UpsertTriggerSql(func='INSERT INTO "occasions_eventhistory" ("start", "end", "title", "description", "creator_id", "created_on", "updated_on", "rule_id", "end_recurring_period", "calendar_id", "color_event", "id", "pgh_created_at", "pgh_label", "pgh_obj_id", "pgh_context_id") VALUES (NEW."start", NEW."end", NEW."title", NEW."description", NEW."creator_id", NEW."created_on", NEW."updated_on", NEW."rule_id", NEW."end_recurring_period", NEW."calendar_id", NEW."color_event", NEW."id", NOW(), \'event.snapshot\', NEW."id", _pgh_attach_context()); RETURN NULL;', hash='edfc6623913c351964a77a95ca2461e7c654c423', operation='INSERT', pgid='pgtrigger_event_snapshot_insert_95439', table='schedule_event', when='AFTER')),
        ),
        pgtrigger.migrations.AddTrigger(
            model_name='eventproxy',
            trigger=pgtrigger.compiler.Trigger(name='event_snapshot_update', sql=pgtrigger.compiler.UpsertTriggerSql(condition='WHEN (OLD."start" IS DISTINCT FROM NEW."start" OR OLD."end" IS DISTINCT FROM NEW."end" OR OLD."title" IS DISTINCT FROM NEW."title" OR OLD."description" IS DISTINCT FROM NEW."description" OR OLD."creator_id" IS DISTINCT FROM NEW."creator_id" OR OLD."created_on" IS DISTINCT FROM NEW."created_on" OR OLD."updated_on" IS DISTINCT FROM NEW."updated_on" OR OLD."rule_id" IS DISTINCT FROM NEW."rule_id" OR OLD."end_recurring_period" IS DISTINCT FROM NEW."end_recurring_period" OR OLD."calendar_id" IS DISTINCT FROM NEW."calendar_id" OR OLD."color_event" IS DISTINCT FROM NEW."color_event" OR OLD."id" IS DISTINCT FROM NEW."id")', func='INSERT INTO "occasions_eventhistory" ("start", "end", "title", "description", "creator_id", "created_on", "updated_on", "rule_id", "end_recurring_period", "calendar_id", "color_event", "id", "pgh_created_at", "pgh_label", "pgh_obj_id", "pgh_context_id") VALUES (NEW."start", NEW."end", NEW."title", NEW."description", NEW."creator_id", NEW."created_on", NEW."updated_on", NEW."rule_id", NEW."end_recurring_period", NEW."calendar_id", NEW."color_event", NEW."id", NOW(), \'event.snapshot\', NEW."id", _pgh_attach_context()); RETURN NULL;', hash='ffefb9117971b6c3a5e2239889dfe429e421769d', operation='UPDATE', pgid='pgtrigger_event_snapshot_update_1fea0', table='schedule_event', when='AFTER')),
        ),
        migrations.AlterField(
            model_name='eventhistory',
            name='pgh_obj',
            field=models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.DO_NOTHING, related_name='history', to='occasions.eventproxy'),
        ),
    ]