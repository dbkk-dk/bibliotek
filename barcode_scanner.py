#!/usr/bin/env python3
#
from operator import itemgetter
import serial
from serial.tools.list_ports import comports
from bookdb import (
    insert_book,
    sanitize_metadata,
    create_connection,
    book_exist,
    updatedb,
    get_locations_id,
)
import logging
import pickle

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


# if __name__ == '__main__':

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

conn = create_connection(BOOKS_DB)
id_loc_map = get_locations_id(conn)
# except KeyboardInterrupt:
#    port = None


KEEP_SQL = 'UPDATE book SET in_lib = ? WHERE id = ?;'
MOVE_SQL = 'UPDATE book SET location = ? WHERE id = ?;'

unknown_isbns = []
try:
    while True:
        print('scan book')
        # with serial.Serial(port) as ser:
        # read bytes, convert to str and strip '\r\n'
        barcode = ser.readline().decode("utf-8").rstrip()
        print(barcode)

        data_dict = {k: barcode for k in ("isbn", "isbn_10", "isbn_13")}
        book = book_exist(conn, data_dict, all_true=False, return_bool=False)
        if book:
            id=book[0]
            title=book[1]
            author=book[3]
            location=book[7]
            publisher=book[12]
            isbns=(book[4], book[5], book[6])
            print(
                f"{id}, {title} -- {author}\n shelf: {location}, {publisher}, {isbns}"
            )
            ret = input('Keep [Y/n]?, change loc [c] or dry-run [d]\n') or 'y'
            if ret == 'y':
                sql = KEEP_SQL
                data = 1
            elif ret == 'n':
                sql = KEEP_SQL
                data = 0
            elif ret == 'c':
                sql = MOVE_SQL
                data = input('New location\n')
            else:
                continue
            data = (data, id)
            updatedb(conn, sql, data)

        else:
            unknown_isbns.append(barcode)
            print(f"isbn {barcode} does not exist")
except KeyboardInterrupt:
    if SAVE_BARCODES:
        d = {
        "unknown_isbns": unknown_isbns,
        }
        with open("unknown_barcodes.pickle", "wb") as f:
            pickle.dump(d, f)
