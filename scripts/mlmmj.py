"""Read public RFC 5322 messages and decode their MIME content."""
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime, parseaddr
from html import escape
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

MONTHS = ('January February March April May June July August September October November December').split()
GERMAN = ('Januar Februar März April Mai Juni Juli August September Oktober November Dezember').split()


def message_id_from_html(text):
    match = re.search(r'In-Reply-To=([^&"\s>]+)', text, re.I)
    return unquote(match[1]) if match else None


class PlainHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.skip += 1
        if tag in ('p', 'div', 'br', 'li', 'tr') and not self.skip:
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style') and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def decode_part(part):
    payload = part.get_payload(decode=True)
    if payload is None:
        return str(part.get_payload())
    try:
        return payload.decode(part.get_content_charset() or 'utf-8', errors='replace')
    except LookupError:
        return payload.decode('utf-8', errors='replace')


def body_text(message):
    if message.get_content_disposition() == 'attachment':
        return ''
    if message.is_multipart():
        if message.get_content_subtype() == 'alternative':
            parts = list(message.iter_parts())
            preferred = next((p for p in parts if p.get_content_type() == 'text/plain'), None)
            if preferred is not None:
                return body_text(preferred)
            return next((text for p in parts if (text := body_text(p))), '')
        return '\n'.join(text for p in message.iter_parts() if (text := body_text(p)))
    if message.get_content_type() == 'text/plain':
        return decode_part(message)
    if message.get_content_type() == 'text/html':
        parser = PlainHTML()
        parser.feed(decode_part(message))
        return ''.join(parser.parts)
    return ''


def linkify(text, page, rewrite=None):
    result = []
    position = 0
    for match in re.finditer(r'https?://[^\s<>"\x00-\x1f]+', text):
        result.append(escape(text[position:match.start()]))
        candidate = match[0].rstrip('.,;:!?')
        while candidate and candidate[-1] in ')]}' and candidate.count(candidate[-1]) > candidate.count({')': '(', ']': '[', '}': '{'}[candidate[-1]]):
            candidate = candidate[:-1]
        try:
            valid = bool(urlsplit(candidate).hostname)
        except ValueError:
            valid = False
        target = rewrite(candidate, page) if valid and rewrite else candidate
        result.append(f'<a href="{escape(target, quote=True)}">{escape(candidate)}</a>' if valid and target else escape(candidate))
        result.append(escape(match[0][len(candidate):]))
        position = match.end()
    result.append(escape(text[position:]))
    return ''.join(result)


def read_messages(root):
    source = root / 'messages'
    manifest = json.loads((root / 'messages-manifest.json').read_text())
    actual = {str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in source.rglob('*') if p.is_file()}
    if actual != manifest:
        raise ValueError('Additional messages differ from messages-manifest.json')
    rows = []
    seen = set()
    for file in sorted(source.glob('*/*.eml')):
        message = BytesParser(policy=policy.default).parsebytes(file.read_bytes())
        mid = str(message.get('Message-ID', '')).strip()
        name = file.parent.name
        if not mid or (name, mid) in seen:
            raise ValueError('Missing or duplicate Message-ID: ' + str(file))
        seen.add((name, mid))
        date = parsedate_to_datetime(str(message['Date']))
        if date.tzinfo is None:
            raise ValueError('Message date has no UTC offset: ' + str(file))
        name = file.parent.name
        month = f'{date.year}-{MONTHS[date.month-1]}'
        page = Path(name) / month / f'mlmmj-{int(file.stem):06}.html'
        refs = re.findall(r'<[^<>]+>', str(message.get('References', '')) + ' ' + str(message.get('In-Reply-To', '')))
        attachments = []
        for i, part in enumerate(message.walk()):
            if part.is_multipart() or not (part.get_filename() or part.get_content_disposition() == 'attachment'):
                continue
            filename = Path(str(part.get_filename() or 'attachment.bin').replace('\\', '/')).name
            filename = re.sub(r'[^\w.()+ -]', '_', filename).strip('. ') or 'attachment.bin'
            target = Path(name) / 'attachments' / 'mlmmj' / file.stem / f'{i:02}-{filename}'
            attachments.append((target, part.get_payload(decode=True) or b''))
        rows.append({'id': mid, 'page': page, 'list': name, 'month': month,
                     'date': date, 'title': str(message.get('Subject', '(kein Betreff)')),
                     'author': parseaddr(str(message.get('From', '')))[0] or parseaddr(str(message.get('From', '')))[1],
                     'body': body_text(message), 'references': refs, 'attachments': attachments,
                     'source': file, 'anchor': page.stem})
    return sorted(rows, key=lambda row: (row['date'].timestamp(), str(row['page'])))
