from django.contrib import admin

from .models import Project, TimeEntry, TimeMarginSettings, TimesheetRecord, TimesheetTemplate


@admin.register(TimeMarginSettings)
class TimeMarginSettingsAdmin(admin.ModelAdmin):
    list_display = ['sd_margin', 'atisa_margin', 'updated_at']


@admin.register(TimesheetTemplate)
class TimesheetTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'uploaded_at']
    list_filter = ['is_active']


@admin.register(TimesheetRecord)
class TimesheetRecordAdmin(admin.ModelAdmin):
    list_display = ['id', 'template', 'created_at']
    list_filter = ['template']


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'created_at']


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ['task', 'project', 'date', 'hours', 'created_at']
    list_filter = ['project', 'date']
