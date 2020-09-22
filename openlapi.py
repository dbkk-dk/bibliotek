#!/usr/bin/env python3

"""Query openlibrary using isbn
"""

import logging
import re
from helpers import wquery
from _exceptions import RecordMappingError, ISBNNotConsistentError

SERVICE_URL = (
    "http://openlibrary.org/api/books?bibkeys=" "ISBN:{isbn}&format=json&jscmd=data"
)
LOGGER = logging.getLogger(__name__)

# pylint: disable=broad-except
def _mapper(isbn, records):
    """Map canonical <- records."""
    # canonical:
    # -> ISBN-13, Title, Authors, Publisher, Year, Language
    try:
        # mapping: canonical <- records
        canonical = {}
        canonical["ISBN-13"] = isbn
        title = records.get("title").replace(" :", ":")
        subtitle = records.get("subtitle", "")
        title = title + " - " + subtitle if subtitle else title
        canonical["Title"] = title
        authors = [a["name"] for a in records.get("authors", ({"name": "",},),)]
        canonical["Authors"] = " ;".join(authors)
        canonical["Publisher"] = records.get("publishers", [{"name": "",},])[0]["name"]
        canonical["Year"] = ""
        strdate = records.get("publish_date")
        if strdate:  # pragma: no cover
            match = re.search(r"\d{4}", strdate)
            if match:
                canonical["Year"] = match.group(0)
        canonical["Language"] = records.get("language", "")
        canonical["Cover"] = records.get("cover", {"medium": "",}).get("medium")
        canonical["Pages"] = records.get("number_of_pages", "")
        canonical["Categories"] = records.get("subjects", [{"name": ""}])[0].get("name")
        canonical["Description"] = records.get("description", "")
        canonical["Olid"] = records.get("identifiers").get("openlibrary")[0]
        canonical["Preview"] = records.get("ebooks" , [{"preview_url": ""}])[0].get("preview_url")
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
