#!/usr/bin/env python3
"""Verify source checksums, rendered message coverage and every local archive link."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit
from build import ROOT, ArchiveHTML, decode_html
from mlmmj import read_messages


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.ids.update(attrs[k] for k in ('id', 'name') if attrs.get(k))
        self.links.extend(attrs[k] for k in ('href', 'src') if attrs.get(k))


def verify(root=ROOT):
    site = (root / 'site').resolve()
    errors = []
    additional = {str(row['page']): row for row in read_messages(root)}
    with (root / 'build/messages.jsonl').open() as stream:
        normalized = [json.loads(line) for line in stream]
    unified = {row['url']: row for row in normalized}
    if len(unified) != len(normalized) or any(set(row) != set(normalized[0]) for row in normalized):
        errors.append('Duplicate messages or inconsistent normalized record fields')
    anchors = {}
    targets = set()
    pages = links = messages = 0
    for file in site.rglob('*.html'):
        if 'attachments' in file.relative_to(site).parts:
            continue  # Original attachment files remain byte-for-byte downloads.
        parser = Links()
        parser.feed(file.read_text())
        pages += 1
        anchors[file] = parser.ids
        if re.fullmatch(r'\d+\.html', file.name):
            messages += 1
            original = ArchiveHTML(file.relative_to(site))
            original.feed(decode_html((root / 'archives' / file.relative_to(site)).read_bytes()))
            rendered = ArchiveHTML(file.relative_to(site))
            rendered.feed(file.read_bytes().decode('utf-8'))
            if ''.join(rendered.text) != ''.join(original.text):
                errors.append(f'Changed message text: {file}')
        elif file.name.startswith('mlmmj-'):
            messages += 1
            row = additional[str(file.relative_to(site))]
            rendered = ArchiveHTML(file.relative_to(site))
            rendered.feed(file.read_bytes().decode('utf-8'))
            if ''.join(rendered.text) != row['body']:
                errors.append(f'Changed mlmmj message text: {file}')
        message_url = '/' + file.relative_to(site).as_posix()
        if message_url in unified:
            html = file.read_bytes().decode('utf-8')
            if '<article class="message">' not in html or 'class="message-meta"' not in html:
                errors.append('Missing unified message layout: ' + message_url)
            message = ArchiveHTML(file.relative_to(site))
            message.feed(html)
            if ''.join(message.text) != unified[message_url]['body']:
                errors.append('Normalized message differs from rendered body: ' + message_url)
        for link in parser.links:
            url = urlsplit(link)
            if url.scheme or url.netloc:
                continue
            links += 1
            if url.path.startswith('/'):
                errors.append(f'Root-absolute link: {file}: {link}')
                continue
            target = (file.parent / unquote(url.path)).resolve() if url.path else file
            if target.is_dir():
                target /= 'index.html'
            if not target.is_relative_to(site) or not target.is_file():
                errors.append(f'Missing target: {file.relative_to(site)}: {link}')
            elif url.fragment and 'attachments' not in target.relative_to(site).parts:
                targets.add((target, unquote(url.fragment)))
    for target, fragment in targets:
        if fragment not in anchors.get(target, set()):
            errors.append(f'Missing anchor: {target.relative_to(site)}#{fragment}')
    records = [json.loads(line) for line in (root / 'build/search-records.jsonl').read_text().splitlines()]
    for record in records:
        if not (site / record['url'].lstrip('/')).is_file():
            errors.append('Missing search target: ' + record['url'])
    manifest = json.loads((root / 'source-manifest.json').read_text())
    for name, digest in manifest.items():
        source = root / 'archives' / name
        if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
            errors.append('Changed source: ' + name)
        if source.suffix.lower() != '.html' or 'attachments' in source.parts:
            if hashlib.sha256((site / name).read_bytes()).hexdigest() != digest:
                errors.append('Changed download: ' + name)
    for row in additional.values():
        download = site / 'messages' / row['source'].relative_to(root / 'messages')
        if download.read_bytes() != row['source'].read_bytes():
            errors.append('Changed original message download: ' + str(download))
        for target, payload in row['attachments']:
            if (site / target).read_bytes() != payload:
                errors.append('Changed MIME attachment: ' + str(target))
    if len({record['url'] for record in records}) != len(records):
        errors.append('Duplicate search targets')
    report = json.loads((root / 'build/report.json').read_text())
    if messages != report['messages'] or len(records) != messages or len(normalized) != messages:
        errors.append('Message/search counts differ from build report')
    for name in ('pagefind.js', 'pagefind-ui.js', 'pagefind-ui.css'):
        if not (site / 'pagefind' / name).is_file():
            errors.append('Missing search bundle: ' + name)
    if errors:
        raise ValueError('\n'.join(errors[:60]) + f'\n{len(errors)} errors')
    print(f'Verified {messages:,} messages, {pages:,} pages, {links:,} local links and {len(manifest):,} source checksums')


if __name__ == '__main__':
    verify()
