import io
import zipfile
from datetime import date, timedelta

import recurring_ical_events
from icalendar import Calendar
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from gigapi.models import Venue
from gigapi.utils import process_ical_event

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
        venue_ids = request.data.getlist('venue_ids')

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
