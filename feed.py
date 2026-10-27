"""Turn Letterboxd RSS items into titleless Micro.blog posts."""

from __future__ import annotations

import argparse
import html
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path


SOURCE = "https://letterboxd.com/iamioannis/rss/"
LETTERBOXD = "https://letterboxd.com"
NS = {"lb": "https://letterboxd.com"}


class ReviewText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"p", "div", "br", "li"} and self.parts:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        return re.sub(r"\n{3,}", "\n\n", "".join(self.parts)).strip()


def review_text(source_html: str) -> str:
    parser = ReviewText()
    parser.feed(source_html)
    return parser.text()


def make_post(item: ET.Element) -> str:
    source_title = html.unescape(item.findtext("title", default="").strip())
    title = item.findtext("lb:filmTitle", default="", namespaces=NS).strip()
    year = item.findtext("lb:filmYear", default="", namespaces=NS).strip()
    rating = item.findtext("lb:memberRating", default="", namespaces=NS).strip()
    link = item.findtext("link", default="").strip()
    description = review_text(item.findtext("description", default=""))
    if not title:
        title = item.findtext("title", default="").strip()
    if not title or not link.startswith(LETTERBOXD + "/"):
        raise ValueError("Letterboxd item lacks a title or valid link")

    stars = ""
    if rating:
        half_steps = round(float(rating) * 2)
        stars = "★" * (half_steps // 2) + ("½" if half_steps % 2 else "")
    header = f"🍿 {source_title or title + (', ' + year if year else '') + (' - ' + stars if stars else '')}"
    lines = [f"<p>{html.escape(header)}</p>"]
    if description:
        for paragraph in re.split(r"\n\s*\n", description):
            lines.append(f"<p>{html.escape(paragraph).replace(chr(10), '<br>')}</p>")
    lines.append(f'<p>🔗 <a href="{html.escape(link, quote=True)}">{html.escape(link)}</a></p>')
    return "\n".join(lines)


def convert(
    source_xml: bytes, *, after: datetime | None = None, previous_xml: bytes | None = None
) -> bytes:
    root = ET.fromstring(source_xml)
    source = root.find("channel")
    if source is None:
        raise ValueError("Source is not an RSS channel")

    out = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(out, "channel")
    for tag, value in (
        ("title", "Ioannis's Letterboxd posts"),
        ("link", SOURCE),
        ("description", "Letterboxd entries formatted for Micro.blog"),
    ):
        ET.SubElement(channel, tag).text = value

    seen: set[str] = set()
    old_items: list[ET.Element] = []
    if previous_xml:
        previous_root = ET.fromstring(previous_xml)
        for old in previous_root.findall("./channel/item"):
            guid = old.findtext("guid", default="").strip()
            if guid and guid not in seen:
                old_items.append(old)
                seen.add(guid)

    for item in source.findall("item"):
        date = item.findtext("pubDate", default="").strip()
        published = parsedate_to_datetime(date) if date else None
        if after and (not published or published.astimezone(timezone.utc) <= after):
            continue
        guid = item.findtext("guid", default="").strip() or item.findtext("link", default="").strip()
        if guid in seen:
            old_items = [old for old in old_items if old.findtext("guid", default="").strip() != guid]
        target = ET.SubElement(channel, "item")
        ET.SubElement(target, "link").text = item.findtext("link", default="")
        ET.SubElement(target, "guid", {"isPermaLink": "false"}).text = guid
        if date:
            ET.SubElement(target, "pubDate").text = date
        ET.SubElement(target, "description").text = make_post(item)
        seen.add(guid)
    for old in old_items:
        channel.append(old)
    return ET.tostring(out, encoding="utf-8", xml_declaration=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=SOURCE)
    parser.add_argument("--output", default="feed.xml")
    parser.add_argument("--after", help="Only include entries published after this ISO 8601 date/time")
    parser.add_argument("--previous-url", help="Existing output feed to retain older imported items")
    args = parser.parse_args()
    cutoff = datetime.fromisoformat(args.after.replace("Z", "+00:00")) if args.after else None
    if cutoff and cutoff.tzinfo is None:
        raise ValueError("--after requires a timezone, for example +00:00")
    request = urllib.request.Request(args.source, headers={"User-Agent": "LetterboxdMicroblogFeed/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        source_xml = response.read()
    previous_xml = None
    if args.previous_url:
        try:
            with urllib.request.urlopen(args.previous_url, timeout=20) as response:
                previous_xml = response.read()
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
    Path(args.output).write_bytes(convert(source_xml, after=cutoff, previous_xml=previous_xml))


if __name__ == "__main__":
    main()
