# Generated by Django 3.2.11 on 2022-04-08 19:41

from django.db import migrations, models
import django.db.models.deletion

from attendees.persons.models import Utility


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('pghistory', '0003_auto_20201023_1636'),
        ('users', '0007_grouphistory'),
    ]

    operations = [
        migrations.CreateModel(
            name='GroupPermissionHistory',
            fields=[
                ('pgh_id', models.AutoField(primary_key=True, serialize=False)),
                ('pgh_created_at', models.DateTimeField(auto_now_add=True)),
                ('id', models.IntegerField()),
                ('group', models.ForeignKey(db_constraint=False, db_tablespace='', on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='auth.group')),
                ('permission', models.ForeignKey(db_constraint=False, db_tablespace='', on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='auth.permission')),
                ('pgh_label', models.TextField(help_text='The event label.')),
                ('pgh_context', models.ForeignKey(db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.RunSQL(Utility.pgh_default_sql('users_grouppermissionhistory')),
    ]