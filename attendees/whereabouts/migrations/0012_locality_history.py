# Generated by Django 3.2.11 on 2022-04-11 18:44

from django.db import migrations, models
import django.db.models.deletion
import pgtrigger.compiler
import pgtrigger.migrations
from attendees.persons.models import Utility


class Migration(migrations.Migration):

    dependencies = [
        ('address', '0005_address_extra'),
        ('pghistory', '0004_auto_20220906_1625'),
        ('whereabouts', '0011_state_history'),
    ]

    operations = [
        migrations.CreateModel(
            name='LocalityProxy',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('address.locality',),
        ),
        migrations.CreateModel(
            name='LocalityHistory',
            fields=[
                ('pgh_id', models.AutoField(primary_key=True, serialize=False)),
                ('pgh_created_at', models.DateTimeField(auto_now_add=True)),
                ('pgh_obj', models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='history', to='address.locality')),
                ('pgh_label', models.TextField(help_text='The event label.')),
                ('id', models.IntegerField()),
                ('state', models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='address.state')),
                ('postal_code', models.CharField(blank=True, max_length=10)),
                ('name', models.CharField(blank=True, max_length=165)),
                ('pgh_context', models.ForeignKey(db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.RunSQL(Utility.pgh_default_sql('whereabouts_localityhistory', index_on_id=True, original_model_table='address_locality')),
        migrations.AlterField(
            model_name='localityhistory',
            name='pgh_obj',
            field=models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.DO_NOTHING, related_name='history', to='whereabouts.localityproxy'),
        ),
        pgtrigger.migrations.AddTrigger(
            model_name='localityproxy',
            trigger=pgtrigger.compiler.Trigger(name='locality_snapshot_insert', sql=pgtrigger.compiler.UpsertTriggerSql(func='INSERT INTO "whereabouts_localityhistory" ("name", "postal_code", "state_id", "id", "pgh_created_at", "pgh_label", "pgh_obj_id", "pgh_context_id") VALUES (NEW."name", NEW."postal_code", NEW."state_id", NEW."id", NOW(), \'locality.snapshot\', NEW."id", _pgh_attach_context()); RETURN NULL;', hash='b3487f7b247380df9943bf4e19cfbaaea3aaaaaf', operation='INSERT', pgid='pgtrigger_locality_snapshot_insert_b9cfb', table='address_locality', when='AFTER')),
        ),
        pgtrigger.migrations.AddTrigger(
            model_name='localityproxy',
            trigger=pgtrigger.compiler.Trigger(name='locality_snapshot_update', sql=pgtrigger.compiler.UpsertTriggerSql(condition='WHEN (OLD."name" IS DISTINCT FROM NEW."name" OR OLD."postal_code" IS DISTINCT FROM NEW."postal_code" OR OLD."state_id" IS DISTINCT FROM NEW."state_id" OR OLD."id" IS DISTINCT FROM NEW."id")', func='INSERT INTO "whereabouts_localityhistory" ("name", "postal_code", "state_id", "id", "pgh_created_at", "pgh_label", "pgh_obj_id", "pgh_context_id") VALUES (NEW."name", NEW."postal_code", NEW."state_id", NEW."id", NOW(), \'locality.snapshot\', NEW."id", _pgh_attach_context()); RETURN NULL;', hash='ca5e7c1bdbe7d8f0eb9d042df897529d93230749', operation='UPDATE', pgid='pgtrigger_locality_snapshot_update_0c9dc', table='address_locality', when='AFTER')),
        ),
        pgtrigger.migrations.AddTrigger(
            model_name='localityproxy',
            trigger=pgtrigger.compiler.Trigger(name='locality_before_delete', sql=pgtrigger.compiler.UpsertTriggerSql(func='INSERT INTO "whereabouts_localityhistory" ("name", "postal_code", "state_id", "id", "pgh_created_at", "pgh_label", "pgh_obj_id", "pgh_context_id") VALUES (OLD."name", OLD."postal_code", OLD."state_id", OLD."id", NOW(), \'locality.before_delete\', OLD."id", _pgh_attach_context()); RETURN NULL;', hash='28d25b5113a483f1ef400346f38af90b06245766', operation='DELETE', pgid='pgtrigger_locality_before_delete_e11c7', table='address_locality', when='AFTER')),
        ),
    ]
