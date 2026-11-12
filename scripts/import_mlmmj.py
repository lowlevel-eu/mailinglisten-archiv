#!/usr/bin/env python3
"""Import only public mlmmj archive messages not already represented by Pipermail."""
import argparse
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
import hashlib
import json
from pathlib import Path
import shutil
from build import ROOT, LISTS, decode_html
from mlmmj import message_id_from_html


def import_messages(source, root=ROOT):
    manifest = {}
    summary = {}
    pending = []
    for name in LISTS:
        directory = source / name
        if not directory.is_dir():
            raise ValueError('Missing public archive directory: ' + str(directory))
        existing = {message_id_from_html(decode_html(file.read_bytes()))
                    for file in (root / 'archives' / name).glob('*/[0-9]*.html')}
        ids = set()
        dates = []
        new = []
        overlap = 0
        for file in sorted(directory.iterdir(), key=lambda p: int(p.name) if p.name.isdecimal() else -1):
            if not file.is_file() or not file.name.isdecimal():
                continue
            message = BytesParser(policy=policy.default).parsebytes(file.read_bytes())
            mid = str(message.get('Message-ID', '')).strip()
            if not mid or mid in ids:
                raise ValueError('Missing or duplicate Message-ID: ' + str(file))
            ids.add(mid)
            date = parsedate_to_datetime(str(message['Date']))
            if date.tzinfo is None:
                raise ValueError('Date without UTC offset: ' + str(file))
            dates.append(date)
            if mid in existing:
                overlap += 1
                continue
            relative = Path(name) / (file.name + '.eml')
            digest = hashlib.sha256(file.read_bytes()).hexdigest()
            target = root / 'messages' / relative
            if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                raise ValueError('Refusing to overwrite changed message: ' + str(target))
            pending.append((file, target))
            manifest[str(relative)] = digest
            new.append({'source': file.name, 'message_id': mid, 'date': str(message['Date']), 'subject': str(message.get('Subject', ''))})
        summary[name] = {'source_messages': len(ids), 'overlap_with_mailman': overlap,
                         'mailman_only_messages': len(existing - ids), 'new_messages': len(new),
                         'latest': max(dates, key=lambda date: date.timestamp()).isoformat() if dates else None, 'new': new}
    # Never silently remove additional messages from an earlier import.
    previous = json.loads((root / 'messages-manifest.json').read_text()) if (root / 'messages-manifest.json').exists() else {}
    if previous.keys() - manifest.keys():
        raise ValueError('This import would remove previously imported messages')
    for source_file, target in pending:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_file, target)
    (root / 'messages-manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    (root / 'mlmmj-import.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archives', type=Path, help='Public mlmmj archives directory (containing list subdirectories)')
    args = parser.parse_args()
    summary = import_messages(args.archives)
    for name, row in summary.items():
        print(f'{name}: {row["new_messages"]} new, {row["overlap_with_mailman"]} already in Mailman, {row["mailman_only_messages"]} retained from Mailman only')
