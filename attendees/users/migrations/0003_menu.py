# Generated by Django 3.0.2 on 2020-04-11 15:33

from attendees.persons.models import Utility
from django.db import migrations, models
import django.utils.timezone
import model_utils.fields
import mptt.fields
import pgtrigger.compiler
import pgtrigger.migrations


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
        pgtrigger.migrations.AddTrigger(
            model_name='menu',
            trigger=pgtrigger.compiler.Trigger(name='menu_snapshot_insert', sql=pgtrigger.compiler.UpsertTriggerSql(func='INSERT INTO "users_menushistory" ("id", "created", "modified", "organization_id", "is_removed", "tree_id", "level", "lft", "rght", "display_order", "category", "url_name", "display_name", "infos", "parent_id", "urn", "html_type", "pgh_created_at", "pgh_label", "pgh_obj_id", "pgh_context_id") VALUES (NEW."id", NEW."created", NEW."modified", NEW."organization_id", NEW."is_removed", NEW."tree_id", NEW."level", NEW."lft", NEW."rght", NEW."display_order", NEW."category", NEW."url_name", NEW."display_name", NEW."infos", NEW."parent_id", NEW."urn", NEW."html_type", NOW(), \'menu.snapshot\', NEW."id", _pgh_attach_context()); RETURN NULL;', hash='54c7ce8565cef18c1e0b49411ea66fca35d52764', operation='INSERT', pgid='pgtrigger_menu_snapshot_insert_b8c5e', table='users_menus', when='AFTER')),
        ),
        pgtrigger.migrations.AddTrigger(
            model_name='menu',
            trigger=pgtrigger.compiler.Trigger(name='menu_snapshot_update', sql=pgtrigger.compiler.UpsertTriggerSql(condition='WHEN (OLD."id" IS DISTINCT FROM NEW."id" OR OLD."created" IS DISTINCT FROM NEW."created" OR OLD."modified" IS DISTINCT FROM NEW."modified" OR OLD."organization_id" IS DISTINCT FROM NEW."organization_id" OR OLD."is_removed" IS DISTINCT FROM NEW."is_removed" OR OLD."tree_id" IS DISTINCT FROM NEW."tree_id" OR OLD."level" IS DISTINCT FROM NEW."level" OR OLD."lft" IS DISTINCT FROM NEW."lft" OR OLD."rght" IS DISTINCT FROM NEW."rght" OR OLD."display_order" IS DISTINCT FROM NEW."display_order" OR OLD."category" IS DISTINCT FROM NEW."category" OR OLD."url_name" IS DISTINCT FROM NEW."url_name" OR OLD."display_name" IS DISTINCT FROM NEW."display_name" OR OLD."infos" IS DISTINCT FROM NEW."infos" OR OLD."parent_id" IS DISTINCT FROM NEW."parent_id" OR OLD."urn" IS DISTINCT FROM NEW."urn" OR OLD."html_type" IS DISTINCT FROM NEW."html_type")', func='INSERT INTO "users_menushistory" ("id", "created", "modified", "organization_id", "is_removed", "tree_id", "level", "lft", "rght", "display_order", "category", "url_name", "display_name", "infos", "parent_id", "urn", "html_type", "pgh_created_at", "pgh_label", "pgh_obj_id", "pgh_context_id") VALUES (NEW."id", NEW."created", NEW."modified", NEW."organization_id", NEW."is_removed", NEW."tree_id", NEW."level", NEW."lft", NEW."rght", NEW."display_order", NEW."category", NEW."url_name", NEW."display_name", NEW."infos", NEW."parent_id", NEW."urn", NEW."html_type", NOW(), \'menu.snapshot\', NEW."id", _pgh_attach_context()); RETURN NULL;', hash='9fe282e3c7ae64164ad00584033a3212b9423c60', operation='UPDATE', pgid='pgtrigger_menu_snapshot_update_182ff', table='users_menus', when='AFTER')),
        ),
        pgtrigger.migrations.AddTrigger(
            model_name='menu',
            trigger=pgtrigger.compiler.Trigger(name='menu_before_delete', sql=pgtrigger.compiler.UpsertTriggerSql(func='INSERT INTO "users_menushistory" ("id", "created", "modified", "organization_id", "is_removed", "tree_id", "level", "lft", "rght", "display_order", "category", "url_name", "display_name", "infos", "parent_id", "urn", "html_type", "pgh_created_at", "pgh_label", "pgh_obj_id", "pgh_context_id") VALUES (OLD."id", OLD."created", OLD."modified", OLD."organization_id", OLD."is_removed", OLD."tree_id", OLD."level", OLD."lft", OLD."rght", OLD."display_order", OLD."category", OLD."url_name", OLD."display_name", OLD."infos", OLD."parent_id", OLD."urn", OLD."html_type", NOW(), \'menu.before_delete\', OLD."id", _pgh_attach_context()); RETURN NULL;', hash='a5fbe579ddbb67e26ef4ef0691e4b069d4bbd94f', operation='DELETE', pgid='pgtrigger_menu_before_delete_e54e6', table='users_menus', when='AFTER')),
        ),
    ]
