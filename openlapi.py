#!/usr/bin/env python3

"""Query openlibrary using isbn,

Example
https://openlibrary.org/api/books?bibkeys=ISBN:184195215X&jscmd=data&format=json
"""

import logging
import re
from helpers import wquery
from _exceptions import RecordMappingError, ISBNNotConsistentError

SERVICE_URL = (
    "http://openlibrary.org/api/books?bibkeys=" "ISBN:{isbn}&format=json&jscmd=data"
)
LOGGER = logging.getLogger(__name__)

def olib_identifiers(identifiers):
    # returns dict, {'isbn_10': val, 'isbn_13': val, 'goodreads': val, etc}
    identifiers = {k.lower(): v[0] for k, v in identifiers.items()}
    if ("isbn_10" not in identifiers) and ("isbn_13" not in identifiers):
        raise KeyError(f"missing isbn in {identifiers}")
    return identifiers


# pylint: disable=broad-except
def _mapper(isbn, records):
    """Map canonical <- records."""
    # canonical:
    # -> ISBN-13, Title, Authors, Publisher, Year, Language
    try:
        # mapping: canonical <- records
        canonical = {}
        canonical["isbn"] = isbn
        title = records.get("title").replace(" :", ":")
        subtitle = records.get("subtitle", "")
        title = title + " - " + subtitle if subtitle else title
        canonical["title"] = title
        authors = [a["name"] for a in records.get("authors", ({"name": "",},),)]
        canonical["authors"] = " ;".join(authors)
        canonical["publisher"] = records.get("publishers", [{"name": "",},])[0]["name"]
        canonical["year"] = ""
        strdate = records.get("publish_date")
        if strdate:  # pragma: no cover
            match = re.search(r"\d{4}", strdate)
            if match:
                canonical["year"] = match.group(0)
        canonical["language"] = records.get("language", "")
        canonical["thumbnail"] = records.get("cover", {"medium": "",}).get("medium")
        canonical["pages"] = records.get("number_of_pages", "")
        canonical["categories"] = records.get("subjects", [{"name": ""}])[0].get("name")
        canonical["description"] = records.get("description", "")
        canonical["preview_url"] = records.get("ebooks" , [{"preview_url": ""}])[0].get("preview_url")
        identifiers = records["identifiers"]
        d = olib_identifiers(identifiers)
        canonical = {**canonical, **d}
    except Exception:  # pragma: no cover
        LOGGER.debug("RecordMappingError for %s with data %s", isbn, records)
        raise RecordMappingError(isbn)
    return canonical


# pylint: disable=broad-except
def _records(isbn, data):
    """Classify (canonically) the parsed data."""
    try:
        # put the selected data in records
        records = data["ISBN:%s" % isbn]
    except Exception:  # pragma: no cover
        # don't raise exception!
        LOGGER.debug('No data from "openlapi" for isbn %s', isbn)
        return {}

    # this will fail if we supply ISBN13 and the book exist with ISBN10
    # # consistency check (isbn request = isbn response)
    # if records:
    #     ids = records.get("identifiers", "")
    #     if isbn not in repr(ids):
    #         LOGGER.debug("ISBNNotConsistentError for %s (%s)", isbn, repr(ids))
    #         raise ISBNNotConsistentError("{0} not in {1}".format(isbn, repr(ids)))
    # else:
    #     return {}

    # map canonical <- records
    return _mapper(isbn, records)


def query(isbn):
    """Query the openlibrary.org service for metadata."""
    data = wquery(SERVICE_URL.format(isbn=isbn))
    return _records(isbn, data)
