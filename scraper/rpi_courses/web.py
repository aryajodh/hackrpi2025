"""web.py - Handles all the http interaction of getting the course
catalog data.
"""
# --- Python 3 Imports ---
import urllib.request as urllib_request
import urllib.error as urllib_error
import urllib.parse as urllib_parse
import datetime
import tempfile
import PyPDF2 as pyPdf
from contextlib import closing

# BeautifulSoup 3 is now BeautifulSoup 4 (bs4)
from bs4 import BeautifulSoup

# Assuming you've updated your config file or have these constants available
try:
    from .config import ROCS_URL, SIS_URL, COMM_URL 
except ImportError:
    # Fallback/Default values if config.py is not available
    ROCS_URL = "http://www.rpi.edu/dept/arc/rocs/"
    SIS_URL = "http://sis.rpi.edu/reg/"
    COMM_URL = "http://www.rpi.edu/dept/arc/rocs/comm/"

import dateutil.parser

# NEW CONSTANTS: Targets the Programs Index page
PROGRAMS_INDEX_URL = "https://catalog.rpi.edu/content.php?catoid=33&navoid=873" 
BASE_URL = "https://catalog.rpi.edu/"


def get(url, last_modified=None):
    """Performs a get request to a given url, using a User-Agent to prevent blocking.
    Returns an empty str on error.
    """
    
    # FIX: Define a standard User-Agent and create the Request object
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    req = urllib_request.Request(url, headers=headers)
    
    try:
        # Use the Request object ('req') and set a timeout for safety
        with closing(urllib_request.urlopen(req, timeout=10)) as page: 
            if last_modified is not None:
                # Logic for conditional GET request
                last_mod_header = dict(page.info()).get('last-modified')
                if last_mod_header:
                    last_mod = dateutil.parser.parse(last_mod_header)
                    if last_mod <= last_modified:
                        return ""
            
            # Read and decode the page content
            content = page.read().decode('utf-8')
            return content
            
    except urllib_error.HTTPError as e:
        print(f"❌ HTTP Error fetching {url}: {e.code}")
        return ""
    except urllib_error.URLError as e:
        print(f"❌ URL Error fetching {url}: {e.reason}")
        return ""
    except Exception as e:
        print(f"❌ Unexpected Error fetching {url}: {e}")
        return ""


# --- REWRITTEN DISCOVERY FUNCTION ---
def list_catalog_urls(index_url=PROGRAMS_INDEX_URL):
    """
    Scrapes the main index page to find all links leading to individual 
    preview_program.php pages (the definitive source for requirements).
    """
    html_content = get(index_url)
    if not html_content:
        return []

    try:
        soup = BeautifulSoup(html_content, 'lxml')
    except Exception:
        soup = BeautifulSoup(html_content, 'html.parser')

    program_urls = set()

    # Iterate through all <a> tags to find program preview links
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        
        # CRITICAL CHECK: Look for the specific program preview pattern
        if 'preview_program.php' in href and 'poid=' in href:
            # Construct the full, absolute URL
            if not href.startswith('http'):
                full_url = BASE_URL + href
            else:
                full_url = href
            
            program_urls.add(full_url)
             
    # Return the unique list of program URLs
    return list(program_urls)


# --- DEPRECATED SIS FUNCTIONS (Kept as stubs) ---
def list_sis_files_for_date(date=None, url_base=SIS_URL):
    """DEPRECATED: Use list_catalog_urls() for the modern RPI Course Catalog."""
    return []


def list_sis_files(url_base=SIS_URL):
    """DEPRECATED: Use list_catalog_urls() for the modern RPI Course Catalog."""
    return []


# --- LEGACY ROCS FUNCTIONS (Kept as stubs) ---
def list_rocs_files(url=ROCS_URL):
    """Gets the contents of the given url."""
    soup = BeautifulSoup(get(url), 'html.parser')
    if not url.endswith('/'):
        url += '/'
    files = []
    for elem in soup.findAll('a'):
        if elem['href'].startswith('?'):
            continue
        if elem.string and elem.string.lower() == 'parent directory':
            continue
        files.append(url + elem['href'])
    return files


def is_xml(filename):
    "Returns True if the filename ends in an xml file extension."
    return filename.strip().endswith('.xml')


def list_rocs_xml_files(url=ROCS_URL):
    "Gets all the xml files."
    return list(filter(is_xml, list_rocs_files(url)))


def get_comm_file(date, base_url=COMM_URL):
    format = '%.4d.pdf'
    if date.month == 9:
        url = base_url + "Fall" + str(format % (date.year))
    else:
        url = base_url + "Spring" + str(format % (date.year))

    req = urllib_request.Request(url)
    
    print("Getting communication intensive list from: " + url)

    full_text = ""
    temp = None
    try:
        f = urllib_request.urlopen(req)
        
        temp = tempfile.NamedTemporaryFile(delete=True)
        
        temp.write(f.read())
        
        pdf = pyPdf.PdfFileReader(temp)
        
        for page in pdf.pages:
            full_text += page.extractText()

    except urllib_error.HTTPError as e:
        print("HTTP Error:", e.code, url)
    except urllib_error.URLError as e:
        print("URL Error:", e.reason, url)
        
    finally:
        if temp:
            temp.close()
            
    return full_text.strip()