import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

spec = importlib.util.spec_from_file_location('archive_build', Path(__file__).resolve().parents[1] / 'scripts/build.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class ArchiveTests(unittest.TestCase):
    def test_patch_unicode_and_whitespace_are_preserved(self):
        source = '<html><head><title>Größe &amp; Patch</title></head><body><b>Jörg</b><i>Datum</i><!--beginarticle--><pre>+\tif (x &lt; y &amp;&amp; z) {\n  Grüße &lt;test&gt;\n}\n</pre><!--endarticle--></body></html>'
        parser = builder.ArchiveHTML(Path('tyndur-devel/2010-May/000001.html'))
        parser.feed(builder.decode_html(b'<meta charset=iso-8859-1>' + source.encode('latin1')))
        self.assertEqual(''.join(parser.text), '+\tif (x < y && z) {\n  Grüße <test>\n}\n')
        rendered = builder.ArchiveHTML(parser.page)
        rendered.feed('<body><!--beginarticle-->' + ''.join(parser.output) + '<!--endarticle--></body>')
        self.assertIn('+\tif (x < y && z)', ''.join(rendered.text))
        self.assertEqual(''.join(parser.author), 'Jörg')

    def test_archive_urls_and_project_paths(self):
        page = Path('tyndur-devel/2010-May/000001.html')
        rewrite = lambda url: builder.rewrite_link(url, page)
        self.assertEqual(rewrite('http://list.tyndur.org/pipermail/tyndur-devel/attachments/a/file.patch'), '../attachments/a/file.patch')
        self.assertEqual(rewrite('https://list.tyndur.org/pipermail/cdi-devel/2010-May/thread.html#123'), '../../cdi-devel/2010-May/thread.html#123')
        self.assertEqual(rewrite('http://list.tyndur.org/pipermail/lost/'), '../index.html')
        self.assertEqual(rewrite('https://example.com/test?q=x#abc'), 'https://example.com/test?q=x#abc')
        self.assertIsNone(rewrite('javascript:alert(1)'))
        self.assertIsNone(rewrite('http://[broken'))

    def test_executable_markup_is_removed(self):
        parser = builder.ArchiveHTML(Path('index.html'))
        parser.feed('<body><script>alert(1)</script><pre onclick="bad()">safe &lt;script&gt;</pre><a href="javascript:bad()">text</a><iframe src="https://example.com">hidden</iframe></body>')
        result = ''.join(parser.output)
        self.assertEqual(result, '<pre>safe &lt;script&gt;</pre><a>text</a>')

    def test_build_downloads_and_source_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'static').mkdir()
            manifest = {}
            for name in builder.LISTS:
                page = root / 'archives' / name / '2010-May/000001.html'
                page.parent.mkdir(parents=True)
                page.write_text('<html><head><title>Test</title></head><body><b>Autor</b><i>Wed Mai 19 10:30:00 CEST 2010</i><a href="mailto:test?In-Reply-To=%3C' + name + '%40test%3E">Mail</a><!--beginarticle--><pre>patch\n</pre><!--endarticle--></body></html>')
                download = page.parent / 'test.patch'
                download.write_bytes(b'\xff\x00\n')
                for file in (page, download):
                    manifest[str(file.relative_to(root / 'archives'))] = hashlib.sha256(file.read_bytes()).hexdigest()
            (root / 'source-manifest.json').write_text(json.dumps(manifest))
            (root / 'messages-manifest.json').write_text('{}')
            report = builder.build(root)
            self.assertEqual(report['messages'], 2)
            self.assertEqual((root / 'site/tyndur-devel/2010-May/test.patch').read_bytes(), b'\xff\x00\n')
            records = [json.loads(row) for row in (root / 'build/search-records.jsonl').read_text().splitlines()]
            self.assertEqual(records[0]['filters']['Jahr'], ['2010'])
            builder.build(root)  # A marked generated directory can be rebuilt.
            page.write_text('changed')
            with self.assertRaisesRegex(ValueError, 'Source files differ'):
                builder.build(root)


if __name__ == '__main__':
    unittest.main()
