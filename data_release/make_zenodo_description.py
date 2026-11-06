# -*- coding: utf-8 -*-
r"""Render README_release.md to zenodo_description.html (the Zenodo description field accepts HTML).

Usage: python -X utf8 -I make_zenodo_description.py [README_release.md] [zenodo_description.html]
The first heading of the README is dropped (Zenodo shows the record title itself), the
HTML comments around the file table are removed and bare URLs (the Zenodo DOI, the GitHub
repository) are turned into links (the README itself stays plain text).
"""
import re, sys
import markdown


def autolink(match):
    """Wraps a bare URL in <a>; trailing punctuation stays outside the link."""
    url, tail = match.group(0), ""
    while url and url[-1] in ".,;:)":
        url, tail = url[:-1], url[-1] + tail
    return f'<a href="{url}">{url}</a>{tail}'


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "README_release.md"
    dst = sys.argv[2] if len(sys.argv) > 2 else "zenodo_description.html"
    text = open(src, encoding="utf-8").read()
    text = re.sub(r"^# .*\n", "", text, count=1)          # drop the H1
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)     # drop HTML comments
    html = markdown.markdown(text, extensions=["tables"])
    html = re.sub(r"""(?<![="'>/\w])https?://[^\s<]+""", autolink, html)   # not inside an existing <a>
    open(dst, "w", encoding="utf-8", newline="\n").write(html)
    print(f"{dst}: {len(html):,} characters, {html.count('<table>')} table(s), {html.count('<h2>')} h2 heading(s), "
          f"{html.count('<a href=')} link(s)")

if __name__ == "__main__":
    main()
