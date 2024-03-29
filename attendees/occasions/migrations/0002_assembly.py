# Generated by Django 3.0.2 on 2020-01-13 14:49

from attendees.persons.models.utility import Utility
from django.db import migrations, models
from django.contrib.postgres.indexes import GinIndex
import pgtrigger.compiler
import pgtrigger.migrations
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('occasions', '0001_message_template'),
    ]

    operations = [
        migrations.CreateModel(
            name='Assembly',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('start', models.DateTimeField(blank=True, help_text='optional', null=True)),
                ('finish', models.DateTimeField(blank=True, help_text='optional', null=True)),
                ('is_removed', models.BooleanField(default=False)),
                ('display_order', models.SmallIntegerField(blank=False, default=0, null=False)),
                ('division', models.ForeignKey(on_delete=models.SET(0), to='whereabouts.Division')),
                ('category', models.ForeignKey(help_text='normal, no-display, etc', default=33, on_delete=models.deletion.DO_NOTHING, to='persons.Category')),
                ('infos', models.JSONField(blank=True, default=dict, help_text='example: {"need_age": 18}, please keep {} here even there\'s no data', null=True)),
                ('slug', models.SlugField(max_length=50, unique=True, help_text='format: Organization_name-Assembly_name')),
                ('display_name', models.CharField(max_length=50, blank=False, null=False, help_text='Uniq within Organization, adding year helps')),
            ],
            options={
                'db_table': 'occasions_assemblies',
                'verbose_name_plural': 'Assemblies',
                'ordering': ('division', 'display_order'),
            },
            bases=(models.Model, Utility),
        ),
        migrations.RunSQL(Utility.default_sql('occasions_assemblies')),
        migrations.AddIndex(
            model_name='Assembly',
            index=GinIndex(fields=['infos'], name='assembly_infos_gin'),
        ),
        migrations.CreateModel(
            name='AssembliesHistory',
            fields=[
                ('pgh_id', models.BigAutoField(primary_key=True, serialize=False)),
                ('pgh_created_at', models.DateTimeField(auto_now_add=True)),
                ('pgh_label', models.TextField(help_text='The event label.')),
                ('pgh_obj', models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='history', to='occasions.assembly')),
                ('id', models.BigIntegerField(db_index=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('is_removed', models.BooleanField(default=False)),
                ('division', models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='whereabouts.division')),
                ('display_order', models.SmallIntegerField(default=0)),
                ('infos', models.JSONField(blank=True, default=dict, help_text='example: {"need_age": 18}, please keep {} here even there\'s no data', null=True)),
                ('category', models.ForeignKey(db_constraint=False, default=33, help_text='normal, no-display, etc', on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='persons.category')),
                ('slug', models.SlugField(db_index=False, help_text='format: Organization_name-Assembly_name')),
                ('display_name', models.CharField(help_text='Uniq within Organization, adding year helps', max_length=50)),
                ('start', models.DateTimeField(blank=True, help_text='optional', null=True)),
                ('finish', models.DateTimeField(blank=True, help_text='optional', null=True)),
                ('pgh_context', models.ForeignKey(db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')),
            ],
            options={
                'db_table': 'occasions_assemblieshistory',
            },
        ),
        migrations.RunSQL(Utility.pgh_default_sql('occasions_assemblieshistory', original_model_table='occasions_assemblies')),
        pgtrigger.migrations.AddTrigger(
            model_name='assembly',
            trigger=pgtrigger.compiler.Trigger(name='assembly_snapshot_insert', sql=pgtrigger.compiler.UpsertTriggerSql(func='INSERT INTO "occasions_assemblieshistory" ("id", "created", "modified", "is_removed", "division_id", "display_order", "infos", "slug", "category_id", "display_name", "start", "finish", "pgh_created_at", "pgh_label", "pgh_obj_id", "pgh_context_id") VALUES (NEW."id", NEW."created", NEW."modified", NEW."is_removed", NEW."division_id", NEW."display_order", NEW."infos", NEW."slug", NEW."category_id", NEW."display_name", NEW."start", NEW."finish", NOW(), \'assembly.snapshot\', NEW."id", _pgh_attach_context()); RETURN NULL;', hash='dbf4c983c2a753d459d6866ffa0e67bcb2a55ab9', operation='INSERT', pgid='pgtrigger_assembly_snapshot_insert_13c43', table='occasions_assemblies', when='AFTER')),
        ),
        pgtrigger.migrations.AddTrigger(
            model_name='assembly',
            trigger=pgtrigger.compiler.Trigger(name='assembly_snapshot_update', sql=pgtrigger.compiler.UpsertTriggerSql(condition='WHEN (OLD."id" IS DISTINCT FROM NEW."id" OR OLD."created" IS DISTINCT FROM NEW."created" OR OLD."modified" IS DISTINCT FROM NEW."modified" OR OLD."is_removed" IS DISTINCT FROM NEW."is_removed" OR OLD."division_id" IS DISTINCT FROM NEW."division_id" OR OLD."display_order" IS DISTINCT FROM NEW."display_order" OR OLD."infos" IS DISTINCT FROM NEW."infos" OR OLD."slug" IS DISTINCT FROM NEW."slug" OR OLD."category_id" IS DISTINCT FROM NEW."category_id" OR OLD."display_name" IS DISTINCT FROM NEW."display_name" OR OLD."start" IS DISTINCT FROM NEW."start" OR OLD."finish" IS DISTINCT FROM NEW."finish")', func='INSERT INTO "occasions_assemblieshistory" ("id", "created", "modified", "is_removed", "division_id", "display_order", "infos", "slug", "category_id", "display_name", "start", "finish", "pgh_created_at", "pgh_label", "pgh_obj_id", "pgh_context_id") VALUES (NEW."id", NEW."created", NEW."modified", NEW."is_removed", NEW."division_id", NEW."display_order", NEW."infos", NEW."slug", NEW."category_id", NEW."display_name", NEW."start", NEW."finish", NOW(), \'assembly.snapshot\', NEW."id", _pgh_attach_context()); RETURN NULL;', hash='6bfc83a180fdb8db47e6158eb9ad7de068a415b5', operation='UPDATE', pgid='pgtrigger_assembly_snapshot_update_44c79', table='occasions_assemblies', when='AFTER')),
        ),
        pgtrigger.migrations.AddTrigger(
            model_name='assembly',
            trigger=pgtrigger.compiler.Trigger(name='assembly_before_delete', sql=pgtrigger.compiler.UpsertTriggerSql(func='INSERT INTO "occasions_assemblieshistory" ("id", "created", "modified", "is_removed", "division_id", "display_order", "infos", "slug", "category_id", "display_name", "start", "finish", "pgh_created_at", "pgh_label", "pgh_obj_id", "pgh_context_id") VALUES (OLD."id", OLD."created", OLD."modified", OLD."is_removed", OLD."division_id", OLD."display_order", OLD."infos", OLD."slug", OLD."category_id", OLD."display_name", OLD."start", OLD."finish", NOW(), \'assembly.before_delete\', OLD."id", _pgh_attach_context()); RETURN NULL;', hash='9a9e892d0165699e210601da2f4d03c3f20c5aeb', operation='DELETE', pgid='pgtrigger_assembly_before_delete_fd52c', table='occasions_assemblies', when='AFTER')),
        ),
    ]
