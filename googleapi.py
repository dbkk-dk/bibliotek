#!/usr/bin/env python3

"""Query googleapi for isbn
"""

import logging
from helpers import wquery
from _exceptions import RecordMappingError, ISBNNotConsistentError

LOGGER = logging.getLogger(__name__)

SERVICE_URL = (
    "https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
    "&fields=items/volumeInfo(title,subtitle,authors,publisher,publishedDate,"
    "language,industryIdentifiers,"
    "pageCount,imageLinks.thumbnail,categories,description"  # we want these extra fields
    ")&maxResults=1"
)


def _mapper(isbn, records):
    """Mapp: canonical <- records."""
    # canonical: ISBN-13, Title, Authors, Publisher, Year, Language
    try:

        canonical = {}
        canonical["ISBN-13"] = isbn
        title = records.get("title").replace(" :", ":")
        subtitle = records.get("subtitle")
        title = title + " - " + subtitle if subtitle else title
        canonical["Title"] = title
        authors =  records.get("authors", [""])
        canonical["Authors"] = " ;".join(authors)
        # see issue #64
        canonical["Publisher"] = records.get("publisher", "").strip('"')
        if "publishedDate" in records and len(records["publishedDate"]) >= 4:
            canonical["Year"] = records["publishedDate"][0:4]
        else:  # pragma: no cover
            canonical["Year"] = ""
        canonical["Language"] = records.get("language")
        canonical["Cover"] = records.get("imageLinks", {"thumbnail": ""}).get("thumbnail")
        canonical["Pages"] = records.get("pageCount")
        categories = records.get("categories", [""])
        canonical["Categories"] = " ;".join(categories)
        canonical["Description"] = records.get("description")

    except Exception:  # pragma: no cover
        LOGGER.debug("RecordMappingError for %s with data %s", isbn, records)
        raise RecordMappingError(isbn)
    return canonical


def _records(isbn, data):
    """Classify (canonically) the parsed data."""
    # put the selected data in records
    try:
        recs = data["items"][0]["volumeInfo"]
    except Exception:  # pragma: no cover
        # don't raise exception!
        LOGGER.debug('No data from "googleapi" for isbn %s', isbn)
        return {}

    # consistency check (isbn request = isbn response)
    if recs:
        ids = recs.get("industryIdentifiers", "")
        if "ISBN_13" in repr(ids) and isbn not in repr(ids):
            LOGGER.debug("ISBNNotConsistentError for %s (%s)", isbn, repr(ids))
            raise ISBNNotConsistentError("{0} not in {1}".format(isbn, repr(ids)))
    else:
        return {}

    # map canonical <- records
    return _mapper(isbn, recs)


def query(isbn):
    """Query the Google Books (JSON API v1) service for metadata."""
    data = wquery(SERVICE_URL.format(isbn=isbn))
    return _records(isbn, data)
