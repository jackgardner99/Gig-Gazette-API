import html
import os
import re
from datetime import datetime

import requests

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


def is_content_flagged(text):
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key or not text:
        return False
    try:
        response = requests.post(
            'https://api.openai.com/v1/moderations',
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            json={'input': text},
            timeout=5,
        )
        response.raise_for_status()
        return response.json()['results'][0]['flagged']
    except Exception:
        return False


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
    flagged = is_content_flagged(f'{title} {description}')

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
            is_flagged=flagged,
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
            is_flagged=flagged,
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
            is_flagged=flagged,
        )

    return 'created'


def scrape_website_for_events(url):
    import json
    from bs4 import BeautifulSoup

    try:
        response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
    except Exception as e:
        return None, str(e)

    soup = BeautifulSoup(response.text, 'html.parser')
    for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
        tag.decompose()
    text = ' '.join(soup.get_text(separator=' ').split())[:8000]

    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        return None, 'OPENAI_API_KEY not set'

    prompt = (
        'Extract all upcoming events from this venue website content. '
        'Return ONLY a valid JSON array (no markdown, no explanation) where each item has: '
        '"title" (string), "date" (YYYY-MM-DD or null), "start_time" (HH:MM:SS or null), '
        '"end_time" (HH:MM:SS or null), "description" (string), "ticket_link" (URL or null), '
        '"event_type" (one of: "show", "open_mic", "writers_round" — classify based on the event content, default to "show"). '
        'If no events are found return []. '
        f'Website content:\n{text}'
    )

    try:
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            json={
                'model': 'gpt-4o-mini',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0,
            },
            timeout=30,
        )
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content'].strip()
        events = json.loads(content)
        return events, None
    except Exception as e:
        return None, str(e)
