import re
from bs4 import BeautifulSoup, NavigableString, Tag

# Helper functions (Defined earlier, included for completeness/context)
def safeInt(x): 
    try:
        return int(x)
    except (ValueError, TypeError):
        return 0

def find_course_data(text):
    """
    Helper function to extract course codes and attempt to infer credits.
    Uses a robust search pattern for course codes (e.g., CSCI 1100).
    """
    # Pattern: 3-4 uppercase letters, space, 4 digits, optional letter (e.g., CIVL 1100, ADMN 1030)
    course_codes = re.findall(r"[A-Z]{3,4}\s\d{4}[A-Z]?", text) 
    
    course_data = []
    
    for code in set(course_codes): # Use a set to handle duplicated codes in a block
        # Try to find specific credit reference immediately following the code (within 50 chars).
        # Pattern: CODE ... (Credit Hours: N or (N credits) or simply CODE N)
        credit_match = re.search(rf'{re.escape(code)}.*?(?:Credit\s*Hours:\s*|credits:\s*|[:\s])\s*(\d+)', text, re.IGNORECASE | re.DOTALL)
        
        # Default to the most common credit value (4 for RPI undergraduate courses) if not found.
        credits = safeInt(credit_match.group(1)) if credit_match and credit_match.group(1) else 4 
        
        course_data.append({"code": code, "credits": credits})
            
    return course_data
    
def extract_detail(header, text, elective_flag=False):
    """
    Helper function to process a single logical requirement block.
    """
    
    # Find courses and estimate credits from the text
    courses_data = find_course_data(text)
    
    # Check for elective status explicitly or via key phrases
    if not elective_flag and any(phrase in text.lower() for phrase in ['free elective', 'h&ss elective', 'humanities elective', 'technical elective', 'free elect.', 'h&ss elect.', 'h/ss elect.', 'restricted elective']):
        elective_flag = True
    
    # Estimate total credits for this block (improved logic)
    credits = 0
    # Look for a specific credit count in the text like '12 credits'
    credits_match = re.search(r'(\d+)\s+(?:credit|elect)', text)
    if credits_match:
        credits = safeInt(credits_match.group(1))
    elif courses_data:
        # Sum of individual course credits (using the heuristic if detail not found)
        credits = sum(c['credits'] for c in courses_data) 
    else:
        # Try to find common phrasing for credit blocks (e.g., "16 credit hours" at the start)
        credits_block_match = re.search(r'^(\d+)\s+(credit|hour)', text)
        credits = safeInt(credits_block_match.group(1)) if credits_block_match else 0
        

    return {
        "header": header,
        "text": text,
        "credits": credits,
        "courses": courses_data,
        "is_elective_section": elective_flag
    }

def classify_program_name(full_name):
    """
    Analyzes the full program name string to extract the prefix, subject name, and degree/type.
    """
    # 1. Standardized Mapping for common suffixes/prefixes
    degree_map = {
        'ph.d.': 'Ph.D.', 'phd': 'Ph.D.',
        'm.s.': 'M.S.', 'ms': 'M.S.',
        'm.eng.': 'M.Eng.', 'meng': 'M.Eng.',
        'b.s.': 'B.S.', 'bs': 'B.S.',
        'b.arch.': 'B.Arch.',
        'm.b.a.': 'M.B.A.', 'mba': 'M.B.A.',
        'minor': 'Minor',
        'pathway': 'Pathway',
        'graduate certificate': 'Grad Cert',
        'certificate': 'Grad Cert'
    }
    
    # Remove common separators and parenthetical content
    name_clean = re.sub(r'\(.*?\)', '', full_name).replace(',', '').replace('/', ' and ').strip()
    name_parts = [p.strip() for p in name_clean.split()]
    
    prefix = "N/A"
    subject_name = name_clean
    degree_type = "N/A"
    
    # 2. Look for Degree/Type at the END
    for i in range(len(name_parts) - 1, -1, -1):
        test_suffix = name_parts[i].lower().replace('.', '')
        
        # Check if the last part is a recognized degree type
        if test_suffix in degree_map:
            degree_type = degree_map[test_suffix]
            
            # The remaining words form the subject name
            subject_parts = name_parts[:i]
            
            # Special handling for names like 'Applied Mathematics M.S.'
            if subject_parts and subject_parts[-1].lower() in ('and', 'or', 'in', 'studies', 'science'):
                 subject_name = " ".join(subject_parts)
            else:
                 subject_name = " ".join(subject_parts) if subject_parts else ""

            # Check if there is a prefix that precedes the subject name (e.g., "Naval Reserve Officers Training Corps")
            if len(subject_parts) > 1 and subject_parts[0].lower() in ('program', 'curriculum', 'accelerated', 'joint', 'dual', 'honors'):
                prefix = subject_parts[0]
                subject_name = " ".join(subject_parts[1:])
                
            break
            
    # 3. Final Check for Minor/Pathway where the keyword is the last word
    if name_clean.lower().endswith("minor"):
        degree_type = "Minor"
        subject_name = name_clean[:-5].strip()
    elif name_clean.lower().endswith("pathway"):
        degree_type = "Pathway"
        subject_name = name_clean[:-7].strip()

    # Fallback cleanup for subjects
    if not subject_name or subject_name.lower() in degree_map or subject_name.lower() in ('and', 'or'):
        subject_name = "Overall Program" # Use a generic name if extraction failed
        
    # Standardize 'Degree/Type' into 'Program Type' for the final output key
    return {
        'program_prefix': prefix,
        'subject_name': subject_name,
        'program_type': degree_type,
        'full_name': full_name # Keep the original name for reference
    }


def program_details_feature(catalog, soup):
    """
    Core parsing logic for a single program page (preview_program.php).
    Extracts program name, total credits, and structured list of requirements.
    Uses robust text-based heuristics and name classification.
    """
    program_data = {}
    program_details = []
    
    # --- 1. Extract Program Name and Total Credits (Heuristic) ---
    
    program_name_tag = soup.find('h1', id='program_name') or soup.find('h1')
    
    if program_name_tag:
        full_name = program_name_tag.text.strip()
        
        # Clean up the name (e.g., remove ' - Catalog Year 202X-202Y')
        if " - " in full_name:
            full_name = full_name.split(' - ')[0].strip()
        
        # CLASSIFY THE NAME
        classification = classify_program_name(full_name)
        program_data.update(classification)
        
        # Heuristic for Total Credits: Look for a number near "Total Credit Hours"
        total_credits = 0
        credits_search_text = soup.get_text()
        
        # Strategy A: Try to extract credits from a table/section with the label
        credit_tag = soup.find(string=lambda t: t and 'Total Credit Hours' in t)
        if credit_tag:
            credits_text = credit_tag.find_next('td').text if credit_tag.parent.name == 'td' else credits_search_text
            match = re.search(r'(\d+)\.?\d*\s*(?:Total Credit Hours)', credits_text)
            total_credits = safeInt(match.group(1)) if match else 0
        else:
            # Strategy B: Fallback, broader search near common credit phrases
            credit_hours_match = re.search(r'(\d+)\s+Total Credit Hours', credits_search_text)
            total_credits = safeInt(credit_hours_match.group(1)) if credit_hours_match else 0
            
        program_data['total_estimated_credits'] = total_credits
            
    # --- 2. Extract Requirement Blocks ---
    # Look for the main container or fall back to body content
    content_area = soup.find('div', id='program_descriptions') or soup.body
    
    EXCLUSION_KEYWORDS = ['general information', 'advising', 'academic regulations', 'policies']
    ELECTIVE_KEYWORDS = ['free elective', 'h&ss elective', 'humanities elective', 'technical elective']
    
    if content_area:
        # Target headings (h3, h4) and common content blocks (p, ul, ol)
        elements = content_area.find_all(['h3', 'h4', 'p', 'ul', 'ol', 'div'], recursive=True)
        
        current_header = "Program Overview"
        current_text_block = []
        
        for elem in elements:
            
            # Skip empty or very short filler content
            text = elem.get_text(separator=' ', strip=True)
            if not text or len(text) < 5:
                continue

            # Check for section headings (h3 or h4)
            if elem.name in ('h3', 'h4'):
                if current_text_block:
                    header_lower = current_header.lower()
                    if not any(kw in header_lower for kw in EXCLUSION_KEYWORDS):
                        is_elective_section = any(kw in header_lower for kw in ELECTIVE_KEYWORDS)
                        program_details.append(extract_detail(current_header, ' '.join(current_text_block), is_elective_section))
                        
                current_header = text
                current_text_block = []
                
            # If it's a content tag (p, ul, ol, div not caught by header)
            elif elem.name in ('p', 'ul', 'ol', 'div'):
                # Treat table content separately if found
                if elem.find('table'):
                    continue
                
                # Accumulate text for the current block
                current_text_block.append(text)
                
        # Finalize the last section
        if current_text_block:
            header_lower = current_header.lower()
            if not any(kw in header_lower for kw in EXCLUSION_KEYWORDS):
                 is_elective_section = any(kw in header_lower for kw in ELECTIVE_KEYWORDS)
                 program_details.append(extract_detail(current_header, ' '.join(current_text_block), is_elective_section))

    # --- 3. Final Compilation and Deduplication for output ---
    required_courses_raw = {}
    elective_sections_list = []
    
    for detail in program_details:
        for course_data in detail['courses']:
            code = course_data['code']
            if code not in required_courses_raw:
                # Store enough info for later enrichment in courscraper.py
                required_courses_raw[code] = {
                    'code': code, 
                    'credits': course_data['credits'] # Use heuristic/extracted credit
                }
                
        if detail['is_elective_section']:
            elective_sections_list.append({
                'section_header': detail['header'],
                'section_text': detail['text']
            })

    program_output = {
        'program_prefix': program_data.get('program_prefix', "N/A"),
        'subject_name': program_data.get('subject_name', "Unknown Program"),
        'program_type': program_data.get('program_type', "N/A"),
        'full_program_name': program_data.get('full_name', "Unknown Program"),
        'total_estimated_credits': program_data.get('total_estimated_credits', 0),
        # Pass the extracted courses (list of dicts with code/credits)
        'required_course_codes': list(required_courses_raw.values()), 
        'elective_and_track_details': elective_sections_list
    }
    
    # Store the results so courscraper.py can access them via catalog.programs
    catalog.programs[program_output['full_program_name']] = program_output