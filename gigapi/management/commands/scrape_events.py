from datetime import date, datetime, timedelta

import recurring_ical_events
import requests
from icalendar import Calendar
from django.core.management.base import BaseCommand

from gigapi.models import OpenMic, Show, Venue, WritersRound

LOOKAHEAD_DAYS = 60

OPEN_MIC_KEYWORDS = ['open mic', 'open-mic', 'openmic']
WRITERS_ROUND_KEYWORDS = ['writers round', "writer's round", 'writers’ round', 'writers-round']


def _categorize(title):
    lower = title.lower()
    if any(k in lower for k in OPEN_MIC_KEYWORDS):
        return 'open_mic'
    if any(k in lower for k in WRITERS_ROUND_KEYWORDS):
        return 'writers_round'
    return 'show'


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

        created = 0
        skipped = 0

        for event in events:
            result = self._process_event(event, venue)
            if result == 'created':
                created += 1
            else:
                skipped += 1

        return created, skipped

    def _process_event(self, event, venue):
        title = str(event.get('SUMMARY', '')).strip()
        if not title:
            return 'skipped'

        dtstart = event.get('DTSTART').dt
        dtend = event.get('DTEND').dt if event.get('DTEND') else None

        if not isinstance(dtstart, datetime):
            return 'skipped'

        event_date = dtstart.date()
        start_time = dtstart.time()
        if dtend and isinstance(dtend, datetime):
            end_time = dtend.time()
        else:
            end_time = start_time.replace(hour=23, minute=59)

        description = str(event.get('DESCRIPTION', '')) or ''
        ticket_link = str(event.get('URL', '')) or ''
        category = _categorize(title)

        if category == 'open_mic':
            if OpenMic.objects.filter(event_title=title, venue=venue, start_time=start_time).exists():
                return 'skipped'
            recurrence = str(event.get('RRULE', ''))
            OpenMic.objects.create(
                venue=venue,
                event_title=title,
                start_time=start_time,
                end_time=end_time,
                recurrence=recurrence,
                description=description,
            )

        elif category == 'writers_round':
            if WritersRound.objects.filter(event_title=title, venue=venue, date=event_date).exists():
                return 'skipped'
            WritersRound.objects.create(
                venue=venue,
                event_title=title,
                date=event_date,
                start_time=start_time,
                end_time=end_time,
                description=description,
            )

        else:
            if Show.objects.filter(event_title=title, venue=venue, date=event_date).exists():
                return 'skipped'
            Show.objects.create(
                venue=venue,
                event_title=title,
                date=event_date,
                start_time=start_time,
                end_time=end_time,
                ticket_link=ticket_link,
                description=description,
            )

        return 'created'
