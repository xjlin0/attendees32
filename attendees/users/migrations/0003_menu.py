# Generated by Django 3.0.2 on 2020-04-11 15:33

from attendees.persons.models import Utility
from django.db import migrations, models
import django.utils.timezone
import model_utils.fields
import mptt.fields


class Migration(migrations.Migration):

    dependencies = [
        # ('whereabouts', '0009_attendee_contact_m2m'),
        ('occasions', '0009_meet_attending'),
        ('users', '0002_user_organization'),
    ]

    operations = [
        migrations.CreateModel(
            name='Menu',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('is_removed', models.BooleanField(default=False)),
                ('category', models.CharField(default='main', help_text="Type of menu, such as 'main', 'side', etc", db_index=True, max_length=32)),
                ('html_type', models.CharField(blank=True, help_text="HTML tags such as div or a. For API it can be blank", max_length=50, null=False)),
                ('urn', models.CharField(blank=True, help_text="use relative path (including leading & ending slash '/') such as /app/division/assembly/page-name", max_length=255, null=True)),
                ('url_name', models.SlugField(blank=False, null=False, db_index=True, help_text="view name of the path, such as 'assembly_attendances', 'divider between index and register links', etc. For API it's class name", max_length=255)),
                ('display_name', models.CharField(blank=False, null=False, help_text="description of the path, such as 'Character index page', 'divider between index and register links', etc", max_length=50)),
                ('display_order', models.SmallIntegerField(default=0)),
                ('infos', models.JSONField(blank=True, default=dict, help_text="HTML attributes & more such as {'class': 'dropdown-item'}. Please keep {} here even no data.", null=True)),
                ('lft', models.PositiveIntegerField(editable=False)),
                ('rght', models.PositiveIntegerField(editable=False)),
                ('tree_id', models.PositiveIntegerField(db_index=True, editable=False)),
                ('level', models.PositiveIntegerField(editable=False)),
                ('organization', models.ForeignKey(default=0, help_text='Organization of the menu', on_delete=models.SET(0), to='whereabouts.Organization')),
                ('parent', mptt.fields.TreeForeignKey(blank=True, null=True, on_delete=models.SET(-1), related_name='children', to='users.Menu')),
            ],
            options={
                'db_table': 'users_menus',
            },
        ),
        migrations.RunSQL(Utility.default_sql('users_menus')),
        # migrations.AddConstraint(
        #     model_name='menu',
        #     constraint=models.UniqueConstraint(fields=('organization', 'category', 'html_type', 'url_name'), condition=models.Q(is_removed=False), name='organization_category_html_type_url_name'),
        # ),
        migrations.CreateModel(
            name='MenusHistory',
            fields=[
                ('pgh_id', models.BigAutoField(primary_key=True, serialize=False)),
                ('pgh_created_at', models.DateTimeField(auto_now_add=True)),
                ('pgh_label', models.TextField(help_text='The event label.')),
                ('pgh_obj', models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='history', to='users.menu')),
                ('id', models.IntegerField(db_index=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('organization', models.ForeignKey(db_constraint=False, default=0, help_text='Organization of the menu', on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='whereabouts.organization')),
                ('is_removed', models.BooleanField(default=False)),
                ('tree_id', models.PositiveIntegerField(editable=False)),
                ('level', models.PositiveIntegerField(editable=False)),
                ('lft', models.PositiveIntegerField(editable=False)),
                ('rght', models.PositiveIntegerField(editable=False)),
                ('display_order', models.SmallIntegerField(default=0)),
                ('category', models.CharField(default='main', help_text="Type of menu, such as 'main', 'side', etc", max_length=32)),
                ('url_name', models.SlugField(db_index=False, help_text="view name of the path, such as 'assembly_attendances', 'divider between index and register links', etc. For API it's class name", max_length=255)),
                ('display_name', models.CharField(help_text="description of the path, such as 'Character index page', 'divider between index and register links', etc", max_length=50)),
                ('infos', models.JSONField(blank=True, default=dict, help_text="HTML attributes & more such as {'class': 'dropdown-item'}. Please keep {} here even no data.", null=True)),
                ('parent', mptt.fields.TreeForeignKey(blank=True, db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='users.menu')),
                ('urn', models.CharField(blank=True, help_text="use relative path (including leading & ending slash '/') such as /app/division/assembly/page-name", max_length=255, null=True)),
                ('html_type', models.CharField(blank=True, help_text='HTML tags such as div or a. For API it can be blank', max_length=50)),
                ('pgh_context', models.ForeignKey(db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')),
            ],
            options={
                'db_table': 'users_menushistory',
            },
        ),
        migrations.RunSQL(Utility.pgh_default_sql('users_menushistory', original_model_table='users_menus')),
    ]
