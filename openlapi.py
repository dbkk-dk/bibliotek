#!/usr/bin/env python3

"""Query openlibrary using isbn,

Example
https://openlibrary.org/api/books?bibkeys=ISBN:184195215X&jscmd=data&format=json

Search for a book on openlibrary.org, using title and optionally author
"""

import logging
import re
from helpers import wquery
from _exceptions import RecordMappingError, ISBNNotConsistentError
import argparse
from olclient.openlibrary import OpenLibrary
import olclient.common as ol_common


SERVICE_URL = (
    "http://openlibrary.org/api/books?bibkeys=" "{bibkey}:{key}&format=json&jscmd=data"
)
LOGGER = logging.getLogger(__name__)


def get_identifiers(identifiers):
    # returns dict, {'isbn_10': val, 'isbn_13': val, 'goodreads': val, etc}
    identifiers = {k.lower(): v for k, v in identifiers.items()}
    return identifiers


# pylint: disable=broad-except
def _mapper(records):
    """Map canonical <- records."""
    # canonical:
    # -> ISBN-13, Title, Authors, Publisher, Year, Language
    LOGGER.debug(records)
    try:
        # mapping: canonical <- records
        canonical = {}
        # canonical["isbn"] = isbn
        title = records.get("title").replace(" :", ":")
        subtitle = records.get("subtitle", "")
        title = title + " - " + subtitle if subtitle else title
        canonical["title"] = title
        authors = [
            a["name"]
            for a in records.get(
                "authors",
                (
                    {
                        "name": "",
                    },
                ),
            )
        ]
        canonical["authors"] = authors
        canonical["publisher"] = records.get("publishers", [{"name": "",},])[
            0
        ]["name"]
        canonical["year"] = ""
        strdate = records.get("publish_date")
        if strdate:  # pragma: no cover
            match = re.search(r"\d{4}", strdate)
            if match:
                canonical["year"] = match.group(0)
        canonical["language"] = records.get("language", "")
        canonical["thumbnail"] = records.get(
            "cover",
            {
                "medium": "",
            },
        ).get("medium")
        canonical["pages"] = records.get("number_of_pages", "")
        canonical["categories"] = records.get("subjects", [{"name": ""}])[0].get("name")
        canonical["description"] = records.get("description", "")
        canonical["preview_url"] = records.get("ebooks", [{"preview_url": ""}])[0].get(
            "preview_url"
        )
        identifiers = records["identifiers"]
        d = get_identifiers(identifiers)
        canonical = {**canonical, **d}
    except Exception:  # pragma: no cover
        raise RecordMappingError(records)
    return canonical


# pylint: disable=broad-except
def _records(key, bibkey, data):
    """Classify (canonically) the parsed data."""

    # extract the given record, ie. the data recieved is:
    # {'OLID:OL11372034M': { ... }
    keystr = f"{bibkey.upper()}:{key}"
    try:
        # put the selected data in records
        records = data[keystr]
    except Exception:  # pragma: no cover
        # don't raise exception!
        LOGGER.debug(f'No data from "openlapi" for {keystr}')
        return {}

    # map canonical <- records
    return _mapper(records)


def query(key, bibkey="ISBN"):
    ALLOWED_KEYS = ["ISBN", "LCCN", "OCLC", "OLID"]
    """Query the openlibrary.org service for metadata."""
    if not bibkey.upper() in ALLOWED_KEYS:
        raise KeyError(f"wrong bibkey {bibkey}. Not of the type {ALLOWED_KEYS}")
    data = wquery(SERVICE_URL.format(bibkey=bibkey, key=key))
    return _records(key, bibkey, data)


def create_book(data):
    # create an `OL` book instance using title and author.
    # Needed for `seach_book`

    # fields we expect to always exist
    title = data["title"]
    authors = [ol_common.Author(name=author_name) for author_name in data["authors"]]

    # Extract fields that may not exist
    industry_identifiers = None  # data.get("isbn")
    number_of_pages = data.get("pages")
    publisher = data.get("publisher")
    publish_date = data.get("year")
    cover_url = None
    return ol_common.Book(
        title=title,
        number_of_pages=number_of_pages,
        identifiers=industry_identifiers,
        authors=authors,
        publisher=publisher,
        publish_date=publish_date,
        cover=cover_url,
    )


def search_book(ol_book):
    "Search for a book using title and author"

    OL = OpenLibrary()
    work = OL.Work.search(title=ol_book.title, author=ol_book.primary_author.name)

    LOGGER.debug(
        f"Work found from search using:"
        f"{ol_book.primary_author.name}: {ol_book.title}\n"
        f"{work}"
    )

    try:
        identifiers = get_identifiers(work.identifiers)
        olid = identifiers["olid"][0]
    except:
        olid = ""
        work = {}

    return olid, work


def parse_edition(edition):
    # parse Edition info from the `OL`
    d = {}
    d["authors"] = [authors.name for authors in edition["authors"]]
    d["olid"] = edition["olid"]
    d["date"] = edition.get("publish_date")
    title = edition.get("title").replace(" :", ":")
    subtitle = edition.get("subtitle", "")
    title = title + " - " + subtitle if subtitle else title
    d["title"] = title
    d["publisher"] = edition.get("publishers")
    return d


def get_edition_from_work(olid):
    """Get Work and related Editions from Work olid

    The individual editions are parsed and merged into a dict"""

    # determine if we have an Edition(M) or Work(W) olid.
    if olid.endswith("M"):
        olids = [olid]
    elif olid.endswith("W"):
        OL = OpenLibrary()
        # get work and related Editions. Convert Edition class to dict
        work = OL.Work.get(olid)
        editions = [vars(e) for e in work.editions]
        olids = [edition["olid"] for edition in editions]
    else:
        raise KeyError(f"missing/wrong Work olid. Should end with 'M' or 'W'")

    # For simplicity we lookup the Edition olid using request, instead of
    # parsing the OL class
    d = {}
    for olid in olids:
        res = query(olid, bibkey="OLID")
        d = {**d, **res}
        # LOGGER.debug(f"{olid}: {res}")
    return d


def main():
    global OL
    OL = OpenLibrary()

    parser = argparse.ArgumentParser()
    parser.add_argument("--title", required=True)
    parser.add_argument("--author", default="", required=False)
    args = parser.parse_args()

    data = {}
    data["title"] = args.title
    data["authors"] = [author for author in args.author.split("; ")]
    book = create_book(data)
    return book, search_book(book)


if __name__ == "__main__":
    book, result = main()
