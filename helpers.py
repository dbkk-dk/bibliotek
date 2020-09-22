#!/usr/bin/env python3

import logging
import requests

LOGGER = logging.getLogger(__name__)

def wquery(SERVICE_URL):
    resp = requests.get(SERVICE_URL)
    data = resp.json()
    LOGGER.debug("Raw data from service:\n%s", data)
    return data
