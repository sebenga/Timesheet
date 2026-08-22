from django.db import migrations, models


def freeze_existing_complete_records(apps, schema_editor):
    TimesheetRecord = apps.get_model('tracker', 'TimesheetRecord')
    TimeMarginSettings = apps.get_model('tracker', 'TimeMarginSettings')
    settings, _created = TimeMarginSettings.objects.get_or_create(pk=1)
    for record in TimesheetRecord.objects.all():
        values = record.field_values or {}
        if values.get('Status') != 'COMPLETE':
            continue
        record.sd_margin = settings.sd_margin
        record.atisa_margin = settings.atisa_margin
        record.save(update_fields=['sd_margin', 'atisa_margin'])


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0003_timemarginsettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='timesheetrecord',
            name='atisa_margin',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='ATISA margin (%) frozen when this record was marked COMPLETE.',
                max_digits=6,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='timesheetrecord',
            name='sd_margin',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='SD margin (%) frozen when this record was marked COMPLETE.',
                max_digits=6,
                null=True,
            ),
        ),
        migrations.RunPython(freeze_existing_complete_records, migrations.RunPython.noop),
    ]
