"""Shared HTML parsing, link rewriting and page layout."""
from html import escape
from html.parser import HTMLParser
import os
from pathlib import Path
import re
from urllib.parse import quote, unquote, urlsplit, urlunsplit

LISTS = ('tyndur-devel', 'cdi-devel')
ALLOWED = set('a p ul ol li table tr th td thead tbody b strong i em pre code blockquote h1 h2 h3 h4 hr br span div dl dt dd sup sub tt u img'.split())
VOID = {'hr', 'br', 'img'}


def relative(target, page):
    return quote(os.path.relpath(target, page.parent).replace(os.sep, '/'), safe='/')


def rewrite_link(value, page):
    """Move old archive URLs to this project without rewriting external sites."""
    try:
        url = urlsplit(value)
    except ValueError:
        return None
    if url.scheme and url.scheme.lower() not in ('http', 'https', 'mailto'):
        return None
    if url.hostname in ('list.tyndur.org', 'lists.tyndur.org'):
        parts = unquote(url.path).strip('/').split('/')
        if len(parts) >= 2 and parts[0] == 'pipermail':
            name = 'tyndur-devel' if parts[1] == 'lost' else parts[1]
            if name in LISTS:
                target = Path(name).joinpath(*parts[2:])
                if url.path.endswith('/') or len(parts) == 2:
                    target /= 'index.html'
                return urlunsplit(('', '', relative(target, page), url.query, url.fragment))
        if len(parts) >= 3 and parts[:2] == ['mailman', 'listinfo']:
            name = 'tyndur-devel' if parts[2] == 'lost' else parts[2]
            if name in LISTS:
                return relative(Path(name) / 'index.html', page)
    return value


class ArchiveHTML(HTMLParser):
    """Keep archive markup and whitespace, discard executable markup and metadata."""
    def __init__(self, page):
        super().__init__(convert_charrefs=True)
        self.page = page
        self.body = False
        self.article = False
        self.title_tag = False
        self.skip = 0
        self.output = []
        self.text = []
        self.title = []
        self.author = []
        self.date = []
        self.capture = None

    def handle_comment(self, data):
        if data.strip() == 'beginarticle':
            self.article = True
            self.output.append('<!--beginarticle-->')
        elif data.strip() == 'endarticle':
            self.article = False
            self.output.append('<!--endarticle-->')

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'title':
            self.title_tag = True
        if tag == 'body':
            self.body = True
            return
        if tag in ('script', 'style', 'iframe', 'object'):
            self.skip += 1
        if not self.body or self.skip or tag not in ALLOWED:
            return
        if not self.text and tag in ('b', 'i') and not self.article:
            self.capture = tag
        kept = []
        for key, value in attrs.items():
            if value is None:
                continue
            if key in ('href', 'src'):
                value = rewrite_link(value, self.page)
                if value is not None:
                    kept.append((key, value))
            elif key in ('id', 'name', 'title', 'alt', 'colspan', 'rowspan'):
                kept.append((key, value))
        self.output.append('<' + tag + ''.join(f' {k}="{escape(v, quote=True)}"' for k, v in kept) + '>')

    def handle_endtag(self, tag):
        if tag == 'title':
            self.title_tag = False
        if tag == 'body':
            self.body = False
        if tag in ('script', 'style', 'iframe', 'object') and self.skip:
            self.skip -= 1
            return
        if self.body and not self.skip and tag in ALLOWED and tag not in VOID:
            self.output.append('</' + tag + '>')
        if tag == self.capture:
            self.capture = None

    def handle_data(self, data):
        if self.title_tag:
            self.title.append(data)
        if self.body and not self.skip:
            self.output.append(escape(data))
            if self.article:
                self.text.append(data)
            elif self.capture == 'b' and not self.author:
                self.author.append(data)
            elif self.capture == 'i' and not self.date:
                self.date.append(data)


def decode_html(data):
    match = re.search(rb'charset=([a-zA-Z0-9_-]+)', data, re.I)
    return data.decode(match[1].decode('ascii') if match else 'utf-8', errors='strict')


def document(title, content, page, search=False):
    css = relative(Path('static/style.css'), page)
    home = relative(Path('index.html'), page)
    search_url = relative(Path('search/index.html'), page)
    extras = ''
    if search:
        pf = relative(Path('pagefind/pagefind-ui'), page)
        js = relative(Path('static/search.js'), page)
        extras = f'<link rel="stylesheet" href="{pf}.css"><script defer src="{pf}.js"></script><script defer src="{js}"></script>'
    return ('<!doctype html><html lang="de"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{escape(title)} · Lowlevel-Mailinglisten</title><link rel="stylesheet" href="{css}">{extras}</head><body>'
            f'<header><nav><a href="{home}">Mailinglisten-Archiv</a><a href="{search_url}">Suche</a>'
            '<a href="https://lowlevel-eu.github.io/">Wiki- und Forumsarchiv</a></nav></header>'
            f'<main>{content}</main><footer>Ein schreibgeschütztes Archiv der Lowlevel-Mailinglisten.</footer></body></html>\n')

