#!/usr/bin/env python3

from bookdb import (
    insert_book,
    sanitize_metadata,
    create_connection,
    book_exist,
    updatedb,
    get_locations_id,
)
from isbnlib import is_isbn10, to_isbn13, to_isbn10, notisbn
import logging

logging.basicConfig(level=logging.DEBUG)
# set the root logger to debug. All other loggers ends here, due to chaining
root = logging.getLogger()
root.setLevel(logging.DEBUG)


BOOKS_DB = "books.sqlite"
conn = create_connection(BOOKS_DB)
id_loc_map = get_locations_id(conn)

"""Remember there can be multiple isbns in the isbn_10 field, due to errors in
the openlibrary.org db. Thus we must split on ';' and calculate isbn13 for all
of the them

"""


def set_isbn10():
    sql = 'select id, isbn from book where isbn_10 = ? and isbn != ?;'
    key = ('', '')
    cur = conn.cursor()
    cur.execute(sql, key)
    res = cur.fetchall()

    data = []
    for book in res:
        id, isbn = book
        if notisbn(isbn):
            print(f'error, id {id}, isbn {isbn} is not a valid isbn')
            continue
        isbn_10 = isbn

        data.append((isbn_10, id))

    sql = "UPDATE book SET isbn_10 = ? WHERE id = ?;"
    cur.executemany(sql, data)
    conn.commit()

try:
    sql = 'select id, isbn_10 from book where isbn_13 = ? and isbn_10 != ?;'
    key = ('', '')
    cur = conn.cursor()
    cur.execute(sql, key)
    res = cur.fetchall()

    data = []
    for book in res:
        id, isbns = book
        isbns = isbns.split('; ')
        isbn_13 = []
        for isbn_10 in isbns:
            if notisbn(isbn_10):
                print(f'error, id {id}, isbn_10 {isbn_10} is not a valid isbn')
                continue
            isbn_13.append(to_isbn13(isbn_10))
        data.append(("; ".join(isbn_13), id))

    sql = "UPDATE book SET isbn_13 = ? WHERE id = ?;"
    cur.executemany(sql, data)
    conn.commit()

except:
    pass
