#!/usr/bin/env python3
"""Build one searchable archive from Mailman and mlmmj sources; stdlib only."""
import hashlib
import json
from pathlib import Path
import shutil

from common import ArchiveHTML, decode_html, document, relative, rewrite_link, LISTS
from unified import load_messages, render_archive, serializable

ROOT = Path(__file__).resolve().parents[1]


def build(root=ROOT):
    source = root / 'archives'
    manifest = json.loads((root / 'source-manifest.json').read_text())
    actual = {str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in source.rglob('*') if p.is_file()}
    if actual != manifest:
        raise ValueError('Source files differ from source-manifest.json')
    rows = load_messages(root)
    site = root / 'site'
    marker = site / '.mailinglisten-generated'
    if site.exists():
        if not marker.is_file():
            raise ValueError('Refusing to replace an unmarked site directory')
        shutil.rmtree(site)
    site.mkdir()
    marker.touch()
    (site / '.nojekyll').touch()
    shutil.copytree(root / 'static', site / 'static')
    for file in sorted(source.rglob('*')):
        if not file.is_file():
            continue
        page = file.relative_to(source)
        if file.suffix.lower() == '.html' and 'attachments' not in page.parts:
            continue  # Every message and index is rendered from the unified records.
        target = site / page
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(file, target)
    records, counts, groups = render_archive(root, site, rows)
    content = '<h1>Lowlevel-Mailinglisten</h1><p>Hier findest du die alten Diskussionen und Patches aus unseren Mailinglisten – mit Diskussionsfäden, Anhängen und einer gemeinsamen Suche.</p><ul>'
    for name in LISTS:
        content += f'<li><a href="{name}/index.html">{name}</a> · {counts[name]:,} Nachrichten</li>'.replace(',', '.')
    content += '</ul><p><a href="search/index.html">Alle Mailinglisten durchsuchen</a></p>'
    (site / 'index.html').write_text(document('Mailinglisten-Archiv', content, Path('index.html')))
    (site / 'search').mkdir()
    (site / 'search/index.html').write_text(document('Suche', '<h1>Mailinglisten durchsuchen</h1><div id="search"></div><p id="search-error" hidden>Die Suche konnte nicht geladen werden. Bitte lade die Seite neu.</p>', Path('search/index.html'), search=True))
    output = root / 'build'
    output.mkdir(exist_ok=True)
    (output / 'messages.jsonl').write_text(''.join(json.dumps(serializable(row), ensure_ascii=False) + '\n' for row in rows))
    (output / 'search-records.jsonl').write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in records))
    report = {'messages': sum(counts.values()), 'lists': counts, 'search_records': len(records),
              'source_files': len(manifest), 'mlmmj_messages': sum(row['source_format'] == 'mlmmj' for row in rows),
              'months': len(groups), 'thread_replies': sum(row['parent'] is not None for row in rows)}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    return report


if __name__ == '__main__':
    build()
