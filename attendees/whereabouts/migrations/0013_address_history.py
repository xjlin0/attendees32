# Generated by Django 3.2.11 on 2022-04-11 18:49

from django.db import migrations, models
import django.db.models.deletion

from attendees.persons.models import Utility


class Migration(migrations.Migration):

    dependencies = [
        ('pghistory', '0003_auto_20201023_1636'),
        ('address', '0005_address_extra'),
        ('whereabouts', '0012_locality_history'),
    ]

    operations = [
        migrations.CreateModel(
            name='AddressHistory',
            fields=[
                ('pgh_id', models.AutoField(primary_key=True, serialize=False)),
                ('pgh_created_at', models.DateTimeField(auto_now_add=True)),
                ('pgh_obj', models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='history', to='address.address')),
                ('pgh_label', models.TextField(help_text='The event label.')),
                ('id', models.IntegerField()),
                ('raw', models.CharField(max_length=200)),
                ('locality', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='address.locality')),
                ('street_number', models.CharField(blank=True, max_length=20)),
                ('extra', models.CharField(blank=True, default=None, max_length=20, null=True)),
                ('name', models.CharField(blank=True, default=None, max_length=40, null=True)),
                ('type', models.CharField(blank=True, default=None, max_length=20, null=True)),
                ('hash', models.CharField(blank=True, default=None, max_length=20, null=True)),
                ('route', models.CharField(blank=True, max_length=100)),
                ('formatted', models.CharField(blank=True, max_length=200)),
                ('latitude', models.FloatField(blank=True, null=True)),
                ('longitude', models.FloatField(blank=True, null=True)),
                ('pgh_context', models.ForeignKey(db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.RunSQL(Utility.pgh_default_sql('whereabouts_addresshistory', index_on_id=True, original_model_table='address_address')),
    ]