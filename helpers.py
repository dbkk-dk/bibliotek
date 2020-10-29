#!/usr/bin/env python3

import logging

import requests
import serial
from serial.tools.list_ports import comports

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


def ask_for_port():
    """Show a list of ports and ask the user for a choice. To make selection
    easier on systems with long device names, also allow the input of an index.
    """
    print("\n--- Available ports:\n")
    ports = []
    for n, (port, desc, hwid) in enumerate(sorted(comports()), 1):
        print("--- {:2}: {:20} {!r}".format(n, port, desc))
        ports.append(port)
    while True:
        port = input("--- Enter port index or full name: ")
        try:
            index = int(port) - 1
            if not 0 <= index < len(ports):
                print("--- Invalid index!")
                continue
        except ValueError:
            pass
        else:
            port = ports[index]
        return port


def get_serial_interface():
    """Get the serial interface, where the usb2serial device is connected"""

    # default port on osx
    port = "/dev/tty.usbserial"
    # Try the default macos port. If not working, ask user for port
    while True:
        try:
            ser = serial.Serial(port)
            print(f"reading from {ser.name}")
            break
        except serial.serialutil.SerialException:
            port = ask_for_port()
            # on macos there's cu.serial and tty.serial. The latter is read only,
            # so we use that.
            port = port.replace("cu.", "tty,")
    return ser
