#!/usr/bin/env python3

"""Add new book to openlibrary


This requires an user account at openlibrary.org.

ol --configure --email mek@archive.org
password: ***********
Successfully configured

The keys are stored in ~/.config/ol.ini
"""

# Import necessary libraries to use
from olclient.openlibrary import OpenLibrary
import olclient.common as common

from isbnlib import is_isbn10, is_isbn13

def add_book(data):
    # add book to openlibrary.org

    # Define a Book Object
    authors = [common.Author(name=author) for author in data['Authors'].split(', ')]
    book = common.Book(title=data['Title'],
                       authors=authors,
                       publisher=data['Publisher'],
                       publish_date=data['Publisher'],
                       pages=data['Pages'],
                       )

    # Add metadata like ISBN 10 and ISBN 13
    isbn = data['ISBN-13']
    if is_isbn10(isbn):
        book.add_id('isbn_10', isbn)
    elif is_isbn13(isbn):
        book.add_id('isbn_13', isbn)

    # Create a new book
    ol = OpenLibrary()
    new_book = ol.create_book(book)

    new_book.add_bookcover(data['Cover'])
    new_book.work.add_subject(data['Categories'])
    new_book.save()

    return new_book
