from datetime import date, timedelta

import recurring_ical_events
import requests
from icalendar import Calendar
from django.core.management.base import BaseCommand

from gigapi.models import OpenMic, Show, Venue, WritersRound
from gigapi.utils import categorize_event, is_content_flagged, process_ical_event, scrape_website_for_events

LOOKAHEAD_DAYS = 60


class Command(BaseCommand):
    help = 'Sync events from venue iCal feeds and website scrapers'

    def handle(self, *args, **options):
        ical_venues = Venue.objects.exclude(ical_feed_url__isnull=True).exclude(ical_feed_url='')
        scrape_venues = Venue.objects.exclude(scrape_url__isnull=True).exclude(scrape_url='')

        self.stdout.write(f'Found {ical_venues.count()} iCal venue(s), {scrape_venues.count()} website venue(s)')

        created = skipped = 0

        for venue in ical_venues:
            c, s = self._sync_ical(venue)
            created += c
            skipped += s

        for venue in scrape_venues:
            c, s = self._sync_website(venue)
            created += c
            skipped += s

        self.stdout.write(f'Done: {created} created, {skipped} skipped')

    def _sync_ical(self, venue):
        self.stdout.write(f'Fetching iCal for {venue.name}')
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
        self.stdout.write(f'  Found {len(events)} event(s)')

        Show.objects.filter(venue=venue, date__gte=start, date__lte=end).delete()
        OpenMic.objects.filter(venue=venue).delete()
        WritersRound.objects.filter(venue=venue, date__gte=start, date__lte=end).delete()

        created = skipped = 0
        for event in events:
            result = process_ical_event(event, venue)
            if result == 'created':
                created += 1
            else:
                skipped += 1
        return created, skipped

    def _sync_website(self, venue):
        self.stdout.write(f'Scraping website for {venue.name}: {venue.scrape_url}')
        events, error = scrape_website_for_events(venue.scrape_url)
        if error:
            self.stderr.write(f'  Failed: {error}')
            return 0, 0

        self.stdout.write(f'  Found {len(events)} event(s)')
        created = skipped = 0

        for event_data in events:
            title = (event_data.get('title') or '').strip()
            if not title:
                skipped += 1
                continue

            category = event_data.get('event_type') or 'show'
            if category not in ('show', 'open_mic', 'writers_round'):
                category = 'show'

            event_date = event_data.get('date')
            start_time = event_data.get('start_time') or '00:00:00'
            end_time = event_data.get('end_time') or '23:59:00'
            description = event_data.get('description') or ''
            ticket_link = event_data.get('ticket_link') or ''
            flagged = is_content_flagged(f'{title} {description}')

            try:
                if category == 'open_mic':
                    if OpenMic.objects.filter(event_title=title, venue=venue, start_time=start_time).exists():
                        skipped += 1
                        continue
                    OpenMic.objects.create(
                        venue=venue,
                        event_title=title,
                        start_time=start_time,
                        end_time=end_time,
                        description=description,
                        is_flagged=flagged,
                    )
                elif category == 'writers_round':
                    if not event_date or WritersRound.objects.filter(event_title=title, venue=venue, date=event_date).exists():
                        skipped += 1
                        continue
                    WritersRound.objects.create(
                        venue=venue,
                        event_title=title,
                        date=event_date,
                        start_time=start_time,
                        end_time=end_time,
                        description=description,
                        is_flagged=flagged,
                    )
                else:
                    if not event_date or Show.objects.filter(event_title=title, venue=venue, date=event_date).exists():
                        skipped += 1
                        continue
                    Show.objects.create(
                        venue=venue,
                        event_title=title,
                        date=event_date,
                        start_time=start_time,
                        end_time=end_time,
                        ticket_link=ticket_link,
                        description=description,
                        is_flagged=flagged,
                    )
                created += 1
            except Exception as e:
                self.stderr.write(f'  Error creating event "{title}": {e}')
                skipped += 1

        return created, skipped
