#!/usr/bin/env python3
# -*- coding: utf-8 -*-


class ISBNLibException(Exception):
    """Base class for isbnlib exceptions. This exception should not be raised
    directly, only subclasses of this exception should be used!

    """

    def __str__(self):
        """Print message."""
        return getattr(self, "message", "")  # pragma: no cover


# pylint: disable=super-init-not-called
class ISBNLibDevException(ISBNLibException):
    """Base class for isbnlib.dev exceptions. This exception should not be raised
    directly, only subclasses of this exception should be used!

    """

    def __init__(self, msg=None):
        if msg:
            self.message = "%s (%s)" % (self.message, msg)

    def __str__(self):
        return getattr(self, "message", "")  # pragma: no cover


class ISBNNotConsistentError(ISBNLibDevException):
    """Exception raised when the isbn request != isbn response."""

    message = "isbn request != isbn response"


class RecordMappingError(ISBNLibDevException):
    """Exception raised when the mapping records -> canonical doesn't work."""

    message = "the mapping `canonical <- records` doesn't work"
