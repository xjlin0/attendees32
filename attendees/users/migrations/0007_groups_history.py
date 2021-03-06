# Generated by Django 3.2.11 on 2022-04-08 18:54

from django.db import migrations, models
import django.db.models.deletion

from attendees.persons.models import Utility


class Migration(migrations.Migration):

    dependencies = [
        ('pghistory', '0003_auto_20201023_1636'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('users', '0006_user_permissions_history'),
    ]

    operations = [
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
    ]
