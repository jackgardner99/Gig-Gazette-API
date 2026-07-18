import io
import zipfile
from datetime import date, timedelta

import recurring_ical_events
from icalendar import Calendar
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from gigapi.models import OpenMic, Show, Venue, WritersRound
from gigapi.utils import categorize_event, is_content_flagged, process_ical_event, scrape_website_for_events

LOOKAHEAD_DAYS = 365


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
