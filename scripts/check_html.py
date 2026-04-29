#!/usr/bin/env python3
"""
Autograder for Lab 1a (HTML Profile + About Us).

Runs from the repo root. Prints a short OK/FAIL message.
Exits 0 on pass, non-zero on fail (which is what GitHub Classroom
autograding reads to award/withhold points for each test).

Usage:
    python3 scripts/check_html.py <test_name>

No external dependencies -- uses Python stdlib only.
"""

import os
import re
import sys
from html.parser import HTMLParser


# ----- helpers ---------------------------------------------------------------

def read(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def ok(msg=""):
    print(f"OK {msg}".strip())
    sys.exit(0)


class Collector(HTMLParser):
    """Walk the HTML and remember the tags + attributes we care about."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tag_counts = {}
        self.tags = []           # list of (tag, dict(attrs))
        self.h1_count = 0
        self.images = []         # list of dicts of attrs for <img>
        self.inputs = []
        self.labels_for = set()  # ids referenced by <label for="...">
        self.links = []
        self.has_doctype = False
        self.html_lang = None
        self.has_charset = False
        self.has_viewport = False
        self.title = None
        self._in_title = False
        self.tables = []         # list of dict(thead=bool, body_rows=int)
        self._table_stack = []
        self._in_thead = False
        self._tbody_rows = 0

    def handle_decl(self, decl):
        if decl.lower().startswith("doctype"):
            self.has_doctype = True

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        self.tags.append((tag, a))
        self.tag_counts[tag] = self.tag_counts.get(tag, 0) + 1

        if tag == "html":
            self.html_lang = a.get("lang")
        elif tag == "meta":
            if a.get("charset"):
                self.has_charset = True
            if a.get("name", "").lower() == "viewport":
                self.has_viewport = True
        elif tag == "title":
            self._in_title = True
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "img":
            self.images.append(a)
        elif tag == "input":
            self.inputs.append(a)
        elif tag == "label":
            if a.get("for"):
                self.labels_for.add(a["for"])
        elif tag == "a":
            self.links.append(a)
        elif tag == "table":
            self._table_stack.append({"thead": False, "body_rows": 0})
            self._in_thead = False
            self._tbody_rows = 0
        elif tag == "thead":
            if self._table_stack:
                self._table_stack[-1]["thead"] = True
            self._in_thead = True
        elif tag == "tbody":
            self._in_thead = False
        elif tag == "tr":
            if self._table_stack and not self._in_thead:
                self._table_stack[-1]["body_rows"] += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "thead":
            self._in_thead = False
        elif tag == "table":
            if self._table_stack:
                self.tables.append(self._table_stack.pop())

    def handle_data(self, data):
        if self._in_title:
            self.title = (self.title or "") + data


def parse(path):
    src = read(path)
    if src is None:
        fail(f"Required file missing: {path}")
    p = Collector()
    p.feed(src)
    return src, p


# ----- tests -----------------------------------------------------------------

REQUIRED_FILES = [
    "index.html",
    "about.html",
    "README.md",
]


def t_files():
    missing = [f for f in REQUIRED_FILES if not os.path.exists(f)]
    if missing:
        fail("missing required file(s): " + ", ".join(missing))

    # at least one image in images/
    has_image = False
    if os.path.isdir("images"):
        for f in os.listdir("images"):
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg")):
                has_image = True
                break
    if not has_image:
        fail("no profile image found in images/")

    ok("all required files present")


def t_index_structure():
    src, p = parse("index.html")
    if not p.has_doctype:
        fail("index.html: missing <!DOCTYPE html>")
    if not p.html_lang:
        fail('index.html: <html> needs a lang attribute, e.g., <html lang="en">')
    if not p.has_charset:
        fail("index.html: missing <meta charset>")
    if not p.has_viewport:
        fail("index.html: missing <meta name='viewport'>")
    if not p.title or len(p.title.strip()) < 5:
        fail("index.html: <title> is missing or too short")
    ok("index.html structure OK")


def t_index_semantic():
    src, p = parse("index.html")
    required = ["header", "nav", "main", "section", "footer"]
    missing = [t for t in required if p.tag_counts.get(t, 0) == 0]
    if missing:
        fail("index.html: missing semantic tag(s): " + ", ".join(missing))
    ok("index.html semantic tags OK")


def t_index_h1():
    _, p = parse("index.html")
    if p.h1_count != 1:
        fail(f"index.html: must have exactly ONE <h1>, found {p.h1_count}")
    ok("exactly one <h1>")


def t_index_a11y():
    _, p = parse("index.html")
    # all images have alt (may be empty for decorative)
    for img in p.images:
        if "alt" not in img:
            fail("index.html: an <img> is missing the alt attribute")
    if len(p.images) == 0:
        fail("index.html: at least one <img> required (your profile photo)")

    # every input must have id and a matching <label for=id>
    for inp in p.inputs:
        if not inp.get("id"):
            fail("index.html: every <input> must have an id")
        if inp["id"] not in p.labels_for:
            fail(f"index.html: input id={inp['id']!r} has no matching <label for=\"{inp['id']}\">")
    ok("a11y checks OK")


def t_index_form():
    _, p = parse("index.html")
    types = [i.get("type", "text").lower() for i in p.inputs]
    if "text" not in types:
        fail("index.html: contact form needs <input type='text'>")
    if "email" not in types:
        fail("index.html: contact form needs <input type='email'>")
    if p.tag_counts.get("textarea", 0) < 1:
        fail("index.html: contact form needs a <textarea>")
    if p.tag_counts.get("button", 0) < 1:
        fail("index.html: contact form needs a <button>")
    ok("contact form OK")


def t_about_structure():
    src, p = parse("about.html")
    if not p.has_doctype:
        fail("about.html: missing <!DOCTYPE html>")
    required = ["header", "nav", "main", "section", "footer"]
    missing = [t for t in required if p.tag_counts.get(t, 0) == 0]
    if missing:
        fail("about.html: missing semantic tag(s): " + ", ".join(missing))
    # nav must link to index.html
    href_targets = [a.get("href", "") for a in p.links]
    if not any("index.html" in h for h in href_targets):
        fail("about.html: nav must link back to index.html")
    ok("about.html structure OK")


def t_about_table():
    _, p = parse("about.html")
    if not p.tables:
        fail("about.html: needs at least one <table>")
    good = [t for t in p.tables if t["thead"] and t["body_rows"] >= 3]
    if not good:
        fail("about.html: <table> must have <thead> and at least 3 data rows in <tbody>")
    ok("table OK")


def t_about_external():
    _, p = parse("about.html")
    external = []
    for a in p.links:
        href = a.get("href", "")
        if href.startswith("http://") or href.startswith("https://"):
            external.append(a)
    if not external:
        fail("about.html: needs at least one external link (http/https)")

    safe = [a for a in external
            if "_blank" in a.get("target", "")
            and "noopener" in a.get("rel", "")]
    if not safe:
        fail("about.html: external link must use target='_blank' rel='noopener noreferrer'")
    ok("external link OK")


# ----- dispatcher ------------------------------------------------------------

TESTS = {
    "files":            t_files,
    "index_structure":  t_index_structure,
    "index_semantic":   t_index_semantic,
    "index_h1":         t_index_h1,
    "index_a11y":       t_index_a11y,
    "index_form":       t_index_form,
    "about_structure":  t_about_structure,
    "about_table":      t_about_table,
    "about_external":   t_about_external,
}


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in TESTS:
        print(f"Usage: {sys.argv[0]} <test_name>")
        print("Available tests: " + ", ".join(TESTS))
        sys.exit(2)
    TESTS[sys.argv[1]]()
