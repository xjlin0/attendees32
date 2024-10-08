# Generated by Django 3.2.11 on 2022-04-08 18:54

from django.db import migrations, models
import django.db.models.deletion
import pgtrigger.compiler
import pgtrigger.migrations
from attendees.persons.models import Utility


class Migration(migrations.Migration):

    dependencies = [
        ('pghistory', '0004_auto_20220906_1625'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('users', '0007_user_permissions_history'),
    ]

    operations = [
        migrations.CreateModel(
            name='GroupProxy',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('auth.group',),
            managers=[
                ('objects', django.contrib.auth.models.GroupManager()),
            ],
        ),
        migrations.CreateModel(
            name='GroupsHistory',
            fields=[
                ('pgh_id', models.AutoField(primary_key=True, serialize=False)),
                ('pgh_created_at', models.DateTimeField(auto_now_add=True)),
                ('pgh_obj', models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='history', to='auth.group')),
                ('id', models.IntegerField()),
                ('pgh_label', models.TextField(help_text='The event label.')),
                ('name', models.CharField(max_length=150, verbose_name='name')),
                ('pgh_context', models.ForeignKey(db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.RunSQL(Utility.pgh_default_sql('users_groupshistory', index_on_id=True, original_model_table='auth_group')),
        migrations.AlterField(
            model_name='groupshistory',
            name='pgh_obj',
            field=models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.DO_NOTHING, related_name='history', to='users.groupproxy'),
        ),
        pgtrigger.migrations.AddTrigger(
            model_name='groupproxy',
            trigger=pgtrigger.compiler.Trigger(name='group_snapshot_insert', sql=pgtrigger.compiler.UpsertTriggerSql(func='INSERT INTO "users_groupshistory" ("name", "id", "pgh_created_at", "pgh_label", "pgh_obj_id", "pgh_context_id") VALUES (NEW."name", NEW."id", NOW(), \'group.snapshot\', NEW."id", _pgh_attach_context()); RETURN NULL;', hash='7c5ceac9f6456146c67d735da97c9f35c3298558', operation='INSERT', pgid='pgtrigger_group_snapshot_insert_d7fcb', table='auth_group', when='AFTER')),
        ),
        pgtrigger.migrations.AddTrigger(
            model_name='groupproxy',
            trigger=pgtrigger.compiler.Trigger(name='group_snapshot_update', sql=pgtrigger.compiler.UpsertTriggerSql(condition='WHEN (OLD."name" IS DISTINCT FROM NEW."name" OR OLD."id" IS DISTINCT FROM NEW."id")', func='INSERT INTO "users_groupshistory" ("name", "id", "pgh_created_at", "pgh_label", "pgh_obj_id", "pgh_context_id") VALUES (NEW."name", NEW."id", NOW(), \'group.snapshot\', NEW."id", _pgh_attach_context()); RETURN NULL;', hash='f35d03a2d05ef13cb59b81e4761ecae6445d9134', operation='UPDATE', pgid='pgtrigger_group_snapshot_update_adcdd', table='auth_group', when='AFTER')),
        ),
        pgtrigger.migrations.AddTrigger(
            model_name='groupproxy',
            trigger=pgtrigger.compiler.Trigger(name='group_before_delete', sql=pgtrigger.compiler.UpsertTriggerSql(func='INSERT INTO "users_groupshistory" ("name", "id", "pgh_created_at", "pgh_label", "pgh_obj_id", "pgh_context_id") VALUES (OLD."name", OLD."id", NOW(), \'group.before_delete\', OLD."id", _pgh_attach_context()); RETURN NULL;', hash='706619536b03b8debc5d4a72c12307f3d6291b3d', operation='DELETE', pgid='pgtrigger_group_before_delete_9d26d', table='auth_group', when='AFTER')),
        ),
    ]
