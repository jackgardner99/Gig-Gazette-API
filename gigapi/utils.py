import html
import json
import os
import re
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from gigapi.models import OpenMic, Show, WritersRound

SCRAPE_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
)

OPEN_MIC_KEYWORDS = ['open mic', 'open-mic', 'openmic']
WRITERS_ROUND_KEYWORDS = ['writers round', "writer's round", "writers' round", 'writers-round', 'in the round', 'in the row', 'writer', 'writers']
SHOW_KEYWORDS = ['show', 'concert', 'gig', 'performance', 'live music', 'live', 'band', 'music', 'showcase', 'tour']

# Known Nashville writers rounds whose event/artist titles don't contain any
# WRITERS_ROUND_KEYWORDS string, so keyword matching alone would miscategorize them.
KNOWN_WRITERS_ROUNDS = {
    'nashville tour stop',
}


def categorize_event(title):
    lower = title.lower().strip()
    if lower in KNOWN_WRITERS_ROUNDS:
        return 'writers_round'
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


def split_iso_datetime(value):
    if not value or not isinstance(value, str):
        return None, None
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None, None
    return dt.date().isoformat(), dt.time().isoformat()


def _walk_jsonld(node):
    results = []
    if isinstance(node, list):
        for item in node:
            results.extend(_walk_jsonld(item))
    elif isinstance(node, dict):
        node_type = node.get('@type')
        types = node_type if isinstance(node_type, list) else [node_type]
        if any(isinstance(t, str) and 'Event' in t for t in types):
            results.append(node)
        for key in ('@graph', 'itemListElement'):
            if key in node:
                results.extend(_walk_jsonld(node[key]))
    return results


def _jsonld_to_event(raw, base_url):
    title = raw.get('name')
    if not title or not isinstance(title, str):
        return None

    event_date, start_time = split_iso_datetime(raw.get('startDate'))
    _, end_time = split_iso_datetime(raw.get('endDate'))

    ticket_link = raw.get('url') or ''
    offers = raw.get('offers')
    if not ticket_link and offers:
        offers = offers[0] if isinstance(offers, list) and offers else offers
        if isinstance(offers, dict):
            ticket_link = offers.get('url') or ''
    if ticket_link:
        ticket_link = urljoin(base_url, ticket_link)

    description = raw.get('description')
    description = description.strip() if isinstance(description, str) else ''

    return {
        'title': title.strip(),
        'date': event_date,
        'start_time': start_time,
        'end_time': end_time,
        'description': description,
        'ticket_link': ticket_link,
        'event_type': categorize_event(title) or 'show',
    }


def _extract_jsonld_events(soup, base_url):
    events = []
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string or script.get_text())
        except (TypeError, ValueError):
            continue
        for raw in _walk_jsonld(data):
            event = _jsonld_to_event(raw, base_url)
            if event:
                events.append(event)
    return events


def _mark_links_and_times(soup, base_url):
    for tag in soup.find_all('a'):
        href = tag.get('href')
        if not href:
            continue
        label = tag.get_text(strip=True) or tag.get('aria-label') or tag.get('title') or 'link'
        tag.replace_with(f'{label} [LINK: {urljoin(base_url, href)}]')

    for tag in soup.find_all('time'):
        dt_value = tag.get('datetime')
        if not dt_value:
            continue
        label = tag.get_text(strip=True) or dt_value
        tag.replace_with(f'{label} [TIME: {dt_value}]')


def scrape_website_for_events(url):
    session = requests.Session()
    session.headers.update({
        'User-Agent': SCRAPE_USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': url,
    })

    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
    except Exception as e:
        return None, str(e)

    soup = BeautifulSoup(response.text, 'html.parser')

    jsonld_events = _extract_jsonld_events(soup, url)
    if jsonld_events:
        return jsonld_events, None

    _mark_links_and_times(soup, url)
    for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
        tag.decompose()
    text = ' '.join(soup.get_text(separator=' ').split())[:20000]

    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        return None, 'OPENAI_API_KEY not set'

    prompt = (
        'Extract all upcoming events from this venue website content. '
        'Links appear inline as "text [LINK: url]" and times as "text [TIME: iso-datetime]" — '
        'use these markers as the source of truth for ticket_link, date, start_time, and end_time when present. '
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
