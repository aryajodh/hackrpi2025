"""web.py - Handles all the http interaction of getting the course
catalog data. This isn't your web.py web dev framework!
"""
# --- Python 3 Imports ---
# urllib2 is now urllib.request
import urllib.request as urllib_request
import urllib.error as urllib_error
import urllib.parse as urllib_parse
import datetime
import tempfile
# pyPdf is now PyPDF2 or pypdf; assuming PyPDF2 is installed
import PyPDF2 as pyPdf
from contextlib import closing

# BeautifulSoup 3 is now BeautifulSoup 4 (bs4)
from bs4 import BeautifulSoup

from .config import ROCS_URL, SIS_URL, COMM_URL
# dateutil is implicitly used but must be imported explicitly in Py3 if needed
import dateutil.parser


def get(url, last_modified=None):
    """Performs a get request to a given url. Returns an empty str on error.
    """
    try:
        # P3 Change 1: urllib2.urlopen -> urllib.request.urlopen (aliased as urllib_request.urlopen)
        with closing(urllib_request.urlopen(url)) as page:
            if last_modified is not None:
                # P3 Change 2: dateutil must be imported
                # P3 Change 3: page.info() returns a Message; dict() conversion is needed
                last_mod = dateutil.parser.parse(dict(page.info())['last-modified'])
                if last_mod <= last_modified:
                    return ""
            # P3 Change 4: page.read() returns bytes; decode to string for generic content
            return page.read().decode('utf-8')
    # P3 Change 5: urllib2.URLError -> urllib.error.URLError (aliased as urllib_error.URLError)
    except urllib_error.URLError:
        return ""


def list_sis_files_for_date(date=None, url_base=SIS_URL):
    # This function is structurally identical in Python 3
    date = date or datetime.datetime.now()
    format = '%(base)s%(prefix)s%(year).4d%(month).2d.htm'
    urls = []
    months = (1, 5, 9)
    prev_m = None
    prefixes = ['zs', 'zfs']
    def add_date(year, month):
        # Python 3 dict formatting works identically
        for prefix in prefixes:
            urls.append(format % dict(base=url_base, prefix=prefix, year=year, month=month))
    for m in months:
        if m >= date.month:
            if prev_m and prev_m < date.month:
                add_date(date.year, prev_m)
            add_date(date.year, m)
        prev_m = m
    if not urls:
        add_date(date.year, months[-1])
        add_date(date.year + 1, months[0])
    return urls


def list_sis_files(url_base=SIS_URL):
    # This function is structurally identical in Python 3
    date = datetime.date(year=2011, month=1, day=1)
    today = datetime.date.today()
    urls = []
    while date.year <= today.year + 1:
        urls.extend(list_sis_files_for_date(date, url_base=url_base))
        date = datetime.date(year=date.year + 1, month=1, day=1)
    return urls


def list_rocs_files(url=ROCS_URL):
    """Gets the contents of the given url.
    """
    # P3 Change 6: BeautifulSoup now uses the 'html.parser' by default
    soup = BeautifulSoup(get(url), 'html.parser')
    if not url.endswith('/'):
        url += '/'
    files = []
    # P3 Change 7: findAll is BS4 compatible
    for elem in soup.findAll('a'):
        # P3 Change 8: dict access is fine
        if elem['href'].startswith('?'):
            continue
        # P3 Change 9: .string access is fine
        if elem.string.lower() == 'parent directory':
            continue
        files.append(url + elem['href'])
    return files


def is_xml(filename):
    "Returns True if the filename ends in an xml file extension."
    # Identical in P3
    return filename.strip().endswith('.xml')


def list_rocs_xml_files(url=ROCS_URL):
    "Gets all the xml files."
    # P3 Change 10: map/filter return iterators; list() conversion is required
    return list(filter(is_xml, list_rocs_files(url)))


def get_comm_file(date, base_url=COMM_URL):
    format = '%.4d.pdf'
    if date.month == 9:
        url = base_url + "Fall" + str(format % (date.year))
    else:
        url = base_url + "Spring" + str(format % (date.year))

    # P3: Use urllib.request.Request (aliased as urllib_request)
    req = urllib_request.Request(url)
    
    # P3: Use print() function
    print("Getting communication intensive list from: " + url)

    full_text = ""
    temp = None
    try:
        # P3: Use urllib.request.urlopen (aliased as urllib_request)
        f = urllib_request.urlopen(req)
        
        # Create a NamedTemporaryFile. We will write bytes to it.
        temp = tempfile.NamedTemporaryFile(delete=True)
        
        # f.read() returns bytes, which temp.write() handles correctly.
        temp.write(f.read())
        temp.seek(0)
        
        # P3 Fix: Pass the file object (temp) directly to PdfFileReader.
        # The redundant open(temp.name, 'rb') is removed, as temp is already open and ready to read.
        pdf = pyPdf.PdfFileReader(temp)
        
        for page in pdf.pages:
            # extractText() is PyPDF2's method.
            full_text += page.extractText()

    # P3: Exception syntax changed from 'except Error, e:' to 'except Error as e:'
    # P3: Exceptions are referenced from the aliased urllib.error module
    except urllib_error.HTTPError as e:
        # P3: Use print() function
        print("HTTP Error:", e.code, url)
    except urllib_error.URLError as e:
        # P3: Use print() function
        print("URL Error:", e.reason, url)
        
    finally:
        # P3: Cleanup is identical, ensuring the temp file is closed and deleted (via NamedTemporaryFile default behavior)
        if temp:
            temp.close()
            
    return full_text.strip()