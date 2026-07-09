import html
import re
from datetime import datetime

from gigapi.models import OpenMic, Show, WritersRound

OPEN_MIC_KEYWORDS = ['open mic', 'open-mic', 'openmic']
WRITERS_ROUND_KEYWORDS = ['writers round', "writer's round", "writers' round", 'writers-round']
SHOW_KEYWORDS = ['show', 'concert', 'gig', 'performance', 'live music', 'live', 'band', 'music', 'showcase', 'tour']


def categorize_event(title):
    lower = title.lower()
    if any(k in lower for k in OPEN_MIC_KEYWORDS):
        return 'open_mic'
    if any(k in lower for k in WRITERS_ROUND_KEYWORDS):
        return 'writers_round'
    if any(k in lower for k in SHOW_KEYWORDS):
        return 'show'
    return None


def process_ical_event(event, venue):
    title = str(event.get('SUMMARY', '')).strip()
    if not title:
        return 'skipped'

    dtstart = event.get('DTSTART').dt
    dtend = event.get('DTEND').dt if event.get('DTEND') else None

    if not isinstance(dtstart, datetime):
        return 'skipped'

    category = categorize_event(title)
    if category is None:
        return 'skipped'

    event_date = dtstart.date()
    start_time = dtstart.time()
    end_time = dtend.time() if dtend and isinstance(dtend, datetime) else start_time.replace(hour=23, minute=59)

    raw_description = str(event.get('DESCRIPTION', '')) or ''
    raw_description = html.unescape(raw_description)
    raw_description = re.sub(r'<[^>]+>', '', raw_description).strip()

    ticket_link = str(event.get('URL', '')) or ''
    if not ticket_link:
        urls = re.findall(r'https?://\S+', raw_description)
        if urls:
            ticket_link = urls[0]
            raw_description = re.sub(re.escape(ticket_link), '', raw_description).strip()

    description = raw_description

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
