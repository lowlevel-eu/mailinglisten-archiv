"""Normalize Mailman and mlmmj messages and render a single archive format."""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
import posixpath
import re
from urllib.parse import unquote, urlsplit

from common import ArchiveHTML, decode_html, document, relative, rewrite_link, LISTS
from mlmmj import MONTHS, GERMAN, linkify, message_id_from_html, read_messages


def mailman_date(text):
    parts = text.split()
    months = dict(zip(MONTHS, range(1, 13)))
    months.update({name[:3]: i for i, name in enumerate(MONTHS, 1)})
    months.update({'Mär': 3, 'Mai': 5, 'Okt': 10, 'Dez': 12})
    if len(parts) != 6 or parts[4] not in ('CET', 'CEST'):
        raise ValueError('Unrecognized Pipermail date: ' + text)
    hour, minute, second = map(int, parts[3].split(':'))
    offset = timezone(timedelta(hours=2 if parts[4] == 'CEST' else 1))
    return datetime(int(parts[5]), months[parts[1]], int(parts[2]), hour, minute, second, tzinfo=offset)


def load_mailman(root):
    rows = []
    by_page = {}
    for name in LISTS:
        for file in sorted((root / 'archives' / name).glob('*/[0-9]*.html')):
            page = file.relative_to(root / 'archives')
            original = decode_html(file.read_bytes())
            parser = ArchiveHTML(page)
            parser.feed(original)
            mid = message_id_from_html(original)
            if not mid:
                raise ValueError('Missing Message-ID: ' + str(file))
            html = ''.join(parser.output)
            if '<!--beginarticle-->' not in html or '<!--endarticle-->' not in html:
                raise ValueError('Missing article boundaries: ' + str(file))
            body_html = html.split('<!--beginarticle-->', 1)[1].split('<!--endarticle-->', 1)[0]
            row = {'id': mid, 'page': page, 'list': name, 'month': page.parts[1],
                   'date': mailman_date(''.join(parser.date).strip()),
                   'title': ' '.join(''.join(parser.title).split()),
                   'author': ''.join(parser.author).strip(), 'body': ''.join(parser.text),
                   'body_html': body_html, 'references': [], 'attachments': [],
                   'downloads': [], 'source_format': 'mailman',
                   'source_path': str(file.relative_to(root)), 'anchor': str(int(file.stem))}
            # Pipermail already detached attachments. Preserve their paths and bytes.
            for match in re.finditer(r'href="([^"]+)"', body_html):
                url = urlsplit(unquote(match[1].replace('&amp;', '&')))
                if not url.scheme and not url.netloc:
                    target = (page.parent / url.path)
                    # Normalize ../ segments without resolving against a real filesystem.
                    target = Path(posixpath.normpath(target.as_posix()))
                    if 'attachments' in target.parts and target not in [a['path'] for a in row['attachments']]:
                        row['attachments'].append({'path': target, 'name': target.name})
            rows.append(row)
            by_page[page] = row
    # The nesting in each original thread index is authoritative for older messages.
    for file in sorted((root / 'archives').glob('*/*/thread.html')):
        stack = []
        for depth, filename in re.findall(r'<!--(\d+)\s+[^>]*-->\s*<li>\s*<a\s+href="(\d+\.html)"', decode_html(file.read_bytes()), re.I):
            page = file.parent.relative_to(root / 'archives') / filename
            if page not in by_page:
                raise ValueError('Thread index references unknown message: ' + str(page))
            row = by_page[page]
            depth = int(depth)
            if depth > len(stack):
                raise ValueError('Invalid thread nesting: ' + str(file))
            stack = stack[:depth]
            if stack:
                row['references'] = [stack[-1]['id']]
            stack.append(row)
    return rows


def load_messages(root):
    rows = load_mailman(root)
    for row in read_messages(root):
        row['body_html'] = '<pre>' + linkify(row['body'], row['page'], rewrite_link) + '</pre>'
        row['attachment_payloads'] = row['attachments']
        row['attachments'] = [{'path': path, 'name': path.name} for path, payload in row['attachment_payloads']]
        download = Path('messages') / row['source'].relative_to(root / 'messages')
        row['downloads'] = [(download, 'Originalnachricht herunterladen (.eml)')]
        row['source_format'] = 'mlmmj'
        row['source_path'] = str(row['source'].relative_to(root))
        rows.append(row)
    seen = set()
    for row in rows:
        key = row['list'], row['id']
        if key in seen:
            raise ValueError('Duplicate message within a list: ' + str(key))
        seen.add(key)
    return sorted(rows, key=lambda row: (row['date'].timestamp(), str(row['page'])))


def month_label(month):
    return GERMAN[MONTHS.index(month[5:])] + ' ' + month[:4]


def month_key(month):
    return int(month[:4]), MONTHS.index(month[5:])


def index_nav():
    return '<nav class="sort-nav">' + ''.join(f'<a href="{mode}.html">{label}</a>' for mode, label in [('thread', 'Diskussionsfäden'), ('date', 'Datum'), ('subject', 'Betreff'), ('author', 'Autor')]) + '</nav>'


def serializable(row):
    return {'id': row['id'], 'list': row['list'], 'month': row['month'], 'url': '/' + row['page'].as_posix(),
            'date': row['date'].isoformat(), 'title': row['title'], 'author': row['author'],
            'body': row['body'], 'body_html': row['body_html'], 'references': row['references'],
            'attachments': [{'path': str(a['path']), 'name': a['name']} for a in row['attachments']],
            'downloads': [{'path': str(path), 'label': label} for path, label in row['downloads']],
            'source': {'format': row['source_format'], 'path': row['source_path']}}


def render_archive(root, site, rows):
    by_id = {(row['list'], row['id']): row for row in rows}
    groups = defaultdict(list)
    lists = defaultdict(list)
    for row in rows:
        row['parent'] = next((by_id[(row['list'], mid)] for mid in reversed(row['references']) if (row['list'], mid) in by_id and mid != row['id']), None)
        row['replies'] = []
        groups[(row['list'], row['month'])].append(row)
        lists[row['list']].append(row)
    for row in rows:
        if row['parent']:
            row['parent']['replies'].append(row)
    for name, messages in lists.items():
        for index, row in enumerate(messages):
            row['previous'] = messages[index - 1] if index else None
            row['next'] = messages[index + 1] if index + 1 < len(messages) else None
    records = []
    for row in rows:
        page = row['page']
        date = row['date']
        content = f'<article class="message"><p class="breadcrumb"><a href="../index.html">{escape(row["list"])}</a> / <a href="thread.html">{month_label(row["month"])}</a></p>'
        content += f'<h1>{escape(row["title"])}</h1><p class="message-meta"><strong>{escape(row["author"])}</strong> · <time datetime="{date.isoformat()}">{date.strftime("%d.%m.%Y %H:%M:%S %z")}</time></p>'
        content += index_nav() + '<nav class="message-nav">'
        for other, label in [(row['previous'], 'Vorherige Nachricht'), (row['next'], 'Nächste Nachricht'), (row['parent'], 'Antwort auf')]:
            if other:
                content += f'<a href="{relative(other["page"], page)}">{label}: {escape(other["title"])}</a>'
        content += '</nav><div class="message-body"><!--beginarticle-->' + row['body_html'] + '<!--endarticle--></div>'
        if row['attachments']:
            content += '<section><h2>Anhänge</h2><ul>' + ''.join(f'<li><a href="{relative(a["path"], page)}" download>{escape(a["name"])}</a></li>' for a in row['attachments']) + '</ul></section>'
        for target, payload in row.get('attachment_payloads', []):
            (site / target).parent.mkdir(parents=True, exist_ok=True)
            (site / target).write_bytes(payload)
        if row['source_format'] == 'mlmmj':
            download = row['downloads'][0][0]
            (site / download).parent.mkdir(parents=True, exist_ok=True)
            (site / download).write_bytes((root / row['source_path']).read_bytes())
        if row['replies']:
            content += '<section><h2>Antworten</h2><ul>' + ''.join(f'<li><a href="{relative(other["page"], page)}">{escape(other["title"])}</a> · {escape(other["author"])}</li>' for other in row['replies']) + '</ul></section>'
        content += ''.join(f'<p><a href="{relative(path, page)}" download>{label}</a></p>' for path, label in row['downloads']) + '</article>'
        (site / page).parent.mkdir(parents=True, exist_ok=True)
        (site / page).write_text(document(row['title'], content, page))
        records.append({'url': '/' + page.as_posix(), 'language': 'de',
                        'content': row['title'] + '\n' + row['author'] + '\n' + row['body'],
                        'meta': {'title': row['title'], 'author': row['author'], 'date': date.isoformat()},
                        'filters': {'Liste': [row['list']], 'Jahr': [row['month'][:4]]}})
    for name in LISTS:
        months = sorted((month for list_name, month in groups if list_name == name), key=month_key, reverse=True)
        page = Path(name) / 'index.html'
        content = f'<h1>{name}</h1><p>{len(lists[name]):,} archivierte Nachrichten</p>'.replace(',', '.')
        content += '<nav class="year-nav">' + ''.join(f'<a href="#jahr-{year}">{year}</a>' for year in sorted({m[:4] for m in months}, reverse=True)) + '</nav>'
        year = None
        for month in months:
            if year != month[:4]:
                if year is not None:
                    content += '</ul></section>'
                year = month[:4]
                content += f'<section><h2 id="jahr-{year}">{year}</h2><ul class="months">'
            content += f'<li><a href="{month}/thread.html">{month_label(month)}</a> · {len(groups[(name, month)])} Nachrichten</li>'
        if year is not None:
            content += '</ul></section>'
        (site / page).parent.mkdir(parents=True, exist_ok=True)
        (site / page).write_text(document(name, content, page))
        chronological = list(reversed(months))
        for index, month in enumerate(chronological):
            group = groups[(name, month)]
            for mode in ('thread', 'date', 'subject', 'author', 'index'):
                page = Path(name) / month / (mode + '.html')
                content = f'<h1>{name} · {month_label(month)}</h1><p>{len(group)} Nachrichten</p><nav class="month-nav"><a href="../index.html">Alle Monate</a>'
                for other, label in [(chronological[index - 1] if index else None, 'Vorheriger Monat'), (chronological[index + 1] if index + 1 < len(chronological) else None, 'Nächster Monat')]:
                    if other:
                        content += f'<a href="../{other}/thread.html">{label}: {month_label(other)}</a>'
                content += '</nav>' + index_nav()
                def item(row, nested=''):
                    return f'<li id="{row["anchor"]}"><a href="{relative(row["page"], page)}">{escape(row["title"])}</a><span class="entry-meta"> · {escape(row["author"])} · {row["date"].strftime("%d.%m. %H:%M")}</span>{nested}</li>'
                if mode in ('thread', 'index'):
                    members = {m['id'] for m in group}
                    children = defaultdict(list)
                    for entry in group:
                        parent = entry['parent']
                        children[parent['id'] if parent and parent['id'] in members else None].append(entry)
                    visited = set()
                    def subtree(entry):
                        if entry['id'] in visited:
                            return ''
                        visited.add(entry['id'])
                        nested = ''.join(subtree(child) for child in children[entry['id']])
                        return item(entry, '<ul>' + nested + '</ul>' if nested else '')
                    body = ''.join(subtree(entry) for entry in children[None])
                    body += ''.join(subtree(entry) for entry in group if entry['id'] not in visited)
                else:
                    key = (lambda row: row['title'].casefold()) if mode == 'subject' else (lambda row: row['author'].casefold()) if mode == 'author' else (lambda row: row['date'].timestamp())
                    body = ''.join(item(entry) for entry in sorted(group, key=key))
                content += '<ul id="start" class="message-index">' + body + '</ul><span id="end"></span>'
                for suffix in ('.txt', '.txt.gz'):
                    download = Path(name) / (month + suffix)
                    if (site / download).exists():
                        content += f'<p><a href="{relative(download, page)}" download>Monatsarchiv herunterladen ({suffix.lstrip(".")})</a></p>'
                (site / page).write_text(document(f'{name} · {month_label(month)}', content, page))
    return records, {name: len(lists[name]) for name in LISTS}, groups
