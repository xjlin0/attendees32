# Generated by Django 3.2.11 on 2022-03-05 23:43

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import pgtrigger.compiler
import pgtrigger.migrations
from attendees.persons.models import Utility


class Migration(migrations.Migration):

    dependencies = [
        ('pghistory', '0004_auto_20220906_1625'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('users', '0004_menu_auth_group'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserGroupProxy',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('users.user_groups',),
        ),
        migrations.CreateModel(
            name='UserGroupsHistory',
            fields=[
                ('pgh_id', models.AutoField(primary_key=True, serialize=False)),
                ('pgh_created_at', models.DateTimeField(auto_now_add=True)),
                ('pgh_label', models.TextField(help_text='The event label.')),
                ('id', models.IntegerField()),
                ('user', models.ForeignKey(db_constraint=False, db_tablespace='', on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to=settings.AUTH_USER_MODEL)),
                ('group', models.ForeignKey(db_constraint=False, db_tablespace='', on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='auth.group')),
                ('pgh_context', models.ForeignKey(db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')),
            ],
        ),
        migrations.RunSQL(Utility.pgh_default_sql('users_usergroupshistory', original_model_table='users_user_groups')),
        pgtrigger.migrations.AddTrigger(
            model_name='usergroupproxy',
            trigger=pgtrigger.compiler.Trigger(name='group_add', sql=pgtrigger.compiler.UpsertTriggerSql(func='INSERT INTO "users_usergroupshistory" ("user_id", "group_id", "id", "pgh_created_at", "pgh_label", "pgh_context_id") VALUES (NEW."user_id", NEW."group_id", NEW."id", NOW(), \'group.add\', _pgh_attach_context()); RETURN NULL;', hash='90d4d58a36d643f72785ba5a78620efded1b390e', operation='INSERT', pgid='pgtrigger_group_add_7431d', table='users_user_groups', when='AFTER')),
        ),
        pgtrigger.migrations.AddTrigger(
            model_name='usergroupproxy',
            trigger=pgtrigger.compiler.Trigger(name='group_remove', sql=pgtrigger.compiler.UpsertTriggerSql(func='INSERT INTO "users_usergroupshistory" ("user_id", "group_id", "id", "pgh_created_at", "pgh_label", "pgh_context_id") VALUES (OLD."user_id", OLD."group_id", OLD."id", NOW(), \'group.remove\', _pgh_attach_context()); RETURN NULL;', hash='44c14856fd875d194b6a06f8cf43c81c9600e374', operation='DELETE', pgid='pgtrigger_group_remove_49cba', table='users_user_groups', when='AFTER')),
        ),
    ]
