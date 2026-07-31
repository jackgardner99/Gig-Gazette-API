import os
import re
from datetime import date, timedelta

import recurring_ical_events
import requests
from icalendar import Calendar
from django.core.management.base import BaseCommand

from gigapi.models import OpenMic, Show, Venue, WritersRound
from gigapi.utils import categorize_event, is_content_flagged, process_ical_event

LOOKAHEAD_DAYS = 60

TICKETMASTER_VENUES_URL = 'https://app.ticketmaster.com/discovery/v2/venues.json'
TICKETMASTER_EVENTS_URL = 'https://app.ticketmaster.com/discovery/v2/events.json'

# Ticketmaster's venue events feed includes administrative listings (store hours,
# signup slots, auditions) alongside real events, with no classification field
# that distinguishes them from real shows - only the title does.
NON_EVENT_KEYWORDS = ['gift shop hours', 'performer sign-up', 'performer sign up', 'auditions', 'open house']


def _normalize(text):
    return re.sub(r'[^a-z0-9]+', '', (text or '').lower())


class Command(BaseCommand):
    help = 'Sync events from venue iCal feeds and Ticketmaster'

    def handle(self, *args, **options):
        ical_venues = Venue.objects.exclude(ical_feed_url__isnull=True).exclude(ical_feed_url='')

        self.stdout.write(f'Found {ical_venues.count()} iCal venue(s)')

        created = skipped = 0

        for venue in ical_venues:
            c, s = self._sync_ical(venue)
            created += c
            skipped += s

        ticketmaster_key = os.environ.get('TICKETMASTER_API_KEY')
        if ticketmaster_key:
            all_venues = Venue.objects.all()
            self.stdout.write(f'Syncing {all_venues.count()} venue(s) from Ticketmaster')
            for venue in all_venues:
                c, s = self._sync_ticketmaster(venue, ticketmaster_key)
                created += c
                skipped += s
        else:
            self.stdout.write('TICKETMASTER_API_KEY not set, skipping Ticketmaster sync')

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

    def _resolve_ticketmaster_venue_id(self, venue, api_key):
        try:
            response = requests.get(
                TICKETMASTER_VENUES_URL,
                params={
                    'keyword': venue.name,
                    'city': venue.city,
                    'countryCode': venue.country or 'US',
                    'apikey': api_key,
                },
                timeout=10,
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            results = response.json().get('_embedded', {}).get('venues', [])
        except Exception as e:
            self.stderr.write(f'  Ticketmaster venue lookup failed for {venue.name}: {e}')
            return None

        venue_name = _normalize(venue.name)
        for result in results:
            result_name = _normalize(result.get('name'))
            if result_name and (result_name == venue_name or result_name in venue_name or venue_name in result_name):
                return result.get('id')
        return None

    def _fetch_ticketmaster_events(self, venue_id, api_key):
        start = date.today()
        end = start + timedelta(days=LOOKAHEAD_DAYS)
        try:
            response = requests.get(
                TICKETMASTER_EVENTS_URL,
                params={
                    'venueId': venue_id,
                    'startDateTime': f'{start.isoformat()}T00:00:00Z',
                    'endDateTime': f'{end.isoformat()}T23:59:59Z',
                    'sort': 'date,asc',
                    'size': 200,
                    'apikey': api_key,
                },
                timeout=10,
            )
            if response.status_code == 404:
                return [], None
            response.raise_for_status()
            return response.json().get('_embedded', {}).get('events', []), None
        except Exception as e:
            return None, str(e)

    def _sync_ticketmaster(self, venue, api_key):
        venue_id = self._resolve_ticketmaster_venue_id(venue, api_key)
        if not venue_id:
            return 0, 0

        events, error = self._fetch_ticketmaster_events(venue_id, api_key)
        if error:
            self.stderr.write(f'  Ticketmaster events fetch failed for {venue.name}: {error}')
            return 0, 0

        self.stdout.write(f'  {venue.name}: found {len(events)} Ticketmaster event(s)')
        created = skipped = 0

        for event in events:
            title = (event.get('name') or '').strip()
            start_info = (event.get('dates') or {}).get('start') or {}
            event_date = start_info.get('localDate')
            start_time = start_info.get('localTime') or '00:00:00'

            if not title or not event_date:
                skipped += 1
                continue

            if any(k in title.lower() for k in NON_EVENT_KEYWORDS):
                skipped += 1
                continue

            ticket_link = event.get('url') or ''
            description = ''
            classifications = event.get('classifications') or []
            if classifications:
                genre = (classifications[0].get('genre') or {}).get('name')
                if genre and genre != 'Undefined':
                    description = genre

            category = categorize_event(title) or 'show'
            flagged = is_content_flagged(f'{title} {description}')

            try:
                if category == 'open_mic':
                    if OpenMic.objects.filter(event_title=title, venue=venue, start_time=start_time).exists():
                        skipped += 1
                        continue
                    OpenMic.objects.create(
                        venue=venue, event_title=title,
                        start_time=start_time, end_time='23:59:00',
                        description=description, is_flagged=flagged,
                    )
                elif category == 'writers_round':
                    if WritersRound.objects.filter(event_title=title, venue=venue, date=event_date).exists():
                        skipped += 1
                        continue
                    WritersRound.objects.create(
                        venue=venue, event_title=title, date=event_date,
                        start_time=start_time, end_time='23:59:00',
                        description=description, is_flagged=flagged,
                    )
                else:
                    if Show.objects.filter(event_title=title, venue=venue, date=event_date).exists():
                        skipped += 1
                        continue
                    Show.objects.create(
                        venue=venue, event_title=title, date=event_date,
                        start_time=start_time, end_time='23:59:00',
                        ticket_link=ticket_link, description=description,
                        is_flagged=flagged,
                    )
                created += 1
            except Exception as e:
                self.stderr.write(f'  Error creating event "{title}": {e}')
                skipped += 1

        return created, skipped
