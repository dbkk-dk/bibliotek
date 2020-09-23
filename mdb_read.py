#!/usr/bin/env python3

from isbnlib import meta, cover, classify, desc, canonical, to_isbn13, notisbn
from isbnlib.registry import bibformatters, add_service

# my libs
from googleapi import query as gquery
from openlapi import query as oquery
from dbkkapi import query as dbkkquery
from bookdb import (insert_book, sanitize_metadata, create_connection,
                    book_exist, get_locations_id)
from helpers import merge_data
from olib_add_new_book import add_book

import numpy as np
import pandas as pd
import pandas_access as mdb
from copy import deepcopy
import logging

# set the root logger to debug. All other loggers ends here, due to chaining
root = logging.getLogger()
root.setLevel(logging.DEBUG)

UPDATE_DB = False

db_filename = "bjerg2003.mdb"
BOOKS_DB = "books.sqlite"
f_isbn = "books_isbn.csv"
f_noisbn = "books_no_isbn.csv"

# Listing the tables.
for tbl in mdb.list_tables(db_filename):
    print(tbl)

# merge de to tabeller
df1 = mdb.read_table(db_filename, "Udgave", dtype={"Sideantal": "string"})
df2 = mdb.read_table(db_filename, "Titel")
df = pd.merge(left=df1, right=df2, left_on="Titel", right_on="Titel")

# Convert missing data Na or NaN to empty strings
# Not for Land, as we use books with NaN to indicate wrong placement
df['Forfatter'] = df['Forfatter'].fillna('')
df['Sideantal'] = df['Sideantal'].fillna('')

data_isbn = []
data_noisbn = []

data_oquery = []
data_gquery = []
data_dbkkquery = []

# create conection to the DB and get the location id,
# eg: which id does location 2.5 correspond to
conn = create_connection(BOOKS_DB)
id_loc_map = get_locations_id(conn)

for index, row in df.iterrows():
    # if index < 30:
    #     continue

    # data from: olib, goob, dbkk
    data_from = "olib"

    # convert isbn with np.nan to empty string
    isbn = row["ISBN-nr"]
    # isbn = "" if isbn is np.nan else isbn
    if isbn is np.nan:
        isbn = ""
        row["ISBN-nr"] = ""

    # use DBKKs db, just parse the current row
    dbkk = dbkkquery(row)
    if (isbn is not np.nan) and (not notisbn(isbn)):
        isbn = canonical(isbn)
        if book_exist(conn, isbn) and not UPDATE_DB:
            continue

        # lookup the isbn. Query all sources to get most info. Then merge
        olib = oquery(isbn)
        goob = gquery(isbn)
        dbkk = dbkkquery(row)

        data, updated1 = merge_data(olib, goob)
        data, updated2 = merge_data(data, dbkk)
        updated = {**updated1, **updated2}

        if olib == dict():  # no result from openlibrary
            data_from = "goob"
        if goob == dict():  # no result from googleapi
            data_from = "dbkk"

        # Find the location id from the location number.
        data['location'] = id_loc_map[str(data['location'])]
       
        # update openlibrary with info from DBKK db
        if bool(updated) and data_from == "olib":
            # print(f"### UPDATED WITH INFO FROM DBKK ###\n{updated}\n")
            pass

        data_oquery.append(olib)
        data_gquery.append(goob)
        data_dbkkquery.append(dbkk)
        data_isbn.append(data)

        # create the book if it doesn't exist in openlibrary
        if data_from != "olib":
            try:
                pass  # does not work yet
                # new_book = add_book(data)
                # print("book added to OLIB.")
            except ValueError as e:
                print(f"Creation failed with {e}")

        # now we pretend the book exist with Olid

        dtuple = sanitize_metadata(data)
        r = insert_book(conn, dtuple)
    else:
        data_noisbn.append(row)
        data_from = "## no ISBN ##"

    print(f"data pulled from {data_from}")
    print(row)
# f2hDaG5tJTaGAbF
#

# # insert book in DB
#
# # Save (commit) the changes
conn.commit()

# # We can also close the connection if we are done with it.
# # Just be sure any changes have been committed or they will be lost.
# conn.close()
