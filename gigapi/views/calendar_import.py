import difflib
import io
import re
import zipfile
from datetime import date, timedelta
from urllib.parse import quote

import recurring_ical_events
import requests
from icalendar import Calendar
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from gigapi.models import OpenMic, Show, Venue, WritersRound
from gigapi.utils import categorize_event, is_content_flagged, process_ical_event, scrape_website_for_events, split_iso_datetime

LOOKAHEAD_DAYS = 365

# Words too generic to carry matching signal on their own (they show up in most
# venue names in this dataset, e.g. every Venue.name here ends in "Nashville").
GENERIC_VENUE_WORDS = {'the', 'nashville', 'downtown', 'and', 'at', 'venue'}

VENUE_NAME_SIMILARITY_THRESHOLD = 0.6


def _normalize(text):
    return re.sub(r'[^a-z0-9]+', '', (text or '').lower())


def _normalize_venue_name(text):
    words = re.findall(r'[a-z0-9]+', (text or '').lower())
    return ''.join(w for w in words if w not in GENERIC_VENUE_WORDS)


def _match_bandsintown_venue(bt_venue, venues):
    bt_name = _normalize_venue_name(bt_venue.get('name'))
    bt_city = _normalize(bt_venue.get('city'))
    if not bt_name:
        return None

    for venue in venues:
        venue_name = _normalize_venue_name(venue.name)
        if not venue_name:
            continue
        if bt_city and venue.city and _normalize(venue.city) != bt_city:
            continue
        if bt_name == venue_name or bt_name in venue_name or venue_name in bt_name:
            return venue
        if difflib.SequenceMatcher(None, bt_name, venue_name).ratio() >= VENUE_NAME_SIMILARITY_THRESHOLD:
            return venue
    return None


def _fetch_bandsintown_events(artist_name, api_key):
    try:
        response = requests.get(
            f'https://rest.bandsintown.com/artists/{quote(artist_name)}/events',
            params={'app_id': api_key},
            timeout=10,
        )
        response.raise_for_status()
        return response.json(), None
    except Exception as e:
        return None, str(e)


def _read_ical_bytes(upload):
    raw = upload.read()
    if zipfile.is_zipfile(io.BytesIO(raw)):
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            ics_names = [n for n in zf.namelist() if n.endswith('.ics')]
            if not ics_names:
                return None, 'Zip contains no .ics files'
            raw = zf.read(ics_names[0])
    return raw, None


class CalendarImportViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):
        calendar_file = request.FILES.get('calendar_file')
        venue_ids = request.data.getlist('venue_ids') if hasattr(request.data, 'getlist') else request.data.get('venue_ids', [])

        if not calendar_file:
            return Response({'error': 'calendar_file is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not venue_ids:
            return Response({'error': 'venue_ids is required'}, status=status.HTTP_400_BAD_REQUEST)

        venues = Venue.objects.filter(pk__in=venue_ids)
        if not venues.exists():
            return Response({'error': 'No matching venues found'}, status=status.HTTP_404_NOT_FOUND)

        raw, err = _read_ical_bytes(calendar_file)
        if err:
            return Response({'error': err}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cal = Calendar.from_ical(raw)
        except Exception:
            return Response({'error': 'Invalid iCal file'}, status=status.HTTP_400_BAD_REQUEST)

        start = date.today()
        end = start + timedelta(days=LOOKAHEAD_DAYS)
        events = recurring_ical_events.of(cal).between(start, end)

        created = 0
        skipped = 0

        for venue in venues:
            for event in events:
                result = process_ical_event(event, venue)
                if result == 'created':
                    created += 1
                else:
                    skipped += 1

        return Response({'created': created, 'skipped': skipped}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='from-url')
    def from_url(self, request):
        url = request.data.get('url')
        venue_ids = request.data.getlist('venue_ids') if hasattr(request.data, 'getlist') else request.data.get('venue_ids', [])
        if not isinstance(venue_ids, list):
            venue_ids = [venue_ids]

        if not url:
            return Response({'error': 'url is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not venue_ids:
            return Response({'error': 'venue_ids is required'}, status=status.HTTP_400_BAD_REQUEST)

        venues = Venue.objects.filter(pk__in=venue_ids)
        if not venues.exists():
            return Response({'error': 'No matching venues found'}, status=status.HTTP_404_NOT_FOUND)

        events, error = scrape_website_for_events(url)
        if error:
            return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)

        created = skipped = 0

        for venue in venues:
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
                            venue=venue, event_title=title,
                            start_time=start_time, end_time=end_time,
                            description=description, is_flagged=flagged,
                        )
                    elif category == 'writers_round':
                        if not event_date or WritersRound.objects.filter(event_title=title, venue=venue, date=event_date).exists():
                            skipped += 1
                            continue
                        WritersRound.objects.create(
                            venue=venue, event_title=title, date=event_date,
                            start_time=start_time, end_time=end_time,
                            description=description, is_flagged=flagged,
                        )
                    else:
                        if not event_date or Show.objects.filter(event_title=title, venue=venue, date=event_date).exists():
                            skipped += 1
                            continue
                        Show.objects.create(
                            venue=venue, event_title=title, date=event_date,
                            start_time=start_time, end_time=end_time,
                            ticket_link=ticket_link, description=description,
                            is_flagged=flagged,
                        )
                    created += 1
                except Exception:
                    skipped += 1

        return Response({'created': created, 'skipped': skipped}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='from-bandsintown')
    def from_bandsintown(self, request):
        api_key = request.data.get('bandsintown_api_key')
        artist_name = request.data.get('artist_name')
        venue_ids = request.data.getlist('venue_ids') if hasattr(request.data, 'getlist') else request.data.get('venue_ids', [])
        if not isinstance(venue_ids, list):
            venue_ids = [venue_ids]

        if not api_key:
            return Response({'error': 'bandsintown_api_key is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not artist_name:
            return Response({'error': 'artist_name is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not venue_ids:
            return Response({'error': 'venue_ids is required'}, status=status.HTTP_400_BAD_REQUEST)

        venues = list(Venue.objects.filter(pk__in=venue_ids))
        if not venues:
            return Response({'error': 'No matching venues found'}, status=status.HTTP_404_NOT_FOUND)

        events, error = _fetch_bandsintown_events(artist_name, api_key)
        if error:
            return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)

        created = skipped = 0
        unmatched = []

        for event in events or []:
            bt_venue = event.get('venue') or {}
            venue = _match_bandsintown_venue(bt_venue, venues)
            if venue is None:
                unmatched.append(bt_venue.get('name') or 'unknown venue')
                continue

            event_date, start_time = split_iso_datetime(event.get('datetime'))
            if not event_date:
                skipped += 1
                continue

            lineup = event.get('lineup') or []
            support = [act for act in lineup if act and act != artist_name]
            description = event.get('description') or (f"with {', '.join(support)}" if support else '')

            ticket_link = ''
            offers = event.get('offers') or []
            if offers:
                ticket_link = offers[0].get('url') or ''
            if not ticket_link:
                ticket_link = event.get('url') or ''

            category = categorize_event(artist_name) or 'show'
            start_time = start_time or '00:00:00'
            flagged = is_content_flagged(f'{artist_name} {description}')

            try:
                if category == 'open_mic':
                    if OpenMic.objects.filter(event_title=artist_name, venue=venue, start_time=start_time).exists():
                        skipped += 1
                        continue
                    OpenMic.objects.create(
                        venue=venue, event_title=artist_name,
                        start_time=start_time, end_time='23:59:00',
                        description=description, is_flagged=flagged,
                    )
                elif category == 'writers_round':
                    if WritersRound.objects.filter(event_title=artist_name, venue=venue, date=event_date).exists():
                        skipped += 1
                        continue
                    WritersRound.objects.create(
                        venue=venue, event_title=artist_name, date=event_date,
                        start_time=start_time, end_time='23:59:00',
                        description=description, is_flagged=flagged,
                    )
                else:
                    if Show.objects.filter(event_title=artist_name, venue=venue, date=event_date).exists():
                        skipped += 1
                        continue
                    Show.objects.create(
                        venue=venue, event_title=artist_name, date=event_date,
                        start_time=start_time, end_time='23:59:00',
                        ticket_link=ticket_link, description=description,
                        is_flagged=flagged,
                    )
                created += 1
            except Exception:
                skipped += 1

        return Response({'created': created, 'skipped': skipped, 'unmatched': unmatched}, status=status.HTTP_201_CREATED)
