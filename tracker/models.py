from django.db import models


def timesheet_template_upload_path(instance, filename):
    return f'timesheet_templates/{filename}'


class TimesheetTemplate(models.Model):
    name = models.CharField(max_length=120)
    file = models.FileField(upload_to=timesheet_template_upload_path)
    columns = models.JSONField(default=list)
    resource_start_index = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.name

    @property
    def resource_columns(self):
        return [column for column in self.columns if column.get('is_resource')]

    @property
    def data_columns(self):
        return [column for column in self.columns if not column.get('is_resource')]


class TimesheetRecord(models.Model):
    template = models.ForeignKey(
        TimesheetTemplate,
        on_delete=models.CASCADE,
        related_name='records',
    )
    field_values = models.JSONField(default=dict)
    sd_margin = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='SD margin (%) frozen when this record was marked COMPLETE.',
    )
    atisa_margin = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='ATISA margin (%) frozen when this record was marked COMPLETE.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Timesheet #{self.pk}'

    def value_for(self, column_name, default=''):
        return self.field_values.get(column_name, default)

    def freeze_margins_if_complete(self):
        """Lock current admin margins onto COMPLETE records; leave them unchanged later."""
        values = self.field_values or {}
        if values.get('Status') != 'COMPLETE':
            self.sd_margin = None
            self.atisa_margin = None
            return

        if self.sd_margin is not None and self.atisa_margin is not None:
            return

        settings = TimeMarginSettings.get_solo()
        if self.sd_margin is None:
            self.sd_margin = settings.sd_margin
        if self.atisa_margin is None:
            self.atisa_margin = settings.atisa_margin

    @property
    def total_hours(self):
        total = 0
        for column in self.template.columns:
            if column.get('type') != 'hours':
                continue
            value = self.field_values.get(column['name'])
            if value in (None, ''):
                continue
            total += float(value)
        return round(total, 2)


class TimeMarginSettings(models.Model):
    sd_margin = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text='Time margin for SD (%).',
    )
    atisa_margin = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text='Time margin for ATISA (%).',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'time margin settings'
        verbose_name_plural = 'time margin settings'

    def __str__(self):
        return 'Time margin settings'

    @classmethod
    def get_solo(cls):
        settings_obj, _created = cls.objects.get_or_create(pk=1)
        return settings_obj


class Project(models.Model):
    name = models.CharField(max_length=120)
    color = models.CharField(max_length=7, default='#6366f1')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class TimeEntry(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='entries',
    )
    task = models.CharField(max_length=200)
    date = models.DateField()
    hours = models.DecimalField(max_digits=5, decimal_places=2)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name_plural = 'time entries'

    def __str__(self):
        return f'{self.task} ({self.hours}h)'
