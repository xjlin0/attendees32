# Generated by Django 3.2.11 on 2022-04-11 18:33

from django.db import migrations, models
import django.db.models.deletion

from attendees.persons.models import Utility


class Migration(migrations.Migration):

    dependencies = [
        ('pghistory', '0003_auto_20201023_1636'),
        ('address', '0005_address_extra'),
        ('whereabouts', '0010_country_history'),
    ]

    operations = [
        migrations.CreateModel(
            name='StateHistory',
            fields=[
                ('pgh_id', models.AutoField(primary_key=True, serialize=False)),
                ('pgh_created_at', models.DateTimeField(auto_now_add=True)),
                ('pgh_obj', models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='history', to='address.state')),
                ('pgh_label', models.TextField(help_text='The event label.')),
                ('id', models.IntegerField()),
                ('country', models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='address.country')),
                ('code', models.CharField(blank=True, max_length=8)),
                ('name', models.CharField(blank=True, max_length=165)),
                ('pgh_context', models.ForeignKey(db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.RunSQL(Utility.pgh_default_sql('whereabouts_statehistory', index_on_id=True, original_model_table='address_state')),
    ]