from email import policy
from email.message import EmailMessage
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build import LISTS, document, relative
from import_mlmmj import import_messages
from mlmmj import body_text, read_messages, linkify
from unified import load_messages, render_archive


def message(mid, subject='Grüße', date='Fri, 05 Mar 2021 10:00:00 +0100'):
    result = EmailMessage(policy=policy.SMTP)
    result['From'] = 'Jörg <joerg@example.org>'
    result['Date'] = date
    result['Subject'] = subject
    result['Message-ID'] = mid
    result.set_content('+\tif (x < y && z) {\n Grüße\n}\n')
    return result


class MlmmjTests(unittest.TestCase):
    def test_plain_alternative_and_html_fallback(self):
        mail = message('<one@example.org>')
        mail.add_alternative('<p>Duplicate alternative<script>bad()</script></p>', subtype='html')
        self.assertIn('Grüße', body_text(mail))
        self.assertNotIn('Duplicate', body_text(mail))
        html = EmailMessage()
        html.set_content('<p>Hallo &amp; Grüße</p><script>bad()</script>', subtype='html')
        self.assertEqual(body_text(html).strip(), 'Hallo & Grüße')

    def test_linkified_urls_keep_message_text(self):
        from build import ArchiveHTML, rewrite_link
        text = 'Grüße https://example.org/path_(x). http://[broken <script> & test'
        rendered = linkify(text, Path('tyndur-devel/2021-May/test.html'), rewrite_link)
        parser = ArchiveHTML(Path('test.html'))
        parser.feed('<body><!--beginarticle-->' + rendered + '<!--endarticle--></body>')
        self.assertEqual(''.join(parser.text), text)
        self.assertIn('href="https://example.org/path_(x)"', rendered)
        self.assertNotIn('href="http://[broken', rendered)
        self.assertIn('&lt;script&gt;', rendered)

    def test_deduplication_is_per_list_and_import_is_repeatable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'repo'
            source = Path(tmp) / 'source'
            for name in LISTS:
                old = root / 'archives' / name / '2017-May/000001.html'
                old.parent.mkdir(parents=True)
                old.write_text('<a href="mailto:test?In-Reply-To=%3Cold%40example.org%3E">mail</a>')
                directory = source / name
                directory.mkdir(parents=True)
                (directory / '1').write_bytes(message('<old@example.org>').as_bytes())
                (directory / '2').write_bytes(message('<crosspost@example.org>').as_bytes())
            result = import_messages(source, root)
            for name in LISTS:
                self.assertEqual(result[name]['new_messages'], 1)
                self.assertEqual(result[name]['overlap_with_mailman'], 1)
                self.assertFalse((root / 'messages' / name / '1.eml').exists())
                self.assertEqual((root / 'messages' / name / '2.eml').read_bytes(), (source / name / '2').read_bytes())
            self.assertEqual(len(read_messages(root)), 2)
            self.assertEqual(import_messages(source, root), result)
            (source / LISTS[0] / '2').write_bytes(message('<crosspost@example.org>', subject='changed').as_bytes())
            with self.assertRaisesRegex(ValueError, 'overwrite changed message'):
                import_messages(source, root)

    def test_threads_downloads_safe_attachment_names_and_patch_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = {}
            first = message('<one@example.org>')
            first.add_attachment(b'patch\r\n\xff', maintype='application', subtype='octet-stream', filename='../../Grüße.patch')
            reply = message('<two@example.org>', date='Sat, 03 Apr 2021 10:00:00 +0200')
            reply['References'] = '<one@example.org>'
            reply['In-Reply-To'] = '<one@example.org>'
            for index, mail in enumerate([first, reply], 1):
                source = root / 'messages/tyndur-devel' / f'{index}.eml'
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_bytes(mail.as_bytes())
                manifest[str(source.relative_to(root / 'messages'))] = hashlib.sha256(source.read_bytes()).hexdigest()
            (root / 'messages-manifest.json').write_text(json.dumps(manifest))
            (root / 'site').mkdir()
            records, counts, groups = render_archive(root, root / 'site', load_messages(root))
            self.assertEqual(counts['tyndur-devel'], 2)
            self.assertEqual(len(records), 2)
            reply_page = (root / 'site/tyndur-devel/2021-April/mlmmj-000002.html').read_text()
            self.assertIn('../2021-March/mlmmj-000001.html', reply_page)
            self.assertIn('Antwort auf', reply_page)
            attachments = list((root / 'site/tyndur-devel/attachments/mlmmj/1').iterdir())
            self.assertEqual(len(attachments), 1)
            self.assertEqual(attachments[0].read_bytes(), b'patch\r\n\xff')
            self.assertEqual((root / 'site/messages/tyndur-devel/1.eml').read_bytes(), first.as_bytes())
            self.assertIn('+\tif (x &lt; y &amp;&amp; z)', (root / 'site/tyndur-devel/2021-March/mlmmj-000001.html').read_text())


if __name__ == '__main__':
    unittest.main()
