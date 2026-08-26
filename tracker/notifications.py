import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.utils import timezone

from .bootstrap import ADMIN_EMAIL

logger = logging.getLogger(__name__)


def admin_notification_emails():
    emails = list(
        User.objects.filter(is_active=True, is_staff=True)
        .exclude(email='')
        .values_list('email', flat=True)
        .distinct()
    )
    if not emails and ADMIN_EMAIL:
        emails = [ADMIN_EMAIL]
    return emails


def _format_value(value):
    if value in (None, ''):
        return '—'
    return str(value)


def _field_changes(before, after):
    before = before or {}
    after = after or {}
    keys = sorted(set(before) | set(after), key=str.lower)
    changes = []
    for key in keys:
        old = before.get(key, '')
        new = after.get(key, '')
        if _format_value(old) == _format_value(new):
            continue
        changes.append((key, old, new))
    return changes


def notify_admin_record_amended(record, editor, previous_values):
    """Email staff when a non-admin user updates a timesheet record."""
    if editor.is_staff:
        return

    recipients = admin_notification_emails()
    if not recipients:
        logger.warning('No admin email addresses found for amendment notification.')
        return

    values = record.field_values or {}
    ticket_id = values.get('Ticket ID') or record.pk
    assigned = values.get('Assigned') or editor.username
    changes = _field_changes(previous_values, values)
    stamp = timezone.localtime().strftime('%Y-%m-%d %H:%M')

    if changes:
        change_lines = [
            f'- {name}: {_format_value(old)} -> {_format_value(new)}'
            for name, old, new in changes
        ]
        changes_block = '\n'.join(change_lines)
    else:
        changes_block = '- No field value differences detected.'

    subject = f'Timesheet amended: Ticket {ticket_id} by {editor.username}'
    body = (
        f'A timesheet record was amended.\n\n'
        f'When: {stamp}\n'
        f'Edited by: {editor.username}\n'
        f'Record ID: {record.pk}\n'
        f'Ticket ID: {ticket_id}\n'
        f'Assigned: {assigned}\n'
        f'Status: {values.get("Status") or "—"}\n\n'
        f'Changes:\n{changes_block}\n'
    )

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=False,
        )
    except Exception:
        logger.exception('Failed to send timesheet amendment email to %s', recipients)
