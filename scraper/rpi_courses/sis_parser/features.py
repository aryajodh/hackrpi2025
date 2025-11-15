"""features.py - Implements all parsing of the XML file.

All functions related to parsing the XML file are here. To be
automatically imported by the CourseCatalog class, postfix the
function name with '_feature'
"""
import datetime
import re
# CRITICAL CHANGE 1: Python 3 requires explicit imports for utils
# Assuming the necessary modules are installed and correctly configured in rpi_courses.*
from rpi_courses.utils import FrozenDict, safeInt
from rpi_courses.config import logger, DEBUG
from rpi_courses.models import CrossListing, Course, Period, Section


def timestamp_feature(catalog, soup):
    """The datetime the xml file was last modified.
    """
    # CRITICAL CHANGE 2: Division logic must be checked. int(float()) is fine, but verbose.
    # The main change is replacing the Python 2-style float cast.
    # The logic remains the same, but the float() call is necessary for the cast to int.
    epoch = 1318790434
    catalog.timestamp = int(float(soup.title.text)) + epoch
    catalog.datetime = datetime.datetime.fromtimestamp(catalog.timestamp)
    logger.info('Catalog last updated on %s' % catalog.datetime)

def _text(nodes, sep='\n'):
    sb = []
    for node in nodes:
        # Minor Change: .text in BS4 is equivalent to .text in BS3/P2
        sb.append(node.text.strip())
    # Minor Change: Using .join() is identical
    return sep.join(sb)

RE_SEMESTER_RANGE = re.compile(r'(?P<start_month>[A-Za-z]+) +(?P<start_day>\d+) +- +(?P<end_month>[A-Za-z]+) +(?P<end_day>\d+),? +(?P<year>\d+)')
RE_SEMESTER_URL = re.compile(r'^.+zs(?P<year>\d{4})(?P<month>\d{2}).+$')

def semester_feature(catalog, soup):
    """The year and semester information that this xml file hold courses for.
    """
    # Minor Change: findAll is BS4 compatible
    raw = _text(soup.findAll('h3')).split('\n')[1]
    match = RE_SEMESTER_RANGE.match(raw)
    # The int() conversion is valid in P3
    catalog.year = int(match.group('year'))

    # month_mapping is identical in P3
    month_mapping = {'january': 1, 'may': 5, 'august': 9}
    catalog.month = month_mapping[match.group('start_month').lower()]

    if catalog.url:
        match = RE_SEMESTER_URL.match(catalog.url)
        if match:
            catalog.year = int(match.group('year'))
            catalog.month = int(match.group('month'))

    semester_mapping = {1: 'Spring', 5: 'Summer', 9: 'Fall'}
    catalog.semester = semester_mapping[catalog.month]
    catalog.name = '%s %d' % (catalog.semester, catalog.year)
    logger.info('Catalog type: %s' % catalog.name)


# crosslisting_feature is commented out in the original, so it remains commented out.


def course_feature(catalog, soup):
    """Parses all the courses (AKA, the most important part).
    """
    courses = {}
    count = 0
    # Python 3 iteration over generators/lists works fine
    for course_data in parse_tables(soup):
        c = create_course(course_data)
        count += 1
        # str() conversion is valid in P3
        courses[str(c)] = c
    catalog.courses = FrozenDict(courses)
    logger.info('Catalog has %d courses (manual: %d)' % (len(courses), count))


# INTERNAL FUNCTIONS


def create_period(period_data):
    return Period(**period_data)


def create_section(section_data):
    data = dict(section_data)
    # Python 3 tuple comprehension is valid
    data['periods'] = tuple(create_period(p) for p in section_data['periods'])
    return Section(**data)


def create_course(course_data):
    data = dict(course_data)
    # Python 3 tuple comprehension is valid
    data['sections'] = tuple(create_section(s) for s in course_data['sections'])
    return Course(**data)


class_days = {
    'M': 0, 'T': 1, 'W': 2, 'R': 3, 'F': 4
}


def extract_period(cells, period, G):
    # Class type and days extraction are compatible with P3 string operations
    period['type'] = G(cells, 'Class Type').text
    # Python 3 list comprehension is valid
    period['int_days'] = list(class_days[x] for x in G(cells, 'Class Days').text if x.strip() != '')
    # start-time & end-time (we need end-time to figure out if it's in the morning or not)

    def is_tba(s):
        return not s or 'TBA' in s.upper()
    period['start'], period['end'] = G(cells, 'Start Time').text, G(cells, 'End Time').text

    if not is_tba(period['start']) and not is_tba(period['end']):

        is_pm = period['end'].upper().endswith('PM')

        def get_time(s):
            # Python 3 string replacement and int conversion is identical
            return int(s.replace(':', ''))

        # Time parsing logic is identical
        period['start'] = get_time(period['start'])
        period['end'] = get_time(period['end'][:-2])

        if is_pm:
            # All mathematical operations are explicit (+=, -=) and work in P3
            period['start'] += 1200
            period['end'] += 1200
            if period['start'] >= 2400:
                period['start'] -= 1200
            if period['end'] >= 2400:
                period['end'] -= 1200

            # this covers the case of getting 11:00 - 1:50PM
            # we're assuming there's no classes from the evening that go beyond midnight.
            if period['start'] > period['end']:
                period['start'] -= 1200

        period['start'], period['end'] = str(period['start']), str(period['end'])
    # instructor, location extraction is identical
    node = G(cells, 'Instructor')
    period['instructor'] = node.text.strip() if node else ''
    # location
    node = G(cells, 'Building/Room')
    period['location'] = node.text.strip() if node else ''


def parse_tables(node):
    courses = []
    cache = {}
    last_course = last_section = last_period = None
    # Python 3 iteration is valid
    rows = node.findAll('tr')

    # Python 3 list initialization is valid
    columns = [None] * len(rows[0].findAll('th'))

    # Python 3 iteration is valid
    for i, row in enumerate(rows[0].findAll('th')):
        columns[i] = row.text.strip()

    # Python 3 iteration is valid
    for i, row in enumerate(rows[1].findAll('th')):
        # Python 3 string concatenation is valid
        columns[i] += ' ' + row.text.strip() if row.text else ''

    # Python 3 tuple/generator comprehension is valid
    columns = tuple(x.strip() for x in columns)

    # CRITICAL CHANGE 3: Python 2 'print columns' is Python 3 'print(columns)'
    print(columns)
    # possible choices... (comment unchanged)

    def G(cells, name):
        try:
            # Python 3 indexing and error handling is identical
            return cells[columns.index(name)]
        except (IndexError, ValueError):
            return None

    def cache_key(course_dict):
        # Python 3 string concatenation is valid
        return course_dict['dept'] + course_dict['num']

    # Python 3 iteration is valid
    for row in rows[2:]:
        course = {'sections': []}
        section = {'notes': set(), 'periods': []}
        period = {}
        # Python 3 iteration is valid
        cells = row.findAll('td')
        # if we got to a new course / section
        if len(cells) < 2:
            continue
        # String comparison and strip() is identical
        elif cells[0].text.strip() != '':
            # <crn> <code>-<num>-<sec>
            # Python 3 string split is identical
            parts = G(cells, 'CRN Course-Sec').text.split(' ', 1)
            section['crn'] = parts[0]
            # Python 3 string split is identical
            course['dept'], course['num'], section['num'] = parts[1].split('-', 2)
            # course name
            course['name'] = G(cells, 'Course Title').text.strip()
            existing_obj = cache.get(cache_key(course))
            if existing_obj:
                course = existing_obj

            # credit hours (eg - '1' or '1-6')
            # Python 3 string split is identical
            parts = G(cells, 'Cred Hrs').text.split('-', 1)
            course['credmin'], course['credmax'] = parts[0], parts[1] if len(parts) > 1 else parts[0]
            # grade_type
            grade_type = G(cells, 'Gr Tp')
            if grade_type:
                # Python 3 dict lookup and string handling is identical
                course['grade_type'] = {
                    'SU': 'Satisfactory/Unsatisfactory',
                }.get(grade_type.text, grade_type.text)
            # seats total
            node = G(cells, 'Max Enrl')
            if node:
                # Python 3 int conversion is identical
                section['total'] = int(node.text) if node.text.strip() else 0
            else:
                section['total'] = ''
            # seats taken
            node = G(cells, 'Enrl')
            if node:
                # Python 3 int conversion is identical
                section['taken'] = int(node.text) if node.text.strip() else 0
            else:
                section['taken'] = ''
            # textbook link? could be useful (comment unchanged)
            # section['textbook_link'] = cells[12].find('a')['href']
            extract_period(cells, period, G)

            # link up
            section['periods'].append(period)
            course['sections'].append(section)
            cache[cache_key(course)] = course

            if not existing_obj:
                courses.append(course)

            last_course, last_section, last_period = course, section, period

        # String comparison is identical
        elif 'NOTE:' in cells[1].text.strip():  # process note
            course, section = last_course, last_section
            # set.add() and strip() is identical
            section['notes'].add(cells[2].text.strip())

        # Dictionary copy is valid
        else:  # process a new period type
            course, section = last_course, last_section

            period = last_period.copy()
            extract_period(cells, period, G)
            section['periods'].append(period)

    return courses