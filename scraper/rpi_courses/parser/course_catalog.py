import datetime
import urllib.request

from bs4 import BeautifulSoup

from rpi_courses.web import get 
from rpi_courses.parser.features import * # All object postfixed with '_feature' will get used.

# --- (Dummy classes for structural integrity remain) ---
try:
    from rpi_courses.utils import FrozenDict, safeInt
except ImportError:
    class FrozenDict(dict):
        def __setitem__(self, key, value):
            raise TypeError("FrozenDict does not support item assignment")
    def safeInt(x):
        try:
            return int(x)
        except (ValueError, TypeError):
            return 0
    
class DummyCrosslisting:
    def __init__(self):
        self.crns = []


class CourseCatalog(object):
    """Represents the RPI course catalog, now focused on Program Requirements."""

    # CRITICAL CHANGE: Only use features relevant to this new goal (Program parsing)
    FEATURES = [obj for name, obj in list(globals().items()) if name.endswith('_feature')]

    def __init__(self, soup=None):
        """Instanciates a CourseCatalog. Initialized with attributes to prevent AttributeError."""
        self.name = "RPI Course Catalog"
        self.crosslistings = {}
        # PRIMARY DATA CONTAINER
        self.programs = {} 
        self.courses = {}
        self.soup = soup 
        self.timestamp = 0
        self.datetime = datetime.datetime.now()
        self.year = self.datetime.year
        self.semester = "Unknown"
        self.month = 0

        if soup is not None:
            self.parse(soup)

    @staticmethod
    def from_string(html_str):
        "Creates a new CourseCatalog instance from a string containing HTML."
        if not html_str:
            return CourseCatalog() 
        
        try:
            soup = BeautifulSoup(html_str, 'lxml')
        except:
            soup = BeautifulSoup(html_str, 'html.parser')
            
        soup.raw_html_string = html_str 
        return CourseCatalog(soup)

    @staticmethod
    def from_url(url):
        "Creates a new CourseCatalog instance from a given url."
        return CourseCatalog.from_string(get(url))

    def merge_from_url(self, url):
        """Fetches courses from a single department URL and merges the results."""
        temp_catalog = CourseCatalog.from_url(url)
        
        # Merge the parsed programs
        self.programs.update(temp_catalog.programs)
        self.courses.update(temp_catalog.courses)
        self.crosslistings.update(temp_catalog.crosslistings)


    def parse(self, soup):
        "Parses the soup instance using defined features."
        for feature in self.FEATURES:
            feature(self, soup)

    # --- Utility Methods (Kept for compatibility) ---
    def crosslisted_with(self, crn):
        return tuple([c for c in self.crosslistings.get(crn, DummyCrosslisting()).crns if c != crn])

    def find_courses(self, partial):
        partial = partial.lower()
        keys = self.courses.keys()
        keys = [k for k in keys if k.lower().find(partial) != -1]
        courses = [self.courses[k] for k in keys]
        return list(set(courses))

    def get_courses(self):
        return list(self.courses.values())

    def find_course_by_crn(self, crn):
        for name, course in self.courses.items():
            if crn in course:
                return course
        return None

    def find_course(self, partial):
        courses = self.find_courses(partial)
        return courses[0] if courses else None
        
    def find_course_and_crosslistings(self, partial):
        course = self.find_course(partial)
        if not course: return ()
        crosslisted = self.crosslisted_with(course.code) 
        return (course,) + tuple(map(self.find_course_by_crn, crosslisted))