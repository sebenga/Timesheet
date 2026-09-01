from calendar import monthrange

from django.db.models import TextField
from django.db.models.functions import Cast
from django.utils import timezone


def current_month_range():
    today = timezone.localdate()
    start = today.replace(day=1)
    last_day = monthrange(today.year, today.month)[1]
    end = today.replace(day=last_day)
    return start, end


def parse_range_filters(form, month_start, month_end):
    start = month_start
    end = month_end
    query = ''
    status = ''
    using_custom_range = False

    if form.is_valid():
        if form.cleaned_data.get('start'):
            start = form.cleaned_data['start']
            using_custom_range = True
        if form.cleaned_data.get('end'):
            end = form.cleaned_data['end']
            using_custom_range = True
        query = (form.cleaned_data.get('q') or '').strip()
        if 'status' in form.fields:
            status = form.cleaned_data.get('status') or ''

    if start and end and start > end:
        start, end = end, start

    return start, end, query, status, using_custom_range


def filter_timesheet_records(queryset, start, end, status, query=''):
    if start:
        queryset = queryset.filter(created_at__date__gte=start)
    if end:
        queryset = queryset.filter(created_at__date__lte=end)
    if status:
        queryset = queryset.filter(field_values__Status=status)
    query = (query or '').strip()
    if query:
        queryset = queryset.annotate(
            _values_text=Cast('field_values', TextField()),
        ).filter(_values_text__icontains=query)
    return queryset
