#!/usr/bin/env python3


"""This script polulates the isbn fields in the DB, if some are missing.

The DB have the fields:
 | isbn | isbn_10 | isbn_13 |

isbn is read from old .mdb DB and inserted if verified(ie correct isbn). isbn_10
and isbn_13 are populated from the info from openlibrary and google-books.

If isbn_10 is missing and isbn is present, copy from isbn. If isbn_13 is missing
and isbn_10 present, calculate isbn_13. isbn will always be the original from
the .mdb DB.

"""

import argparse
import logging

from isbnlib import notisbn, to_isbn13

from bookdb import create_connection

logging.basicConfig(level=logging.DEBUG)
# set the root logger to debug. All other loggers ends here, due to chaining
root = logging.getLogger()
root.setLevel(logging.DEBUG)


BOOKS_DB = "books.sqlite"
conn = create_connection(BOOKS_DB)


def set_isbn10():
    """if isbn10 is empty, copy from from isbn"""
    sql = "select id, isbn from book where isbn_10 = ? and isbn != ?;"
    key = ("", "")
    cur = conn.cursor()
    cur.execute(sql, key)
    res = cur.fetchall()

    data = []
    for book in res:
        id, isbn = book
        if notisbn(isbn):
            print(f"error, id {id}, isbn {isbn} is not a valid isbn")
            continue
        isbn_10 = isbn

        data.append((isbn_10, id))

    sql = "UPDATE book SET isbn_10 = ? WHERE id = ?;"
    cur.executemany(sql, data)
    conn.commit()


def set_isbn13():
    """If isbn13 is empty, calculate it from isbn10

    Remember there can be multiple isbns in the isbn_10 field, due to errors in
    the openlibrary.org db. Thus we must split on ';' and calculate isbn13 for
    all of the them"""

    sql = "select id, isbn_10 from book where isbn_13 = ? and isbn_10 != ?;"
    key = ("", "")
    cur = conn.cursor()
    cur.execute(sql, key)
    res = cur.fetchall()

    data = []
    for book in res:
        id, isbns = book
        isbns = isbns.split("; ")
        isbn_13 = []
        for isbn_10 in isbns:
            if notisbn(isbn_10):
                print(f"error, id {id}, isbn_10 {isbn_10} is not a valid isbn")
                continue
            isbn_13.append(to_isbn13(isbn_10))
        data.append(("; ".join(isbn_13), id))

    sql = "UPDATE book SET isbn_13 = ? WHERE id = ?;"
    cur.executemany(sql, data)
    conn.commit()


def main():
    # If no arg is given, run the default which is to show the usage
    # https://stackoverflow.com/a/40613995
    parser = argparse.ArgumentParser()
    parser.set_defaults(func=lambda x: parser.print_usage())
    parser.add_argument(
        # https://docs.python.org/3/library/argparse.html#action
        "--isbn10",
        required=False,
        action="store_true",  # set to True if present
    )
    parser.add_argument("--isbn13", required=False, action="store_true")
    args = parser.parse_args()
    args.func(args)
    try:
        if args.isbn10:
            set_isbn10()
        if args.isbn13:
            set_isbn13()
    except:
        pass


if __name__ == "__main__":
    main()
