#!/usr/bin/env python3

"""Add new book to openlibrary


This requires an user account at openlibrary.org.

ol --configure --email mek@archive.org
password: ***********
Successfully configured

The keys are stored in ~/.config/ol.ini

https://github.com/hornc/catharbot
https://github.com/internetarchive/openlibrary/wiki/Writing-Bots
https://github.com/internetarchive/openlibrary-client/issues/165
https://gitter.im/theopenlibrary/Lobby

https://platform.worldcat.org/api-explorer/apis
https://platform.worldcat.org/api-explorer/apis/Classify/ClassificationResource/Search
http://classify.oclc.org/classify2/Classify?title=de%20syv%20tinder
"""

# Import necessary libraries to use
from olclient.openlibrary import OpenLibrary
import olclient.common as common

from isbnlib import is_isbn10, is_isbn13

def add_book(data):
    # add book to openlibrary.org

    # Define a Book Object
    authors = [common.Author(name=author) for author in data['authors'].split(', ')]
    book = common.Book(title=data['title'],
                       authors=authors,
                       publisher=data['publisher'],
                       publish_date=data['year'],
                       pages=data['pages'],
                       )

    # Add metadata like ISBN 10 and ISBN 13
    isbn = data['isbn']
    if is_isbn10(isbn):
        book.add_id('isbn_10', isbn)
    elif is_isbn13(isbn):
        book.add_id('isbn_13', isbn)

    # Create a new book
    ol = OpenLibrary()
    new_book = ol.create_book(book)

    new_book.add_bookcover(data['cover'])
    new_book.work.add_subject(data['categories'])
    new_book.save()

    return new_book
