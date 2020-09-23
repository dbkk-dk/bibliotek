#!/usr/bin/env python3

import logging
import requests

LOGGER = logging.getLogger(__name__)

# validate isbn
# https://stackoverflow.com/a/14096142

def wquery(SERVICE_URL):
    resp = requests.get(SERVICE_URL)
    data = resp.json()
    LOGGER.debug("Raw data from service:\n%s", data)
    return data


def merge_data(data1, data2):
    """Merge values from data2 into data1 IF the values in data1 is empty or the
    keyword does not exist.

    Also returns the updated {key:values} in a separate dict, so we can update
    openlibrary with the missing data

    Test if dict is empty:
    bool({}) -> False
    not {} -> True
    len({}) -> 0

    """
    # this does not work; we need to treat empty strings
    # replacec values from data1 with these from data2
    # return {**data1, **data2}

    updated = {}
    res = data1.copy()
    for k, v in data2.items():
        if k not in data1 or data1[k] == "":
            res[k] = v
            updated[k] = v
    return res, updated
