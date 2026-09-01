from decimal import Decimal

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

from .models import Project, TimeEntry, TimeMarginSettings


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'color']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Project name'}),
            'color': forms.TextInput(attrs={'type': 'color'}),
        }


class TimeEntryForm(forms.ModelForm):
    class Meta:
        model = TimeEntry
        fields = ['project', 'task', 'date', 'hours', 'notes']
        widgets = {
            'task': forms.TextInput(attrs={'placeholder': 'What did you work on?'}),
            'date': forms.DateInput(attrs={'type': 'date'}),
            'hours': forms.NumberInput(attrs={'step': '0.25', 'min': '0.25', 'placeholder': 'Hours'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional notes'}),
        }


class LoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Username', 'autofocus': True}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password'}),
    )


class FirstLoginPasswordForm(forms.Form):
    new_password = forms.CharField(
        label='New password',
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Choose a new password',
            'autocomplete': 'new-password',
            'autofocus': True,
        }),
    )
    confirm_password = forms.CharField(
        label='Confirm new password',
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Confirm new password',
            'autocomplete': 'new-password',
        }),
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_new_password(self):
        password = self.cleaned_data['new_password']
        validate_password(password, user=self.user)
        return password

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get('new_password')
        confirm = cleaned.get('confirm_password')
        if password and confirm and password != confirm:
            self.add_error('confirm_password', 'Passwords do not match.')
        return cleaned


class CreateUserForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Username'}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'Email address'}),
    )
    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={'placeholder': 'Password'}),
    )

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('That username is already in use.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('That email address is already in use.')
        return email


class EditUserForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Username'}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'Email address'}),
    )
    password = forms.CharField(
        required=False,
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Leave blank to keep current password',
            'autocomplete': 'new-password',
        }),
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        query = User.objects.filter(username__iexact=username)
        if self.user:
            query = query.exclude(pk=self.user.pk)
        if query.exists():
            raise forms.ValidationError('That username is already in use.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip()
        query = User.objects.filter(email__iexact=email)
        if self.user:
            query = query.exclude(pk=self.user.pk)
        if query.exists():
            raise forms.ValidationError('That email address is already in use.')
        return email


class TimeMarginSettingsForm(forms.ModelForm):
    class Meta:
        model = TimeMarginSettings
        fields = ['sd_margin', 'atisa_margin']
        labels = {
            'sd_margin': 'SD time margin (%)',
            'atisa_margin': 'ATISA time margin (%)',
        }
        help_texts = {
            'sd_margin': '',
            'atisa_margin': '',
        }
        widgets = {
            'sd_margin': forms.NumberInput(attrs={
                'step': '0.01',
                'min': '0',
                'max': '100',
                'placeholder': '%',
            }),
            'atisa_margin': forms.NumberInput(attrs={
                'step': '0.01',
                'min': '0',
                'max': '100',
                'placeholder': '%',
            }),
        }


STATUS_CHOICES = [
    ('NEW', 'NEW'),
    ('IN-PROGRESS', 'IN-PROGRESS'),
    ('UAT', 'UAT'),
    ('COMPLETE', 'COMPLETE'),
]

RESOURCE_STATUS_CHOICES = [
    ('NEW', 'NEW'),
    ('IN-PROGRESS', 'IN-PROGRESS'),
    ('UAT', 'UAT'),
]


def status_choices_for(allow_complete):
    if allow_complete:
        return [('', 'Select status')] + STATUS_CHOICES
    return [('', 'Select status')] + RESOURCE_STATUS_CHOICES


class DateRangeSearchForm(forms.Form):
    start = forms.DateField(
        required=False,
        label='Start date',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'date-input'}),
    )
    end = forms.DateField(
        required=False,
        label='End date',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'date-input'}),
    )
    q = forms.CharField(
        required=False,
        label='Search',
        widget=forms.TextInput(attrs={
            'placeholder': 'Ticket, assignee, comment…',
            'class': 'search-input',
        }),
    )


class TimesheetFilterForm(DateRangeSearchForm):
    status = forms.ChoiceField(
        required=False,
        label='Status',
        choices=[('', 'All statuses')] + STATUS_CHOICES,
        widget=forms.Select(),
    )

    field_order = ['start', 'end', 'status', 'q']


def build_timesheet_form(template, allow_complete=False):
    field_definitions = {}

    for column in template.columns:
        name = column['name']
        field_type = column['type']
        key = name.lower()
        if key == 'completed at':
            continue

        if key == 'status':
            field_definitions[name] = forms.ChoiceField(
                required=False,
                choices=status_choices_for(allow_complete),
                widget=forms.Select(),
            )
        elif key == 'assigned':
            field_definitions[name] = forms.CharField(
                required=False,
                widget=forms.TextInput(attrs={
                    'readonly': True,
                    'class': 'readonly-input',
                }),
            )
        elif field_type == 'date':
            field_definitions[name] = forms.DateField(
                required=False,
                widget=forms.DateInput(attrs={'type': 'date', 'class': 'date-input'}),
            )
        elif key == 'ticket id' or (field_type == 'number' and key == 'ticket id'):
            field_definitions[name] = forms.IntegerField(
                required=True,
                min_value=0,
                widget=forms.NumberInput(attrs={
                    'step': '1',
                    'min': '0',
                    'placeholder': name,
                    'required': True,
                }),
            )
        elif field_type == 'number':
            field_definitions[name] = forms.IntegerField(
                required=False,
                min_value=0,
                widget=forms.NumberInput(attrs={
                    'step': '1',
                    'min': '0',
                    'placeholder': name,
                }),
            )
        elif field_type == 'hours' or key == 'hours spent':
            field_definitions[name] = forms.DecimalField(
                required=False,
                min_value=Decimal('0'),
                max_digits=6,
                decimal_places=2,
                widget=forms.NumberInput(attrs={
                    'step': '0.25',
                    'min': '0',
                    'placeholder': 'Hours spent',
                    'class': 'hours-input',
                }),
            )
        elif key in {'description', 'comment'}:
            field_definitions[name] = forms.CharField(
                required=False,
                widget=forms.Textarea(attrs={
                    'placeholder': name,
                    'rows': 2,
                }),
            )
        else:
            field_definitions[name] = forms.CharField(
                required=False,
                widget=forms.TextInput(attrs={'placeholder': name}),
            )

    return type(
        'DynamicTimesheetForm',
        (forms.Form,),
        field_definitions,
    )
