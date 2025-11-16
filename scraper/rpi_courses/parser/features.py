"""features.py - Implements all parsing of the XML file.

All functions related to parsing the XML file are here. To be
automatically imported by the CourseCatalog class, postfix the
function name with '_feature'
"""
# rpi_courses/parser/features.py - New logic for parsing Program Requirements.

import datetime
import re # Required for regex to extract credits

# Assuming these imports work based on the project structure
try:
    from rpi_courses.utils import FrozenDict, safeInt 
    from rpi_courses.config import logger, DEBUG 
except ImportError:
    # Minimal stubbing if utilities/config are not present
    class FrozenDict(dict):
        def __setitem__(self, key, value): pass
    def safeInt(x): 
        try:
            return int(x)
        except (ValueError, TypeError):
            return 0
    class DummyLogger:
        def info(self, msg): pass
        def warning(self, msg): pass
    logger = DummyLogger()
    DEBUG = False

# --- NEW: Program Requirement Model ---
class ProgramRequirement:
    def __init__(self, name, type='Requirement', credit_hours=0, details=None):
        self.name = name
        self.type = type
        self.credit_hours = credit_hours
        self.details = details if details is not None else []
        
    def __repr__(self):
        return f"<Requirement: {self.name} ({self.credit_hours} Cr)>"

# --- Course and Crosslisting class definition (REQUIRED) ---
class Course:
    def __init__(self, code, name, description, sections=None, dept=None):
        self.code = code
        self.name = name
        self.description = description
        self.sections = sections if sections is not None else []
        self.dept = dept
    
    def __str__(self):
        return self.code
    
    def __contains__(self, crn):
        return crn in [s.get('crn') for s in self.sections] 
    
    def __repr__(self):
        return f"<{self.code}: {self.name}>"

class CrossListing:
    def __init__(self, crns, seats):
        self.crns = crns
        self.seats = seats

# --- Feature Functions (Must be suffixed with '_feature') ---

def catalog_name_feature(catalog, soup):
    """Sets the catalog name and current timestamp."""
    title_tag = soup.find('h1', class_='page-title')
    catalog.name = title_tag.text.strip() if title_tag else "RPI Course Catalog"
    catalog.datetime = datetime.datetime.now()
    catalog.timestamp = int(catalog.datetime.timestamp())
    logger.info('Catalog last updated (scraped) on %s' % catalog.datetime)


def crosslisting_feature(catalog, soup):
    """STUB: Cross-listings are not cleanly available on the HTML course pages."""
    listing = {}
    catalog.crosslistings = FrozenDict(listing)
    logger.info('Catalog has %d course crosslistings' % len(catalog.crosslistings))


def program_requirements_feature(catalog, soup):
    """
    Parses program-level requirements from headings and lists on the Program pages,
    using exclusion and inclusion checks for resiliency.
    """
    programs = catalog.programs 
    
    # 1. Define Exclusion/Inclusion Sets (Kept for reference)
    EXCLUSION_LIST = {
        'general information', 'applying for financial aid', 'enrollment', 
        'grading', 'policies', 'graduation requirements',
        'cross-registration at area colleges', 'academic policies',
        'student success', 'admission and registration',
        'fees and expenses', 'the undergraduate experience',
        'auditing', 'transfer credit', 'academic calendar',
        'registration', 'add/drop', 'withdrawals', 'leave of absence',
        'pass/no credit option', 'independent study', 'degree requirements',
        'attendance', 'honors', 'times for registration', 'the rpi plan', 'academic regulations', 
        'residence and time limit', 'plan of study', 'thesis, projects, and professional projects',
        'office of graduate education requirements', 'program adjustments (drop/add/withdraw)',
        'degree program changes', 'student records','withdrawal from the institute', 'advisers', 'advising'
    }
    
    ACADEMIC_KEYWORDS = {'major', 'track', 'option', 'program', 'degree', 'curriculum', 'pathway'}
    
    # 2. Find the main content area and potential headings
    program_blocks = soup.find('div', id='content') 
    if not program_blocks:
        program_blocks = soup
        
    potential_headings = program_blocks.find_all(['h2', 'h3', 'h4'])
    
    if not potential_headings:
        logger.warning("No H2/H3/H4 headings found. Parsing skipped.")
        return

    # 3. Iterate and Filter
    for heading in potential_headings:
        
        # 🛑 FIX 1: Initialize req_list to None at the start of the loop
        req_list = None 
        
        program_name = heading.text.strip()
        program_name_lower = program_name.lower()
        
        # --- Filtering Logic (Remains the same) ---
        if program_name_lower in EXCLUSION_LIST or program_name_lower.startswith('table of contents'):
             continue
             
        if len(program_name_lower) > 80:
            continue
        
        # The following filtering is currently commented out in your provided code block:
        # if len(program_name_lower) < 25 and not is_program_title:
        #      continue
        
        # --- Parsing Requirements List ---
        
        # Check 1: Immediate sibling list (<ul> or <ol>)
        # FIX 2: Assign the result of the sibling search to req_list
        req_list = heading.find_next_sibling(['ul', 'ol']) 
        
        # Check 2: Resiliency check for list wrapped in a <div> or <p>
        if not req_list: # This check is now safe because req_list is None if not found in Check 1
             next_container = heading.find_next_sibling(['div', 'p'])
             if next_container:
                 req_list = next_container.find(['ul', 'ol'])
        
        
        # 4. Filter by List Length
        if req_list: # Check is safe again
            
            # CRITICAL FILTER: Programs have many requirements; policies have few.
            total_list_items = len(req_list.find_all('li'))
            
            # FINAL HEURISTIC: A major program likely has more than 10 requirements.
            if total_list_items < 5: 
                continue # Skip short policy lists
        
        # 5. Final check before parsing items (to avoid parsing non-list items)
        if req_list and len(req_list.find_all('li')) > 0:
            
            # 6. Process Requirements (Parsing Logic)
            req_obj = ProgramRequirement(program_name, 'Major', 0)
            
            for item in req_list.find_all('li'):
                item_text = item.text.strip()
                
                # A. Find Hyperlinks (Course Codes)
                course_links = item.find_all('a', href=True)
                course_data = []
                for link in course_links:
                    code = link.text.strip().replace(':', '').replace(' ', '')
                    course_data.append({'type': 'Course Link', 'code': code})
                    
                # B. Extract Credit Hours (using regex)
                credit_match = re.search(r'\((\d+)\s+credit\s+hours?\)|\s+(\d+)\s+Credit\s+Hours?', item_text, re.I)
                credits = 0
                if credit_match:
                    credit_str = credit_match.group(1) or credit_match.group(2)
                    # NOTE: safeInt must be available in scope
                    credits = safeInt(credit_str)

                # C. Store the requirement detail
                detail = {
                    'text': item_text,
                    'credits': credits,
                    'courses': course_data
                }
                req_obj.details.append(detail)
                req_obj.credit_hours += credits
                
            # 7. Store result
            catalog.programs[program_name] = req_obj
    
    catalog.programs = programs
    logger.info('Catalog parsed %d program requirement blocks.' % len(programs))