from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile

from .models import TimesheetTemplate

DEFAULT_TEMPLATE_NAME = 'Default developer timesheet'
SAMPLE_FILENAME = 'timesheet_template.csv'

DEFAULT_COLUMNS = [
    {'name': 'Ticket ID', 'type': 'number', 'is_resource': False},
    {'name': 'Created On', 'type': 'date', 'is_resource': False},
    {'name': 'Description', 'type': 'text', 'is_resource': False},
    {'name': 'Team', 'type': 'text', 'is_resource': False},
    {'name': 'Status', 'type': 'choice', 'is_resource': False},
    {'name': 'Business User', 'type': 'text', 'is_resource': False},
    {'name': 'Assigned', 'type': 'text', 'is_resource': False},
    {'name': 'Comment', 'type': 'text', 'is_resource': False},
    {'name': 'Transport number', 'type': 'text', 'is_resource': False},
    {'name': 'series number', 'type': 'text', 'is_resource': False},
    {'name': 'Hours spent', 'type': 'hours', 'is_resource': False},
    {'name': 'Completed At', 'type': 'datetime', 'is_resource': False},
]


def ensure_default_timesheet_template():
    template = TimesheetTemplate.objects.filter(is_active=True).first()
    if template is None:
        sample_path = Path(settings.BASE_DIR) / 'static' / 'samples' / SAMPLE_FILENAME
        template = TimesheetTemplate(
            name=DEFAULT_TEMPLATE_NAME,
            columns=DEFAULT_COLUMNS,
            resource_start_index=len(DEFAULT_COLUMNS),
            is_active=True,
        )
        if sample_path.exists():
            template.file.save(SAMPLE_FILENAME, ContentFile(sample_path.read_bytes()), save=False)
        template.save()
        return template

    if template.columns != DEFAULT_COLUMNS:
        template.columns = DEFAULT_COLUMNS
        template.resource_start_index = len(DEFAULT_COLUMNS)
        template.save(update_fields=['columns', 'resource_start_index'])
    return template
