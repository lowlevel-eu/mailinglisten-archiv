from datetime import timedelta
from email.message import EmailMessage
from email import policy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from common import ArchiveHTML
from unified import load_messages, mailman_date, render_archive, serializable


class UnifiedTests(unittest.TestCase):
    def test_german_and_english_dates(self):
        self.assertEqual(mailman_date('Fr Mär 10 12:34:56 CET 2017').isoformat(), '2017-03-10T12:34:56+01:00')
        self.assertEqual(mailman_date('Sun May 07 18:45:42 CEST 2017').utcoffset(), timedelta(hours=2))
        self.assertEqual(mailman_date('Mo Dez 12 01:02:03 CET 2016').month, 12)
        with self.assertRaisesRegex(ValueError, 'Unrecognized'):
            mailman_date('unknown')

    def test_mixed_month_thread_and_chronological_navigation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            month = root / 'archives/tyndur-devel/2017-May'
            month.mkdir(parents=True)
            for number in (1, 2):
                text = (f'<html><head><title>Alter Patch {number}</title></head><body><b>Jörg</b>'
                        f'<i>Di Mai 0{number} 10:00:00 CEST 2017</i>'
                        f'<a href="mailto:test?In-Reply-To=%3Cold{number}%40example.org%3E">Mail</a>'
                        '<!--beginarticle-->\n<pre>+\tGrüße &lt;test&gt;\n</pre>\n<!--endarticle--></body></html>')
                (month / f'{number:06}.html').write_bytes(('<meta charset=iso-8859-1>' + text).encode('latin1'))
            (month / 'thread.html').write_text('<!--0 123- --><LI><A HREF="000001.html">root</A><UL><!--1 123-456- --><LI><A HREF="000002.html">reply</A></UL>')
            manifest = {}
            for number, date in [(3, 'Wed, 03 May 2017 10:00:00 +0200'), (4, 'Fri, 03 Jan 2020 10:00:00 +0100')]:
                message = EmailMessage(policy=policy.SMTP)
                message['Message-ID'] = f'<new{number}@example.org>'
                message['From'] = 'Jörg <joerg@example.org>'
                message['Date'] = date
                message['Subject'] = f'Neuer Patch {number}'
                message['References'] = '<old2@example.org>'
                message.set_content('+\tGrüße <test>\n')
                source = root / 'messages/tyndur-devel' / f'{number}.eml'
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_bytes(message.as_bytes())
                manifest[str(source.relative_to(root / 'messages'))] = hashlib.sha256(source.read_bytes()).hexdigest()
            (root / 'messages-manifest.json').write_text(json.dumps(manifest))
            rows = load_messages(root)
            self.assertEqual(len(rows), 4)
            self.assertEqual(rows[1]['references'], ['<old1@example.org>'])
            self.assertEqual(set(serializable(rows[0])), set(serializable(rows[2])))
            site = root / 'site'
            site.mkdir()
            records, counts, groups = render_archive(root, site, rows)
            self.assertEqual(counts['tyndur-devel'], 4)
            self.assertEqual(len(groups[('tyndur-devel', '2017-May')]), 3)
            old = (site / 'tyndur-devel/2017-May/000002.html').read_text()
            new = (site / 'tyndur-devel/2017-May/mlmmj-000003.html').read_text()
            for html in (old, new):
                self.assertIn('<article class="message">', html)
                self.assertIn('class="message-meta"', html)
                self.assertIn('class="message-body"', html)
            self.assertIn('href="mlmmj-000003.html">Nächste Nachricht', old)
            self.assertIn('href="000002.html">Antwort auf', new)
            self.assertIn('../2020-January/mlmmj-000004.html', new)
            thread = (site / 'tyndur-devel/2017-May/thread.html').read_text()
            self.assertIn('id="1"', thread)
            self.assertIn('id="2"', thread)
            self.assertIn('id="mlmmj-000003"', thread)
            self.assertIn('id="start"', thread)
            self.assertIn('id="end"', thread)
            self.assertIn('3 Nachrichten', thread)
            self.assertLess(thread.index('Alter Patch 1'), thread.index('Alter Patch 2'))
            self.assertLess(thread.index('Alter Patch 2'), thread.index('Neuer Patch 3'))
            landing = (site / 'tyndur-devel/index.html').read_text()
            self.assertIn('jahr-2017', landing)
            self.assertIn('jahr-2020', landing)
            self.assertNotIn('Neuere Nachrichten', landing)
            for row in rows:
                rendered = ArchiveHTML(row['page'])
                rendered.feed((site / row['page']).read_bytes().decode('utf-8'))
                self.assertEqual(''.join(rendered.text), row['body'])


if __name__ == '__main__':
    unittest.main()
