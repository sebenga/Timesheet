from io import BytesIO
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_not_required, user_passes_test
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from openpyxl import Workbook

from .dashboard_summary import build_completed_month_summary
from .forms import (
    CreateUserForm,
    EditUserForm,
    FirstLoginPasswordForm,
    LoginForm,
    ProjectForm,
    TimeEntryForm,
    TimesheetFilterForm,
    build_timesheet_form,
)
from .models import TimesheetRecord, TimesheetTemplate, UserProfile
from .notifications import notify_admin_record_amended
from .timesheet_defaults import ensure_default_timesheet_template
from .timesheet_query import current_month_range, filter_timesheet_records


def staff_required(view):
    return user_passes_test(
        lambda user: user.is_authenticated and user.is_staff,
        login_url='login',
    )(view)


def home_for(user):
    profile = UserProfile.for_user(user)
    if profile.must_change_password:
        return 'change_password'
    return 'dashboard' if user.is_staff else 'timesheets'


@login_not_required
def login_view(request):
    if request.user.is_authenticated:
        return redirect(home_for(request.user))

    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password'],
        )
        if user is None:
            messages.error(request, 'Invalid username or password.')
        else:
            login(request, user)
            return redirect(home_for(user))

    return render(request, 'tracker/login.html', {'form': form})


@require_POST
def logout_view(request):
    logout(request)
    return redirect('login')


def change_password(request):
    profile = UserProfile.for_user(request.user)
    form = FirstLoginPasswordForm(request.POST or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        request.user.set_password(form.cleaned_data['new_password'])
        request.user.save()
        profile.must_change_password = False
        profile.save(update_fields=['must_change_password'])
        update_session_auth_hash(request, request.user)
        messages.success(request, 'Your password has been updated.')
        return redirect('dashboard' if request.user.is_staff else 'timesheets')

    return render(request, 'tracker/change_password.html', {
        'form': form,
        'forced': profile.must_change_password,
    })


@staff_required
def admin_console(request):
    users = User.objects.order_by('-is_staff', 'username')
    return render(request, 'tracker/admin_console.html', {
        'users': users,
        'create_user_form': CreateUserForm(),
        'edit_user_form': EditUserForm(auto_id='id_edit_%s'),
    })


@staff_required
@require_POST
def create_user(request):
    form = CreateUserForm(request.POST)
    if not form.is_valid():
        messages.error(request, form.errors.as_text())
        return redirect('admin_console')

    account = User.objects.create_user(
        username=form.cleaned_data['username'],
        email=form.cleaned_data['email'],
        password=form.cleaned_data['password'],
        is_staff=False,
        is_superuser=False,
    )
    profile = UserProfile.for_user(account)
    profile.must_change_password = True
    profile.save(update_fields=['must_change_password'])
    messages.success(
        request,
        f'Account created for {account.username}. They must set a new password on first login.',
    )
    return redirect('admin_console')


@staff_required
@require_POST
def edit_user(request, pk):
    account = get_object_or_404(User, pk=pk)
    form = EditUserForm(request.POST, user=account)
    if not form.is_valid():
        messages.error(request, form.errors.as_text())
        return redirect('admin_console')

    old_username = account.username
    new_username = form.cleaned_data['username']
    account.username = new_username
    account.email = form.cleaned_data['email']
    password_reset = bool(form.cleaned_data.get('password'))
    if password_reset:
        account.set_password(form.cleaned_data['password'])
    account.save()

    if password_reset:
        profile = UserProfile.for_user(account)
        profile.must_change_password = True
        profile.save(update_fields=['must_change_password'])

    if old_username != new_username:
        for record in TimesheetRecord.objects.all():
            values = record.field_values or {}
            if values.get('Assigned') != old_username:
                continue
            values['Assigned'] = new_username
            record.field_values = values
            record.save(update_fields=['field_values'])

    if password_reset:
        messages.success(
            request,
            f'Profile updated for {account.username}. They must set a new password on next login.',
        )
    else:
        messages.success(request, f'Profile updated for {account.username}.')
    return redirect('admin_console')


@staff_required
@require_POST
def delete_user(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, 'You cannot delete your own admin account.')
        return redirect('admin_console')
    if user.is_superuser:
        messages.error(request, 'The primary admin account cannot be deleted.')
        return redirect('admin_console')

    username = user.username
    user.delete()
    messages.success(request, f'User "{username}" deleted.')
    return redirect('admin_console')


@staff_required
def dashboard(request):
    summary = build_completed_month_summary()
    return render(request, 'tracker/dashboard.html', summary)


@staff_required
@require_GET
def export_dashboard_excel(request):
    summary = build_completed_month_summary()
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Completed timesheets'

    headers = list(summary['detail_columns']) + ['Hours spent']
    headers += [f'{user} hours' for user in summary['users']]
    headers += [
        'ATISA Total Hours',
        f'{summary["admin_username"]} Total Hours',
    ]
    sheet.append(headers)

    for row in summary['rows']:
        values = [row['details'].get(name, '') or '' for name in summary['detail_columns']]
        values.append(float(row['total_hours']))
        values.extend(float(row['user_hours'][user]) for user in summary['users'])
        values.append(float(row['atisa_total_decimal']))
        values.append(float(row['admin_sd_total_decimal']))
        sheet.append(values)

    totals = summary['totals']
    footer = ['Totals'] + [''] * (len(summary['detail_columns']) - 1)
    footer.append(float(totals['total_hours']))
    footer.extend(float(totals['user_hours'][user]) for user in summary['users'])
    footer.append(float(totals['atisa_total_decimal']))
    footer.append(float(totals['admin_sd_total_decimal']))
    sheet.append(footer)

    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    filename = f'completed-timesheets-{summary["start"]}-to-{summary["end"]}.xlsx'
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def _completion_stamp():
    return timezone.localtime().strftime('%Y-%m-%d %H:%M')


def _timesheet_field_values(template, form, assigned_username, previous=None):
    previous = previous or {}
    field_values = {}
    for column in template.columns:
        name = column['name']
        key = name.lower()
        if key == 'assigned':
            field_values[name] = assigned_username
            continue
        if key == 'completed at':
            continue
        value = form.cleaned_data.get(name)
        if value is None or value == '':
            continue
        if column['type'] == 'date':
            field_values[name] = value.isoformat()
        elif column['type'] in {'hours', 'number'}:
            field_values[name] = str(value)
        else:
            field_values[name] = value

    if field_values.get('Status') == 'COMPLETE':
        field_values['Completed At'] = previous.get('Completed At') or _completion_stamp()
    elif previous.get('Status') == 'COMPLETE' and not field_values.get('Status'):
        field_values['Status'] = 'COMPLETE'
        field_values['Completed At'] = previous.get('Completed At') or _completion_stamp()
    return field_values


def _user_can_manage_record(user, record):
    if user.is_staff:
        return True
    return (record.field_values or {}).get('Assigned') == user.username


def _guard_complete_status(user, form, previous=None):
    previous = previous or {}
    if user.is_staff:
        return None
    if form.cleaned_data.get('Status') != 'COMPLETE':
        return None
    if previous.get('Status') == 'COMPLETE':
        return None
    return 'Only an administrator can mark a timesheet as COMPLETE.'


def _parse_margin_percent(raw):
    if raw is None:
        return None
    text = str(raw).strip()
    if text == '':
        return None
    try:
        value = Decimal(text)
    except (InvalidOperation, ValueError):
        return False
    if value < 0 or value > 100:
        return False
    return value.quantize(Decimal('0.01'))


def _apply_record_margins(request, record, previous=None):
    """Require ATISA/SD margins when Status becomes COMPLETE; clear when not COMPLETE."""
    previous = previous or {}
    values = record.field_values or {}
    status = values.get('Status')
    if status != 'COMPLETE':
        record.apply_completion_margins()
        return None

    becoming_complete = previous.get('Status') != 'COMPLETE'
    if not becoming_complete:
        return None

    sd_margin = _parse_margin_percent(request.POST.get('sd_margin'))
    atisa_margin = _parse_margin_percent(request.POST.get('atisa_margin'))
    if sd_margin in (None, False) or atisa_margin in (None, False):
        return 'Enter ATISA and SD time margins (0–100%) when marking a timesheet COMPLETE.'

    record.apply_completion_margins(sd_margin=sd_margin, atisa_margin=atisa_margin)
    return None


def timesheets(request):
    template = ensure_default_timesheet_template()
    month_start, month_end = current_month_range()
    filter_form = TimesheetFilterForm(request.GET or None)

    start = month_start
    end = month_end
    status = ''
    using_custom_range = False

    if filter_form.is_valid():
        if filter_form.cleaned_data.get('start'):
            start = filter_form.cleaned_data['start']
            using_custom_range = True
        if filter_form.cleaned_data.get('end'):
            end = filter_form.cleaned_data['end']
            using_custom_range = True
        status = filter_form.cleaned_data.get('status') or ''

    if start and end and start > end:
        start, end = end, start

    if not filter_form.is_bound:
        filter_form = TimesheetFilterForm(initial={
            'start': month_start,
            'end': month_end,
        })

    records = TimesheetRecord.objects.none()
    if template:
        records = filter_timesheet_records(
            TimesheetRecord.objects.select_related('template'),
            start,
            end,
            status,
        )
        if not request.user.is_staff:
            records = records.filter(field_values__Assigned=request.user.username)

    timesheet_form = None
    edit_form = None
    data_fields = []
    edit_fields = []
    if template:
        form_class = build_timesheet_form(template, allow_complete=request.user.is_staff)
        timesheet_form = form_class(initial={'Assigned': request.user.username})
        edit_form_class = build_timesheet_form(template, allow_complete=True)
        edit_form = edit_form_class(auto_id='id_edit_%s')
        data_fields = [
            (column, timesheet_form[column['name']])
            for column in template.data_columns
            if column['name'].lower() != 'completed at'
        ]
        edit_fields = [
            (column, edit_form[column['name']])
            for column in template.data_columns
            if column['name'].lower() != 'completed at'
        ]

    return render(request, 'tracker/timesheets.html', {
        'template': template,
        'records': records,
        'timesheet_form': timesheet_form,
        'edit_form': edit_form,
        'data_fields': data_fields,
        'edit_fields': edit_fields,
        'filter_form': filter_form,
        'using_custom_range': using_custom_range,
        'filter_status': status,
    })


@require_POST
def submit_timesheet(request):
    template = get_object_or_404(TimesheetTemplate, pk=request.POST.get('template_id'), is_active=True)
    form_class = build_timesheet_form(template, allow_complete=request.user.is_staff)
    form = form_class(request.POST)

    if not form.is_valid():
        messages.error(request, 'Fix the highlighted fields and try again.')
        return redirect('timesheets')

    blocked = _guard_complete_status(request.user, form)
    if blocked:
        messages.error(request, blocked)
        return redirect('timesheets')

    field_values = _timesheet_field_values(template, form, request.user.username)
    record = TimesheetRecord(template=template, field_values=field_values)
    margin_error = _apply_record_margins(request, record)
    if margin_error:
        messages.error(request, margin_error)
        return redirect('timesheets')
    record.save()
    messages.success(request, 'Timesheet entry saved.')
    return redirect('timesheets')


@require_POST
def edit_timesheet(request, pk):
    record = get_object_or_404(TimesheetRecord, pk=pk)
    if not _user_can_manage_record(request.user, record):
        return HttpResponseForbidden('You can only edit your own timesheet entries.')
    form_class = build_timesheet_form(record.template, allow_complete=True)
    form = form_class(request.POST)

    if not form.is_valid():
        messages.error(request, 'Fix the highlighted fields and try again.')
        return redirect('timesheets')

    previous = record.field_values or {}
    blocked = _guard_complete_status(request.user, form, previous=previous)
    if blocked:
        messages.error(request, blocked)
        return redirect('timesheets')

    assigned = previous.get('Assigned') or request.user.username
    if not request.user.is_staff:
        assigned = request.user.username
    record.field_values = _timesheet_field_values(
        record.template, form, assigned, previous=previous,
    )
    margin_error = _apply_record_margins(request, record, previous=previous)
    if margin_error:
        messages.error(request, margin_error)
        return redirect('timesheets')
    record.save(update_fields=['field_values', 'sd_margin', 'atisa_margin'])
    notify_admin_record_amended(record, request.user, previous)
    messages.success(request, 'Timesheet entry updated.')
    return redirect('timesheets')


@require_POST
def delete_timesheet_record(request, pk):
    record = get_object_or_404(TimesheetRecord, pk=pk)
    if not _user_can_manage_record(request.user, record):
        return HttpResponseForbidden('You can only delete your own timesheet entries.')
    record.delete()
    messages.success(request, 'Timesheet entry deleted.')
    return redirect('timesheets')


@staff_required
@require_POST
def add_entry(request):
    form = TimeEntryForm(request.POST)
    if form.is_valid():
        form.save()
    return redirect('dashboard')


@staff_required
@require_POST
def add_project(request):
    form = ProjectForm(request.POST)
    if form.is_valid():
        form.save()
    return redirect('dashboard')


@staff_required
@require_POST
def delete_entry(request, pk):
    entry = get_object_or_404(TimeEntry, pk=pk)
    entry.delete()
    return redirect('dashboard')
