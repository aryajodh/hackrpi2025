# --- Python 3 Imports ---
# Beautiful Soup 3 (BeautifulSoup) is now Beautiful Soup 4 (bs4)
from bs4 import BeautifulSoup

import datetime
# urllib2 is now urllib.request
import urllib.request as urllib_request

from rpi_courses.web import get
# Assuming 'features' is accessible, but Python 3 requires the dot (e.g., '.features') if it's relative
from .features import * # Assuming this file is part of a package structure

import re


RE_DIV = re.compile(r'</?div[^>]*?>', re.I)


def _remove_divs(string):
    # Some of the DIV formatting even breaks beautiful soup!
    # ... (comments unchanged)
    return RE_DIV.sub('', string)


class CourseCatalog(object):
    """Represents the RPI course catalog.

    This takes a BeautifulSoup instance
    allows an object-oriented method of accessing the data.
    """

    # CRITICAL CHANGE 1: Python 2 'globals().iteritems()' is Python 3 'globals().items()'
    FEATURES = [obj for name, obj in list(globals().items()) if name.endswith('_feature')]

    def __init__(self, soup=None, url=None):
        """Instanciates a CourseCatalog given a BeautifulSoup instance.
        Pass nothing to initiate an empty course catalog.
        """
        self.url = url
        if soup is not None:
            self.parse(soup)

    @staticmethod
    def from_string(html_str, url=None):
        "Creates a new CourseCatalog instance from an string containing html."
        # CRITICAL CHANGE 2: BeautifulSoup.HTML_ENTITIES is removed in BS4.
        # We specify the 'html.parser' or 'lxml' parser for HTML content.
        # html_str must be a string (bytes must be decoded first).
        return CourseCatalog(BeautifulSoup(_remove_divs(html_str), 'html.parser'), url)

    @staticmethod
    def from_stream(stream, url=None):
        "Creates a new CourseCatalog instance from a filehandle-like stream."
        # CRITICAL CHANGE 3: stream.read() returns bytes in Python 3; must decode to str.
        return CourseCatalog.from_string(stream.read().decode('utf-8'), url)

    @staticmethod
    def from_file(filepath):
        "Creates a new CourseCatalog instance from a local filepath."
        # Recommended: Specify encoding and reading mode for text files
        with open(filepath, 'r', encoding='utf-8') as f:
            return CourseCatalog.from_stream(f, filepath)

    @staticmethod
    def from_url(url):
        "Creates a new CourseCatalog instance from a given url."
        # 'get(url)' must return a decoded string in Python 3 'web.py'
        catalog = CourseCatalog.from_string(get(url), url)
        return catalog

    def parse(self, soup):
        "Parses the soup instance as RPI's XML course catalog file."
        for feature in self.FEATURES:
            feature(self, soup)

    def crosslisted_with(self, crn):
        """Returns all the CRN courses crosslisted with the given crn.
        The returned crosslisting does not include the original CRN.
        """
        # NOTE: The original function raises NotImplemented, but the logic below is P3 compatible
        # raise NotImplemented # Keep if function is not meant to be used
        return tuple([c for c in self.crosslistings[crn].crns if c != crn])

    def find_courses(self, partial):
        """Finds all courses by a given substring. This is case-insensitive.
        """
        partial = partial.lower()
        # dict.keys() returns a view in P3, which is fine
        keys = self.courses.keys