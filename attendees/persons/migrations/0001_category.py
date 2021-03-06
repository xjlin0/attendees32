# Generated by Django 3.0.5 on 2020-04-29 00:33

from django.db import migrations, models
from attendees.persons.models import Utility
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('persons', '0000_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('is_removed', models.BooleanField(default=False)),
                ('display_order', models.SmallIntegerField(default=0, blank=False, null=False, db_index=True)),
                ('type', models.CharField(blank=False, max_length=25, db_index=True, null=False, default='generic', help_text='main type')),
                ('display_name', models.CharField(blank=False, max_length=50, null=False, db_index=True)),
                ('infos', models.JSONField(blank=True, default=dict, help_text='Example: {"icon": "home", "style": "normal"}. Please keep {} here even no data', null=True)),
            ],
            options={
                'db_table': 'persons_categories',
                'verbose_name_plural': 'Categories',
                'ordering': ('type', 'display_order'),
            },
        ),
        migrations.RunSQL(Utility.default_sql('persons_categories')),
        migrations.AddIndex(
            model_name='category',
            index=django.contrib.postgres.indexes.GinIndex(fields=['infos'], name='category_infos_gin'),
        ),
        migrations.CreateModel(
            name='CategoriesHistory',
            fields=[
                ('pgh_id', models.BigAutoField(primary_key=True, serialize=False)),
                ('pgh_created_at', models.DateTimeField(auto_now_add=True)),
                ('pgh_label', models.TextField(help_text='The event label.')),
                ('pgh_obj', models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='history', to='persons.category')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('is_removed', models.BooleanField(default=False)),
                ('type', models.CharField(default='generic', help_text='main type', max_length=25)),
                ('display_order', models.SmallIntegerField(default=0)),
                ('display_name', models.CharField(max_length=50)),
                ('infos', models.JSONField(blank=True, default=dict, help_text='Example: {"icon": "home", "style": "normal"}. Please keep {} here even no data', null=True)),
                ('id', models.BigIntegerField(db_index=True)),
                ('pgh_context', models.ForeignKey(db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')),
            ],
            options={
                'db_table': 'persons_categorieshistory',
            },
        ),
        migrations.RunSQL(Utility.pgh_default_sql('persons_categorieshistory')),
    ]
