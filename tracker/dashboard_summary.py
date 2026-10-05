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


def round_hours(value):
    """Round hour amounts to one decimal place (nearest tenth)."""
    return _to_decimal(value).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)


def round_whole_hours(value):
    """Round hours to a whole number: .5 and above up, below .5 down."""
    return _to_decimal(value).quantize(Decimal('1'), rounding=ROUND_HALF_UP)


def format_hours(value):
    amount = round_hours(value)
    if amount == amount.to_integral_value():
        return str(int(amount))
    return format(amount, 'f')


def margin_hours_only(hours, percent, rounder=round_nearest_decimal):
    """Margin portion only: hours spent × margin %."""
    total = _to_decimal(hours)
    rate = _to_decimal(percent) / Decimal('100')
    return rounder(total * rate)


def apply_atisa_total(hours, atisa_percent, rounder=round_nearest_decimal):
    """Hours spent + ATISA margin (as % of hours spent)."""
    total = _to_decimal(hours)
    atisa_rate = _to_decimal(atisa_percent) / Decimal('100')
    return rounder(total + (total * atisa_rate))


def _format_percent(percent):
    amount = round_nearest_decimal(percent)
    if amount == amount.to_integral_value():
        return str(int(amount))
    return format(amount, 'f').rstrip('0').rstrip('.')


def format_margin_display(hours, percents):
    hours_text = f'{format_hours(hours)}h'
    unique = sorted({round_nearest_decimal(value) for value in percents})
    if not unique:
        return f'{hours_text} @ 0%'
    percent_text = '/'.join(_format_percent(value) for value in unique)
    return f'{hours_text} @ {percent_text}%'


def _margins_for_record(record):
    if record.atisa_margin is not None:
        return record.atisa_margin
    return Decimal('0')


def _row_matches_query(row, users, query):
    needle = (query or '').strip().lower()
    if not needle:
        return True
    parts = [str(value) for value in row['details'].values() if value not in (None, '')]
    parts.append(str(row['total_hours']))
    parts.append(str(row.get('atisa_margin_display', '')))
    parts.append(str(row['atisa_total_decimal']))
    for user in users:
        parts.append(user)
        parts.append(str(row['user_hours'].get(user, '')))
    return needle in ' '.join(parts).lower()


def build_completed_month_summary(start=None, end=None, query=''):
    month_start, month_end = current_month_range()
    start = start or month_start
    end = end or month_end
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
        atisa_margin = _margins_for_record(record)

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
                'atisa_margin_hours': Decimal('0'),
                'atisa_margin_percents': set(),
            }
            grouped[ticket_key] = row
        else:
            for name in DETAIL_COLUMNS:
                if not row['details'].get(name) and values.get(name):
                    row['details'][name] = values.get(name)

        row['user_hours'][assigned] = row['user_hours'].get(assigned, Decimal('0')) + hours
        row['total_hours'] += hours
        row['atisa_total'] += apply_atisa_total(hours, atisa_margin, round_nearest_10)
        row['atisa_total_decimal'] += apply_atisa_total(hours, atisa_margin)
        row['atisa_margin_hours'] += margin_hours_only(hours, atisa_margin)
        row['atisa_margin_percents'].add(_to_decimal(atisa_margin))

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

    for row in grouped.values():
        user_hours = {
            user: round_hours(row['user_hours'].get(user, Decimal('0')))
            for user in users
        }
        row['details']['Assigned'] = ', '.join(
            user for user in users if user_hours[user] > 0
        )
        atisa_margin_hours = round_whole_hours(row['atisa_margin_hours'])
        prepared = {
            'details': row['details'],
            'user_hours': user_hours,
            'total_hours': round_hours(row['total_hours']),
            'atisa_total': round_whole_hours(row['atisa_total']),
            'atisa_total_decimal': round_whole_hours(row['atisa_total_decimal']),
            'atisa_margin_hours': atisa_margin_hours,
            'atisa_margin_percents': set(row['atisa_margin_percents']),
            'atisa_margin_display': format_margin_display(
                atisa_margin_hours, row['atisa_margin_percents'],
            ),
        }
        if _row_matches_query(prepared, users, query):
            rows.append(prepared)

    totals = {
        'total_hours': Decimal('0'),
        'user_hours': {user: Decimal('0') for user in users},
        'atisa_total': Decimal('0'),
        'atisa_total_decimal': Decimal('0'),
        'atisa_margin_hours': Decimal('0'),
        'atisa_margin_percents': set(),
    }
    for row in rows:
        totals['total_hours'] += row['total_hours']
        totals['atisa_total'] += row['atisa_total']
        totals['atisa_total_decimal'] += row['atisa_total_decimal']
        totals['atisa_margin_hours'] += row['atisa_margin_hours']
        totals['atisa_margin_percents'].update(row['atisa_margin_percents'])
        for user in users:
            totals['user_hours'][user] += row['user_hours'][user]

    totals['atisa_margin_hours'] = round_whole_hours(totals['atisa_margin_hours'])
    totals['total_hours'] = round_hours(totals['total_hours'])
    totals['atisa_total'] = round_whole_hours(totals['atisa_total'])
    totals['atisa_total_decimal'] = round_whole_hours(totals['atisa_total_decimal'])
    totals['user_hours'] = {
        user: round_hours(hours) for user, hours in totals['user_hours'].items()
    }
    totals['atisa_margin_display'] = format_margin_display(
        totals['atisa_margin_hours'], totals['atisa_margin_percents'],
    )

    return {
        'start': start,
        'end': end,
        'users': users,
        'rows': rows,
        'totals': totals,
        'detail_columns': DETAIL_COLUMNS,
        'admin_username': ADMIN_USERNAME,
        'query': query,
    }
