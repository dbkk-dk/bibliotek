#!/usr/bin/env python3
#
import functools
import logging
import pickle
import select
import sys

import serial
from serial.tools.list_ports import comports

from bookdb import create_connection, updatedb

logging.basicConfig(level=logging.DEBUG)
# set the root logger to debug. All other loggers ends here, due to chaining
root = logging.getLogger()
root.setLevel(logging.DEBUG)


BOOKS_DB = "books.sqlite"
SAVE_BARCODES = True

# default port on osx
port = "/dev/tty.usbserial"


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


def get_locations_id(conn):
    # returns a dict with location -> id mapping
    sql = "SELECT * FROM location"
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()  # (id, label_name, full_name)
    ids = {row[0]: (row[1], row[2]) for row in rows}
    return ids


# single_dispatch: A form of generic function dispatch where the implementation
# is chosen based on the type of a single argument.
# https://docs.python.org/3/library/functools.html#functools.singledispatch
# Another simple way to test if data is bytes and need to be decoded
# isinstance(barcode, (data, bytearray))
@functools.singledispatch
def decode(data):
    raise TypeError("Unknown type: " + repr(type(data)))


@decode.register(str)
def _(data):
    # data is a str
    return data.rstrip()


@decode.register(bytes)
@decode.register(bytearray)
def _(data):
    data = data.decode("utf-8")
    return decode(data)


conn = create_connection(BOOKS_DB)
id_loc_map = get_locations_id(conn)
# except KeyboardInterrupt:
#    port = None


KEEP_SQL = "UPDATE book SET in_lib = ? WHERE id = ?;"
MOVE_SQL = "UPDATE book SET location = ? WHERE id = ?;"

# different inputs to read from. Nonblocking by using select
inputs = [sys.stdin, ser]

unknown_isbns = []
try:
    while True:
        print("scan book")
        # read from multiple inputs
        (ready, [], []) = select.select(inputs, [], [])
        if not ready:
            continue
        else:
            for f in ready:
                # decode and strip newline
                barcode = f.readline()
                barcode = decode(barcode)

        print(barcode)

        data = {k: f"%{barcode}%" for k in ("isbn", "isbn_10", "isbn_13")}
        sql = " like ? or ".join(data.keys()) + " like ?"
        key = list(data.values())
        sql = (
            "SELECT id, title, authors, location, publisher, isbn, isbn_10, "
            "isbn_13 FROM book WHERE "
        ) + sql
        cur = conn.cursor()
        cur.execute(sql, key)
        book = cur.fetchone()

        if book:
            id, title, authors, location, publisher, isbn, isbn_10, isbn_13 = book
            isbns = (isbn, isbn_10, isbn_13)
            print(
                f"{id}, {title} -- {authors}\n shelf: {id_loc_map[location]}, {publisher}, {isbns}"
            )
            ret = input("Keep [Y/n]?, change loc [c] or dry-run [d]\n") or "y"
            if ret == "y":
                sql = KEEP_SQL
                data = 1
            elif ret == "n":
                sql = KEEP_SQL
                data = 0
            elif ret == "c":
                sql = MOVE_SQL
                data = input("New location\n")
            else:
                continue
            data = (data, id)
            updatedb(conn, sql, data)

        else:
            unknown_isbns.append(barcode)
            print(f"isbn {barcode} does not exist")
except KeyboardInterrupt:
    if SAVE_BARCODES:
        with open("unknown_barcodes.pickle", "rb") as f:
            old_data = pickle.load(f)
        d = {
            # save only unique isbns (in case the same book was scanned twice)
            "unknown_isbns": list(set(unknown_isbns + old_data["unknown_isbns"])),
        }
        # overwrite old data completely. Pickle streams are entirely
        # self-contained, so if data was appended with '+ab' we would only load
        # one pickle stream
        with open("unknown_barcodes.pickle", "wb") as f:
            pickle.dump(d, f)
