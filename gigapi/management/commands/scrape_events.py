from datetime import date, timedelta

import recurring_ical_events
import requests
from icalendar import Calendar
from django.core.management.base import BaseCommand

from gigapi.models import OpenMic, Show, Venue, WritersRound
from gigapi.utils import process_ical_event

LOOKAHEAD_DAYS = 60


class Command(BaseCommand):
    help = 'Sync events from venue iCal feeds'

    def handle(self, *args, **options):
        venues = Venue.objects.exclude(ical_feed_url__isnull=True).exclude(ical_feed_url='')
        self.stdout.write(f'Found {venues.count()} venue(s) with iCal feeds')
        if not venues.exists():
            self.stdout.write('No venues with iCal feeds found — add an ical_feed_url to a venue first')
            return

        created = 0
        skipped = 0

        for venue in venues:
            c, s = self._sync_venue(venue)
            created += c
            skipped += s

        self.stdout.write(f'Done: {created} created, {skipped} skipped')

    def _sync_venue(self, venue):
        self.stdout.write(f'Fetching feed for {venue.name}: {venue.ical_feed_url}')
        try:
            response = requests.get(venue.ical_feed_url, timeout=10)
            response.raise_for_status()
            cal = Calendar.from_ical(response.content)
        except Exception as e:
            self.stderr.write(f'Failed to fetch feed for {venue.name}: {e}')
            return 0, 0

        start = date.today()
        end = start + timedelta(days=LOOKAHEAD_DAYS)
        events = recurring_ical_events.of(cal).between(start, end)
        self.stdout.write(f'Found {len(events)} event(s) in the next {LOOKAHEAD_DAYS} days')

        Show.objects.filter(venue=venue, date__gte=start, date__lte=end).delete()
        OpenMic.objects.filter(venue=venue).delete()
        WritersRound.objects.filter(venue=venue, date__gte=start, date__lte=end).delete()

        created = 0
        skipped = 0

        for event in events:
            result = process_ical_event(event, venue)
            if result == 'created':
                created += 1
            else:
                skipped += 1

        return created, skipped
