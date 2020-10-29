#!/usr/bin/env python3

"""Scan a book using a barcode scanner or write the ISBN in the console.


The scanned book can be inserted/removed from the DB, by setting the field
`in_lib` to 1/0, or moved to another location. Both `isbn_10` and `isbn_13` can
be used.

If the book is not found in the `DB` the ISBN is appended to the
`unknown_barcodes.pickle` file.

"""


import functools
import logging
import pickle
import pprint
import select
import sys
import traceback

from isbnlib import notisbn

from bookdb import create_connection, get_locations_id, updatedb
from helpers import get_serial_interface

logging.basicConfig(level=logging.DEBUG)
# set the root logger to debug. All other loggers ends here, due to chaining
root = logging.getLogger()
root.setLevel(logging.DEBUG)


BOOKS_DB = "books.sqlite"
SAVE_BARCODES = True
UNKNOWN_ISBN_FILE = "unknown_barcodes.pickle"

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


def query_new_location():
    # query for new location.
    global loc_id_map
    first = True
    while True:
        try:
            ret = input("Indtast hylde. [l] to view loc, [ret] to keep current loc\n")
            if ret == "":
                return None
            data = loc_id_map[ret]
            break
        except KeyError as e:
            print(f"forkert hylde {e}")
            if first:
                pprint.pprint(id_loc_map)
                first = False
    return data


def load_unknown_isbns():
    try:
        # catch error if file not found. Another way to handle this, could
        # be to open as a+ instead of r, to make sure the file is created if
        # not found.
        # pickle throws an error(EOFError) if no data is found in the file.
        with open(UNKNOWN_ISBN_FILE, "rb") as f:
            old_data = pickle.load(f)
    except (EOFError, FileNotFoundError):
        old_data = {}
    return old_data


conn = create_connection(BOOKS_DB)
# {1: ('5', 'Biografi/Erindringer/Historie'), 2: ('6', 'Blandet indhold'), ...
id_loc_map = get_locations_id(conn)
loc_id_map = {v[0]: k for k, v in id_loc_map.items()}


KEEP_SQL = "UPDATE book SET in_lib = ? WHERE id = ?;"
MOVE_SQL = "UPDATE book SET location = ? WHERE id = ?;"

# different inputs to read from. Nonblocking by using select
try:
    ser = get_serial_interface()
    inputs = [sys.stdin, ser]
except KeyboardInterrupt:
    inputs = [sys.stdin]

unknown_isbns = load_unknown_isbns()
loc = None
ask_for_location = True
isbn = None
try:
    while True:
        print("scan book. [loc], [batch], [c].")
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

        if barcode == "loc":
            loc = query_new_location()
            continue
        if barcode == "batch":
            ask_for_location = not ask_for_location
            continue
        if barcode == "c":
            # get last scanned isbn - or last inserted isbn
            if not isbn:
                isbn = list(unknown_isbns)[-1]
            locid = unknown_isbns[isbn]
            print(f"Previous book: {isbn}, {id_loc_map[locid]}")
            locid = query_new_location() or locid
            unknown_isbns[isbn] = locid
            print(f"{isbn} updated to {id_loc_map[locid]}")
            continue

        if notisbn(barcode):
            print(f"Not valid isbn10/isbn13, {barcode}")
            continue

        isbn = barcode
        data = {k: f"%{isbn}%" for k in ("isbn", "isbn_10", "isbn_13")}
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
            ret = (
                input("Keep [Y/n]?, change loc [c], view loc [l] or dry-run [d]\n")
                or "y"
            )
            if ret == "y":
                sql = KEEP_SQL
                data = 1
            elif ret == "n":
                sql = KEEP_SQL
                data = 0
            elif ret == "c":
                data = query_new_location() or location
                sql = MOVE_SQL
            elif ret == "l":
                pprint.pprint(id_loc_map)
                data = query_new_location() or location
                sql = MOVE_SQL
            else:
                continue
            data = (data, id)
            updatedb(conn, sql, data)

        else:
            locid = None
            if isbn in unknown_isbns:
                locid = unknown_isbns[isbn]
                print(
                    f"isbn {isbn} already in unknown_isbns with loc {id_loc_map[locid]}"
                )
            if loc is None or ask_for_location or (locid is not None):
                loc = query_new_location() or locid
            unknown_isbns[isbn] = loc
            print(
                f"isbn {isbn} with loc {id_loc_map[loc]}."
                f" [c] to change location"
            )
except Exception as e:
    print(traceback.print_exc())
except KeyboardInterrupt:
    pass
finally:
    if SAVE_BARCODES:
        # overwrite old data completely. Pickle streams are entirely
        # self-contained, so if data was appended with '+ab' we would only load
        # one pickle stream
        with open(UNKNOWN_ISBN_FILE, "wb") as f:
            pickle.dump(unknown_isbns, f)
        print("unknown ISBNS saved")
        pprint.pprint(unknown_isbns)
