# Generated by Django 3.0.2 on 2020-01-14 04:36

from attendees.persons.models import Utility
from django.db import migrations, models
import django.utils.timezone
import model_utils.fields
import pgtrigger.compiler
import pgtrigger.migrations


class Migration(migrations.Migration):

    dependencies = [
        ('occasions', '0003_price'),
        ('persons', '0006_attendee'),
    ]

    operations = [
        migrations.CreateModel(
            name='Registration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('is_removed', models.BooleanField(default=False)),
                ('assembly', models.ForeignKey(on_delete=models.deletion.DO_NOTHING, to='occasions.Assembly')),
                ('registrant', models.ForeignKey(null=True, on_delete=models.deletion.SET_NULL, to='persons.Attendee')),
                ('infos', models.JSONField(blank=True, default=dict, help_text=('Example: {"price": "150.75", "donation": "85.00", "credit": "35.50", "apply_type": "online","apply_key": "001"}. Please keep {} here even no data',), null=True)),
            ],
            options={
                'db_table': 'persons_registrations',
                'ordering': ('assembly', 'registrant__last_name', 'registrant__first_name'),
            },
            bases=(models.Model, Utility),
        ),
        migrations.RunSQL(Utility.default_sql('persons_registrations')),
        migrations.AddConstraint(
            model_name='registration',
            constraint=models.UniqueConstraint(fields=('assembly', 'registrant'), condition=models.Q(is_removed=False), name='assembly_registrant'),
        ),
        migrations.AddIndex(
            model_name='registration',
            index=django.contrib.postgres.indexes.GinIndex(fields=['infos'], name='registration_infos_gin'),
        ),
        migrations.CreateModel(
            name='RegistrationsHistory',
            fields=[
                ('pgh_id', models.BigAutoField(primary_key=True, serialize=False)),
                ('pgh_created_at', models.DateTimeField(auto_now_add=True)),
                ('pgh_label', models.TextField(help_text='The event label.')),
                ('pgh_obj', models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.DO_NOTHING, related_name='history', to='persons.registration')),
                ('id', models.BigIntegerField(db_index=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('is_removed', models.BooleanField(default=False)),
                ('assembly', models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='occasions.assembly')),
                ('infos', models.JSONField(blank=True, default=dict, help_text=('Example: {"price": "150.75", "donation": "85.00", "credit": "35.50", "apply_type": "online","apply_key": "001"}. Please keep {} here even no data',), null=True)),
                ('registrant', models.ForeignKey(db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='persons.attendee')),
                ('pgh_context', models.ForeignKey(db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')),
            ],
            options={
                'db_table': 'persons_registrationshistory',
            },
        ),
        migrations.RunSQL(Utility.pgh_default_sql('persons_registrationshistory', original_model_table='persons_registrations')),
        pgtrigger.migrations.AddTrigger(
            model_name='registration',
            trigger=pgtrigger.compiler.Trigger(name='registration_snapshot_insert', sql=pgtrigger.compiler.UpsertTriggerSql(func='INSERT INTO "persons_registrationshistory" ("id", "created", "modified", "is_removed", "assembly_id", "infos", "registrant_id", "pgh_created_at", "pgh_label", "pgh_obj_id", "pgh_context_id") VALUES (NEW."id", NEW."created", NEW."modified", NEW."is_removed", NEW."assembly_id", NEW."infos", NEW."registrant_id", NOW(), \'registration.snapshot\', NEW."id", _pgh_attach_context()); RETURN NULL;', hash='e84bb653cd7078647ac7818ff71a4408713fcfa4', operation='INSERT', pgid='pgtrigger_registration_snapshot_insert_749b9', table='persons_registrations', when='AFTER')),
        ),
        pgtrigger.migrations.AddTrigger(
            model_name='registration',
            trigger=pgtrigger.compiler.Trigger(name='registration_snapshot_update', sql=pgtrigger.compiler.UpsertTriggerSql(condition='WHEN (OLD."id" IS DISTINCT FROM NEW."id" OR OLD."created" IS DISTINCT FROM NEW."created" OR OLD."modified" IS DISTINCT FROM NEW."modified" OR OLD."is_removed" IS DISTINCT FROM NEW."is_removed" OR OLD."assembly_id" IS DISTINCT FROM NEW."assembly_id" OR OLD."infos" IS DISTINCT FROM NEW."infos" OR OLD."registrant_id" IS DISTINCT FROM NEW."registrant_id")', func='INSERT INTO "persons_registrationshistory" ("id", "created", "modified", "is_removed", "assembly_id", "infos", "registrant_id", "pgh_created_at", "pgh_label", "pgh_obj_id", "pgh_context_id") VALUES (NEW."id", NEW."created", NEW."modified", NEW."is_removed", NEW."assembly_id", NEW."infos", NEW."registrant_id", NOW(), \'registration.snapshot\', NEW."id", _pgh_attach_context()); RETURN NULL;', hash='ea0dc65af5a252be6191d12bab52abad2472a4e0', operation='UPDATE', pgid='pgtrigger_registration_snapshot_update_ce443', table='persons_registrations', when='AFTER')),
        ),
        pgtrigger.migrations.AddTrigger(
            model_name='registration',
            trigger=pgtrigger.compiler.Trigger(name='registration_before_delete', sql=pgtrigger.compiler.UpsertTriggerSql(func='INSERT INTO "persons_registrationshistory" ("id", "created", "modified", "is_removed", "assembly_id", "infos", "registrant_id", "pgh_created_at", "pgh_label", "pgh_obj_id", "pgh_context_id") VALUES (OLD."id", OLD."created", OLD."modified", OLD."is_removed", OLD."assembly_id", OLD."infos", OLD."registrant_id", NOW(), \'registration.before_delete\', OLD."id", _pgh_attach_context()); RETURN NULL;', hash='62a222ccc0bf98e434668b8daaa78d6ffc570432', operation='DELETE', pgid='pgtrigger_registration_before_delete_1d1fa', table='persons_registrations', when='AFTER')),
        ),
    ]
