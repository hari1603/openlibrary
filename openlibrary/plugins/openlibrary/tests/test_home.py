import datetime
import pytest
import sys
import web

#from infogami.utils.view import render_template
#from openlibrary.app import render_template
from infogami.utils import template, context
from infogami.utils.macro import codemacros, macrostore, load_macros
from openlibrary.i18n import gettext
from openlibrary.core.admin import Stats
from bs4 import BeautifulSoup

import six

from openlibrary.core import cache
from openlibrary import core
from openlibrary.plugins.openlibrary import carousels
from openlibrary.core.models import Edition

class MockDoc(dict):
    def __init__(self, _id, *largs, **kargs):
        self.id = _id
        kargs['_key'] = _id
        super(MockDoc, self).__init__(*largs, **kargs)

    def __repr__(self):
        o = super(MockDoc, self).__repr__()
        return "<%s - %s>"%(self.id, o)


class TestHomeTemplates:
    def test_about_template(self, render_template):
        html = six.text_type(render_template("home/about"))
        assert "About the Project" in html

        blog = BeautifulSoup(html, "lxml").find("ul", {"id": "olBlog"})
        assert blog is not None
        assert len(blog.findAll("li")) == 0

        posts = [web.storage({
            "title": "Blog-post-0",
            "link": "http://blog.openlibrary.org/2011/01/01/blog-post-0",
            "pubdate": datetime.datetime(2011, 1, 1)
        })]
        html = six.text_type(render_template("home/about", blog_posts=posts))
        assert "About the Project" in html
        assert "Blog-post-0" in html
        assert "http://blog.openlibrary.org/2011/01/01/blog-post-0" in html

        blog = BeautifulSoup(html, "lxml").find("ul", {"id": "olBlog"})
        assert blog is not None
        assert len(blog.findAll("li")) == 1

    def test_stats_template(self, render_template):
        # Make sure that it works fine without any input (skipping section)
        html = six.text_type(render_template("home/stats"))
        assert html == ""

    def test_home_template(self, render_template, mock_site, monkeypatch):
        docs = [MockDoc(_id=datetime.datetime.now().strftime("counts-%Y-%m-%d"),
                        human_edits=1, bot_edits=1, lists=1,
                        visitors=1, loans=1, members=1,
                        works=1, editions=1, ebooks=1,
                        covers=1, authors=1, subjects=1)]* 100
        stats = dict(human_edits = Stats(docs, "human_edits", "human_edits"),
                     bot_edits   = Stats(docs, "bot_edits", "bot_edits"),
                     lists       = Stats(docs, "lists", "total_lists"),
                     visitors    = Stats(docs, "visitors", "visitors"),
                     loans       = Stats(docs, "loans", "loans"),
                     members     = Stats(docs, "members", "total_members"),
                     works       = Stats(docs, "works", "total_works"),
                     editions    = Stats(docs, "editions", "total_editions"),
                     ebooks      = Stats(docs, "ebooks", "total_ebooks"),
                     covers      = Stats(docs, "covers", "total_covers"),
                     authors     = Stats(docs, "authors", "total_authors"),
                     subjects    = Stats(docs, "subjects", "total_subjects"))

        mock_site.quicksave("/people/foo/lists/OL1L", "/type/list")
        web.template.Template.globals['cached_random_readable_works'] = lambda: []
        web.template.Template.globals['get_editions_by_ia_query'] = lambda: {}
        load_macros('openlibrary', lazy=True)
        html = six.text_type(render_template("home/index", stats=stats, test=True))
        headers = ["Classic Books", "Books We Love", "Recently Returned",
                   "Recently Added", "Textbooks", "Kids",
                   "Authors Alliance &amp; MIT Press"]
        for h in headers:
            assert h in html

        assert "Around the Library" in html
        assert "About the Project" in html


class Test_format_book_data:
    def test_all(self, mock_site, mock_ia):
        book = mock_site.quicksave("/books/OL1M", "/type/edition", title="Foo")
        work = mock_site.quicksave("/works/OL1W", "/type/work", title="Foo")

    def test_authors(self, mock_site, mock_ia):
        a1 = mock_site.quicksave("/authors/OL1A", "/type/author", name="A1")
        a2 = mock_site.quicksave("/authors/OL2A", "/type/author", name="A2")
        work = mock_site.quicksave("/works/OL1W", "/type/work", title="Foo",
                                   authors=[{"author": {"key": "/authors/OL2A"}}])

        book = mock_site.quicksave("/books/OL1M", "/type/edition", title="Foo")

        assert Edition.canonicalize(book)['authors'] == []

        # when there is no work and authors, the authors field must be
        # picked from the book
        book = mock_site.quicksave(
            "/books/OL1M", "/type/edition", title="Foo",
            authors=[{"key": "/authors/OL1A"}])
        assert (Edition.canonicalize(book)['authors'] ==
                [{"key": "/authors/OL1A", "name": "A1"}])

        # when there is work, the authors field must be picked from the work
        book = mock_site.quicksave("/books/OL1M", "/type/edition",
            title="Foo",
            authors=[{"key": "/authors/OL1A"}],
            works=[{"key": "/works/OL1W"}]
        )
        assert (Edition.canonicalize(book)['authors'] ==
                [{"key": "/authors/OL2A", "name": "A2"}])
