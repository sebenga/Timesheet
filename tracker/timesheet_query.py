from calendar import monthrange

from django.utils import timezone


def current_month_range():
    today = timezone.localdate()
    start = today.replace(day=1)
    last_day = monthrange(today.year, today.month)[1]
    end = today.replace(day=last_day)
    return start, end


def filter_timesheet_records(queryset, start, end, status):
    if start:
        queryset = queryset.filter(created_at__date__gte=start)
    if end:
        queryset = queryset.filter(created_at__date__lte=end)
    if status:
        queryset = queryset.filter(field_values__Status=status)
    return queryset
