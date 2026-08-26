from collections import OrderedDict
from decimal import Decimal, ROUND_HALF_UP

from .bootstrap import ADMIN_USERNAME, LEGACY_ADMIN_USERNAME
from .models import TimesheetRecord
from .timesheet_defaults import DEFAULT_COLUMNS
from .timesheet_query import current_month_range, filter_timesheet_records

HIDDEN_DETAIL_COLUMNS = {
    'Hours spent',
    'Transport number',
    'series number',
    'Comment',
}

DETAIL_COLUMNS = [
    column['name']
    for column in DEFAULT_COLUMNS
    if column['name'] not in HIDDEN_DETAIL_COLUMNS
]


def _to_decimal(value):
    if value in (None, ''):
        return Decimal('0')
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal('0')


def round_nearest_10(value):
    amount = _to_decimal(value)
    return (amount / Decimal('10')).quantize(Decimal('1'), rounding=ROUND_HALF_UP) * Decimal('10')


def round_nearest_decimal(value):
    return _to_decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def apply_margin(total_hours, percent, rounder=round_nearest_10):
    total = _to_decimal(total_hours)
    rate = _to_decimal(percent) / Decimal('100')
    return rounder(total + (total * rate))


def apply_user_plus_sd_percent(user_hours, total_hours, percent, rounder=round_nearest_10):
    user = _to_decimal(user_hours)
    total = _to_decimal(total_hours)
    rate = _to_decimal(percent) / Decimal('100')
    return rounder(user + (total * rate))


def _margins_for_record(record):
    sd = record.sd_margin if record.sd_margin is not None else Decimal('0')
    atisa = record.atisa_margin if record.atisa_margin is not None else Decimal('0')
    return sd, atisa


def build_completed_month_summary():
    start, end = current_month_range()
    records = filter_timesheet_records(
        TimesheetRecord.objects.select_related('template'),
        start,
        end,
        'COMPLETE',
    ).order_by('created_at')

    grouped = OrderedDict()
    users = []

    for record in records:
        values = record.field_values or {}
        ticket_id = values.get('Ticket ID')
        if ticket_id in (None, ''):
            continue
        ticket_key = str(ticket_id)
        assigned = (values.get('Assigned') or 'Unassigned').strip() or 'Unassigned'
        hours = _to_decimal(values.get('Hours spent'))
        sd_margin, atisa_margin = _margins_for_record(record)

        if assigned not in users:
            users.append(assigned)

        row = grouped.get(ticket_key)
        if row is None:
            row = {
                'ticket_id': ticket_key,
                'details': {name: values.get(name, '') for name in DETAIL_COLUMNS},
                'user_hours': {},
                'total_hours': Decimal('0'),
                'atisa_total': Decimal('0'),
                'atisa_total_decimal': Decimal('0'),
                'sd_total': Decimal('0'),
                'admin_sd_total': Decimal('0'),
                'admin_sd_total_decimal': Decimal('0'),
            }
            grouped[ticket_key] = row
        else:
            for name in DETAIL_COLUMNS:
                if not row['details'].get(name) and values.get(name):
                    row['details'][name] = values.get(name)

        row['user_hours'][assigned] = row['user_hours'].get(assigned, Decimal('0')) + hours
        row['total_hours'] += hours
        row['atisa_total'] += apply_margin(hours, atisa_margin)
        row['atisa_total_decimal'] += apply_margin(hours, atisa_margin, round_nearest_decimal)
        row['sd_total'] += apply_margin(hours, sd_margin)

        assigned_key = assigned
        if assigned_key == LEGACY_ADMIN_USERNAME:
            assigned_key = ADMIN_USERNAME
        admin_hours = hours if assigned_key == ADMIN_USERNAME else Decimal('0')
        row['admin_sd_total'] += apply_user_plus_sd_percent(admin_hours, hours, sd_margin)
        row['admin_sd_total_decimal'] += apply_user_plus_sd_percent(
            admin_hours, hours, sd_margin, round_nearest_decimal,
        )

    for row in grouped.values():
        legacy_hours = row['user_hours'].pop(LEGACY_ADMIN_USERNAME, Decimal('0'))
        if legacy_hours:
            row['user_hours'][ADMIN_USERNAME] = (
                row['user_hours'].get(ADMIN_USERNAME, Decimal('0')) + legacy_hours
            )

    users = sorted(
        {user for row in grouped.values() for user in row['user_hours']},
        key=str.lower,
    )
    rows = []
    totals = {
        'total_hours': Decimal('0'),
        'user_hours': {user: Decimal('0') for user in users},
        'atisa_total': Decimal('0'),
        'sd_total': Decimal('0'),
        'admin_sd_total': Decimal('0'),
        'atisa_total_decimal': Decimal('0'),
        'admin_sd_total_decimal': Decimal('0'),
    }

    for row in grouped.values():
        user_hours = {user: row['user_hours'].get(user, Decimal('0')) for user in users}
        row['details']['Assigned'] = ', '.join(
            user for user in users if user_hours[user] > 0
        )
        rows.append({
            'details': row['details'],
            'user_hours': user_hours,
            'total_hours': row['total_hours'],
            'atisa_total': row['atisa_total'],
            'atisa_total_decimal': row['atisa_total_decimal'],
            'sd_total': row['sd_total'],
            'admin_sd_total': row['admin_sd_total'],
            'admin_sd_total_decimal': row['admin_sd_total_decimal'],
        })
        totals['total_hours'] += row['total_hours']
        totals['atisa_total'] += row['atisa_total']
        totals['atisa_total_decimal'] += row['atisa_total_decimal']
        totals['sd_total'] += row['sd_total']
        totals['admin_sd_total'] += row['admin_sd_total']
        totals['admin_sd_total_decimal'] += row['admin_sd_total_decimal']
        for user in users:
            totals['user_hours'][user] += user_hours[user]

    return {
        'start': start,
        'end': end,
        'users': users,
        'rows': rows,
        'totals': totals,
        'detail_columns': DETAIL_COLUMNS,
        'admin_username': ADMIN_USERNAME,
    }
