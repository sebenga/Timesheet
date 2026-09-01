from django.core.files.base import ContentFile
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone

from tracker.dashboard_summary import (
    build_completed_month_summary,
    format_hours,
    format_margin_display,
    round_hours,
    round_whole_hours,
)
from tracker.models import TimesheetRecord, TimesheetTemplate
from tracker.timesheet_query import filter_timesheet_records


class TableSearchTests(TestCase):
    def setUp(self):
        self.template = TimesheetTemplate(
            name='Default',
            columns=[],
            resource_start_index=0,
            is_active=True,
        )
        self.template.file.save('sample.csv', ContentFile(b'ticket\n'), save=False)
        self.template.save()
        self.alpha = TimesheetRecord.objects.create(
            template=self.template,
            field_values={
                'Ticket ID': '1001',
                'Description': 'Alpha billing fix',
                'Status': 'COMPLETE',
                'Assigned': 'sikidosi',
                'Hours spent': '2',
            },
            sd_margin=10,
            atisa_margin=35,
        )
        self.beta = TimesheetRecord.objects.create(
            template=self.template,
            field_values={
                'Ticket ID': '2002',
                'Description': 'Beta login work',
                'Status': 'IN-PROGRESS',
                'Assigned': 'alice',
                'Hours spent': '3',
            },
        )
        now = timezone.now()
        TimesheetRecord.objects.filter(pk__in=[self.alpha.pk, self.beta.pk]).update(created_at=now)

    def test_timesheet_text_search_matches_description(self):
        records = filter_timesheet_records(
            TimesheetRecord.objects.all(),
            start=None,
            end=None,
            status='',
            query='billing',
        )
        self.assertEqual(list(records), [self.alpha])

    def test_dashboard_search_filters_grouped_rows(self):
        summary = build_completed_month_summary(query='1001')
        self.assertEqual(len(summary['rows']), 1)
        self.assertEqual(summary['rows'][0]['details']['Ticket ID'], '1001')

    def test_dashboard_margin_columns(self):
        summary = build_completed_month_summary()
        row = summary['rows'][0]
        self.assertEqual(row['atisa_margin_display'], '1h @ 35%')
        self.assertEqual(row['admin_margin_display'], '0h @ 10%')
        self.assertEqual(row['atisa_total_decimal'], Decimal('3'))
        self.assertEqual(row['admin_sd_total_decimal'], Decimal('2'))

        empty = build_completed_month_summary(query='does-not-exist')
        self.assertEqual(empty['rows'], [])

    def test_format_margin_display_multiple_percents(self):
        self.assertEqual(
            format_margin_display(Decimal('3'), {Decimal('10'), Decimal('35')}),
            '3h @ 10/35%',
        )

    def test_hours_round_to_one_decimal(self):
        self.assertEqual(round_hours(Decimal('2.35')), Decimal('2.4'))
        self.assertEqual(round_hours(Decimal('2.34')), Decimal('2.3'))
        self.assertEqual(format_hours(Decimal('0.70')), '0.7')
        self.assertEqual(format_hours(Decimal('2')), '2')

    def test_margin_and_total_hours_round_to_whole(self):
        self.assertEqual(round_whole_hours(Decimal('2.4')), Decimal('2'))
        self.assertEqual(round_whole_hours(Decimal('2.5')), Decimal('3'))
        self.assertEqual(round_whole_hours(Decimal('2.6')), Decimal('3'))
        self.assertEqual(round_whole_hours(Decimal('0.2')), Decimal('0'))
        self.assertEqual(round_whole_hours(Decimal('0.7')), Decimal('1'))
