import datetime
import urllib.request

from bs4 import BeautifulSoup

from rpi_courses.web import get
from rpi_courses.parser.features import * # all object postfixed with '_feature' will get used.


class CourseCatalog(object):
    """Represents the RPI course catalog.

    This takes a BeautifulSoup instance (usually a BeautifulStoneSoup instance)
    allows an object-oriented method of accessing the data.
    """

    # CRITICAL CHANGE 1: Python 2 'globals().iteritems()' is Python 3 'globals().items()'
    # list() wrapper is added to ensure iteration completes before list construction.
    FEATURES = [obj for name, obj in list(globals().items()) if name.endswith('_feature')]

    def __init__(self, soup=None):
        """Instanciates a CourseCatalog given a BeautifulSoup instance.
        Pass nothing to initiate an empty course catalog.
        """
        if soup is not None:
            self.parse(soup)

    @staticmethod
    def from_string(xml_str):
        "Creates a new CourseCatalog instance from an string containing xml."
        # CRITICAL CHANGE 2: BeautifulStoneSoup/XML_ENTITIES are removed in BS4
        # We replace it with the standard BeautifulSoup object and specify the 'xml' parser.
        return CourseCatalog(BeautifulSoup(xml_str, 'xml'))

    @staticmethod
    def from_stream(stream):
        "Creates a new CourseCatalog instance from a filehandle-like stream."
        # stream.read() in P3 returns bytes; decode to string for BeautifulSoup
        return CourseCatalog.from_string(stream.read().decode('utf-8'))

    @staticmethod
    def from_file(filepath):
        "Creates a new CourseCatalog instance from a local filepath."
        # CRITICAL CHANGE 3: Universal read mode 'r' is safer for text files
        with open(filepath, 'r', encoding='utf-8') as f:
            return CourseCatalog.from_stream(f)

    @staticmethod
    def from_url(url):
        "Creates a new CourseCatalog instance from a given url."
        return CourseCatalog.from_string(get(url))

    def parse(self, soup):
        "Parses the soup instance as RPI's XML course catalog file."
        for feature in self.FEATURES:
            feature(self, soup)

    def crosslisted_with(self, crn):
        """Returns all the CRN courses crosslisted with the given crn.
        The returned crosslisting does not include the original CRN.
        """
        return tuple([c for c in self.crosslistings[crn].crns if c != crn])

    def find_courses(self, partial):
        """Finds all courses by a given substring. This is case-insensitive.
        """
        partial = partial.lower()
        # Minor Change: keys() returns a view in P3, which is fine
        keys = self.courses.keys()
        keys = [k for k in keys if k.lower().find(partial) != -1]
        courses = [self.courses[k] for k in keys]
        return list(set(courses))

    def get_courses(self):
        """Returns all course objects from this catalog.
        """
        # Minor Change: values() returns a view in P3; return list() is good practice
        return list(self.courses.values())

    def find_course_by_crn(self, crn):
        """Searches all courses by CRNs. Not particularly efficient.
        Returns None if not found.
        """
        # CRITICAL CHANGE 4: Python 2 'dict.iteritems()' is Python 3 'dict.items()'
        for name, course in self.courses.items():
            if crn in course:
                return course
        return None

    def find_course_and_crosslistings(self, partial):
        """Returns the given course and all other courses it is
        crosslisted with.
        """
        course = self.find_course(partial)
        crosslisted = self.crosslisted_with(course.crn)
        return (course,) + tuple(map(self.find_course_by_crn, crosslisted))