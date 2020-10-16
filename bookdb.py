#!/usr/bin/env python3

import sqlite3
from dbkkapi import COUNTRY_TABLE, LOC_TABLE
import argparse
from _exceptions import RecordMappingError, ISBNNotConsistentError
import logging

LOGGER = logging.getLogger(__name__)

"""update and insert books/locations into sqlite db.

Create the db from the command line:
sqlite3 < createdb.sqlite

Delete all cells in table
DELETE FROM book
"""


def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except sqlite3.Error as e:
        print(e)

    return conn


def updatedb(conn, sql, data):
    cur = conn.cursor()
    LOGGER.debug(f"sql={sql}; key={data}")
    if isinstance(data, list) and len(data) > 1:
        cur.executemany(sql, data)
    else:
        cur.execute(sql, data)
    conn.commit()
    return cur.lastrowid


def create_locations(conn):
    # populate locations in database
    sql = "INSERT INTO location(label_name, full_name) VALUES(?,?)"

    loc1 = [(v, k) for k, v in LOC_TABLE.items()]
    loc2 = [(f"2.{v}", k) for k, v in COUNTRY_TABLE.items()]
    loc = loc1 + loc2
    return updatedb(conn, sql, loc)


def get_locations_id(conn):
    # returns a dict with location -> id mapping
    # {1: ('5', 'Biografi/Erindringer/Historie'), 2: ('6', 'Blandet indhold'),
    sql = "SELECT * FROM location"
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()  # (id, label_name, full_name)
    ids = {row[0]: (row[1], row[2]) for row in rows}
    return ids


def book_exist(conn, data_dict, all_true=True, return_bool=True):
    """returns bool, depending on if the book exist or not

    data_dict is a dict containing the k,v used for the search, eg
    data_dict = {k: dbkk[k] for k in ('isbn',)}

    This function generates the sql statement and keys
    sql = 'isbn = ?; key': (isbn,)
    sql = 'title = ? and authors = ?'; key: (title, author)

    example
    SELECT count(*) FROM book WHERE title = 'Im steilen Eis - 80 Eiswände in den Alpen' and authors = 'Erich Vanis';
    """
    data = convert_list(data_dict)
    if all_true:
        sql = " = ? and ".join(data.keys()) + " = ?"
    else:
        sql = " = ? or ".join(data.keys()) + " = ?"
    key = list(data.values())

    # SELECT count(*) returns either (1,) or (0,).
    if return_bool:
        sql = "SELECT count(*) FROM book WHERE " + sql
    else:
        sql = "SELECT * FROM book WHERE " + sql

    LOGGER.debug(f"sql={sql}; key={key}")
    cur = conn.cursor()
    cur.execute(sql, key)

    if return_bool:
        res = bool(cur.fetchone()[0])
    else:
        res = cur.fetchone()
    # LOGGER.debug(res)
    return res


def insert_book(conn, data):
    # insert a new book, after checking if it exist

    d = {"title": data[7], "authors": data[8]}
    if book_exist(conn, d):
        return

    # do this a bit more dynamically
    # https://stackoverflow.com/a/39361069
    sql = """INSERT INTO book
    (isbn, isbn_10, isbn_13, olid, goodreads, lccn, oclc, title, authors,
    publisher, publish_date, number_of_pages, subjects,
    openlibrary_medcover_url, location, language, openlibrary_preview_url,
    description)
    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) """
    return updatedb(conn, sql, data)


def update_book(conn, data):
    return


def convert_list(d):
    for k, v in d.items():
        if isinstance(v, list):
            d[k] = "; ".join(v)
    return d


def sanitize_metadata(data):
    # convert data dict -> tuple to match sql database
    # as of python 3.7, dicts are guaranteed to be insertion ordered. Thus we
    # can just convert dict to tuple. For python < 3.7, this approach is error
    # phrone
    try:
        d = {}
        d["isbn"] = data.get("isbn", "")
        d["isbn_10"] = data.get("isbn_10", "")
        d["isbn_13"] = data.get("isbn_13", "")
        d["olid"] = data.get("openlibrary", "")
        d["goodreads"] = data.get("goodreads", "")
        d["lccn"] = data.get("lccn", "")
        d["oclc"] = data.get("oclc", "")
        d["title"] = data["title"]
        d["authors"] = data["authors"]
        d["publisher"] = data["publisher"]
        d["publish_date"] = data["year"]
        d["number_of_pages"] = data["pages"]
        d["subjects"] = data["categories"]
        d["openlibrary_medcover_url"] = data["thumbnail"]
        d["location"] = data["location"]
        d["langauge"] = data["language"]
        d["openlibrary_preview_url"] = data["preview_url"]
        d["description"] = data["description"]
    except KeyError as e:
        LOGGER.debug("RecordMappingError for %s with data %s", e, data)
        raise RecordMappingError(e)

    d = convert_list(d)
    return tuple(d.values())


if __name__ == "__main__":
    DB_FILE = "books.sqlite"
    conn = create_connection(DB_FILE)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--init",
        action="store_true",  # set to True if present
        help="Fill the locations table. Only to be run on new DBs",
    )
    args = parser.parse_args()

    # create locations. Only to be run once
    if args.init:
        r = create_locations(conn)


# id_loc_map = get_locations_id(conn)
# loc = id_loc_map[ret['Location']]
# data = (ret['ISBN-13'], ret['Olid'], ret['Title'], ret['Authors'], ret['Publisher'],
#         ret['Year'], ret['Pages'], ret['Categories'], ret['Cover'], loc)

# r = insert_book(data)
