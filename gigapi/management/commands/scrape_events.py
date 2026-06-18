import os
from datetime import datetime

import requests
from django.core.management.base import BaseCommand

from gigapi.models import Show, Venue

MAX_TICKET_PRICE = 40


class Command(BaseCommand):
    help = 'Scrape upcoming shows from Ticketmaster for Nashville venues'

    def handle(self, *args, **options):
        api_key = os.environ.get('TICKETMASTER_API_KEY')
        if not api_key:
            self.stderr.write('TICKETMASTER_API_KEY not set')
            return

        created = 0
        skipped = 0
        page = 0

        while True:
            try:
                response = requests.get(
                    'https://app.ticketmaster.com/discovery/v2/events.json',
                    params={
                        'apikey': api_key,
                        'city': 'Nashville',
                        'stateCode': 'TN',
                        'classificationName': 'Music',
                        'priceMax': MAX_TICKET_PRICE,
                        'size': 200,
                        'page': page,
                    },
                    timeout=10,
                )
                response.raise_for_status()
            except requests.RequestException as e:
                self.stderr.write(f'Ticketmaster request failed: {e}')
                break

            data = response.json()
            events = data.get('_embedded', {}).get('events', [])
            if not events:
                break

            for event in events:
                result = self._process_event(event)
                if result == 'created':
                    created += 1
                elif result == 'skipped':
                    skipped += 1

            total_pages = data.get('page', {}).get('totalPages', 1)
            if page >= total_pages - 1:
                break
            page += 1

        self.stdout.write(f'Done: {created} created, {skipped} skipped')

    def _process_event(self, event):
        tm_venues = event.get('_embedded', {}).get('venues', [])
        if not tm_venues:
            return 'skipped'

        venue_name = tm_venues[0].get('name', '').strip()
        venue = Venue.objects.filter(name__iexact=venue_name).first()
        if not venue:
            return 'skipped'

        dates = event.get('dates', {})
        start = dates.get('start', {})
        local_date = start.get('localDate')
        local_time = start.get('localTime')

        if not local_date or not local_time:
            return 'skipped'

        event_title = event.get('name', '').strip()
        if not event_title:
            return 'skipped'

        if Show.objects.filter(event_title=event_title, venue=venue, date=local_date).exists():
            return 'skipped'

        start_time = datetime.strptime(local_time, '%H:%M:%S').time()
        end_time_str = dates.get('end', {}).get('localTime')
        if end_time_str:
            end_time = datetime.strptime(end_time_str, '%H:%M:%S').time()
        else:
            end_time = start_time.replace(hour=23, minute=59)

        Show.objects.create(
            venue=venue,
            event_title=event_title,
            date=local_date,
            start_time=start_time,
            end_time=end_time,
            ticket_link=event.get('url', ''),
            description='',
        )
        return 'created'
