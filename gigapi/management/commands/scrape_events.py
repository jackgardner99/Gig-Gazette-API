import os
from datetime import datetime

import requests
from django.core.management.base import BaseCommand

from gigapi.models import Show, Venue


class Command(BaseCommand):
    help = 'Scrape upcoming shows from Eventbrite for Nashville venues'

    def handle(self, *args, **options):
        api_key = os.environ.get('EVENTBRITE_API_KEY')
        if not api_key:
            self.stderr.write('EVENTBRITE_API_KEY not set')
            return

        headers = {'Authorization': f'Bearer {api_key}'}
        created = 0
        skipped = 0
        page = 1

        while True:
            try:
                response = requests.get(
                    'https://www.eventbriteapi.com/v3/events/search/',
                    headers=headers,
                    params={
                        'location.address': 'Nashville, TN',
                        'location.within': '25mi',
                        'categories': '103',
                        'expand': 'venue',
                        'page_size': 50,
                        'page': page,
                    },
                    timeout=10,
                )
                response.raise_for_status()
            except requests.RequestException as e:
                self.stderr.write(f'Eventbrite request failed: {e}')
                break

            data = response.json()
            events = data.get('events', [])
            if not events:
                break

            for event in events:
                result = self._process_event(event)
                if result == 'created':
                    created += 1
                elif result == 'skipped':
                    skipped += 1

            if not data.get('pagination', {}).get('has_more_items'):
                break
            page += 1

        self.stdout.write(f'Done: {created} created, {skipped} skipped')

    def _process_event(self, event):
        eb_venue = event.get('venue')
        if not eb_venue:
            return 'skipped'

        venue_name = eb_venue.get('name', '').strip()
        venue = Venue.objects.filter(name__iexact=venue_name).first()
        if not venue:
            return 'skipped'

        start_str = event.get('start', {}).get('local')
        end_str = event.get('end', {}).get('local')
        if not start_str:
            return 'skipped'

        start_dt = datetime.fromisoformat(start_str)
        end_dt = datetime.fromisoformat(end_str) if end_str else None

        event_title = event.get('name', {}).get('text', '').strip()
        if not event_title:
            return 'skipped'

        if Show.objects.filter(event_title=event_title, venue=venue, date=start_dt.date()).exists():
            return 'skipped'

        Show.objects.create(
            venue=venue,
            event_title=event_title,
            date=start_dt.date(),
            start_time=start_dt.time(),
            end_time=end_dt.time() if end_dt else start_dt.replace(hour=23, minute=59).time(),
            ticket_link=event.get('url', ''),
            description=event.get('description', {}).get('text', '') or '',
        )
        return 'created'
