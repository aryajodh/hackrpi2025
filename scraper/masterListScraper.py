import requests
from bs4 import BeautifulSoup
import re
import json
import time

# --- Configuration ---
BASE_CATALOG_URL = "https://catalog.rpi.edu/content.php?filter%5B27%5D=-1&filter%5B29%5D=&filter%5Bcourse_type%5D=-1&filter%5Bkeyword%5D=&filter%5B32%5D=1&filter%5Bcpage%5D=1&cur_cat_oid=33&expand=1&navoid=891&print=1&filter%5Bexact_match%5D=1"
PAGES_TO_PARSE = 22

# --- Helper Function (Remains Robust) ---
def extract_field_value(text_block, start_label):
    """
    Finds a field value in the text block by slicing the string between the 
    start_label and the next pipe '|' separator.
    """
    start_index = text_block.find(start_label)
    
    if start_index == -1:
        return None

    value_start = start_index + len(start_label)
    value_end = text_block.find('|', value_start)
    
    if value_end == -1:
        value_end = len(text_block)
        
    value = text_block[value_start:value_end].strip().replace('|', ' ')
    
    return value if value else None


# --- Main Logic ---

def parse_rpi_course_catalog(base_url, num_pages=1):
    all_course_data = []

    for page in range(1, num_pages + 1):
        url = base_url.replace("&filter%5Bcpage%5D=1", f"&filter%5Bcpage%5D={page}")
        
        print(f"--- Fetching print view page {page} from: {url} ---")
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers)
            response.raise_for_status() 
        except requests.exceptions.RequestException as e:
            print(f"Error fetching page {page}: {e}")
            break

        soup = BeautifulSoup(response.content, 'html.parser') 
        course_list_container = soup.find('body')
        
        if not course_list_container:
            print("Could not find main course list container. Stopping.")
            break

        course_blocks = course_list_container.find_all('li')

        if not course_blocks:
            print(f"No <li> elements found containing courses on page {page}. Stopping.")
            break
        
        print(f"Found {len(course_blocks)} course blocks (<li>) on page {page}.")
            
        # Define field separators globally and include the most generic corequisite patterns
        # FIX: Ensure all Prerequisite/Corequisite patterns are included here.
        FIELD_LABELS = [
            '|When Offered:', '|Credit Hours:', '|Graded:', 
            '|Prerequisite(s):', '|Corequisite(s):', '|Prerequisite or Corequisite:', 
            '|Corequisite:', '|Prerequisite:' # Added generic 'Prerequisite:' for robustness
        ]

        for block in course_blocks:
            course = {
                'Code': 'N/A',
                'Name': 'N/A',
                'Description': 'N/A',
                'Credits': 'N/A',
                'Prerequisites': 'None listed',
                'Corequisites': 'None listed',
                'Offered': 'Unknown'
            }
            
            block_text = block.get_text(separator='|', strip=True)
            
            # 1. --- CODE, NAME, AND DESCRIPTION EXTRACTION ---
            
            match_header = re.match(r'([A-Z]{3,4}\s\d{4}[A-Z]?)\s*-\s*(.*)', block_text)
            
            if match_header:
                course['Code'] = match_header.group(1).strip()
                
                remaining_text = match_header.group(2).strip()
                
                name_and_description_text = remaining_text
                
                if '|' in name_and_description_text:
                    name_part, description_and_fields = name_and_description_text.split('|', 1)
                else:
                    name_part = name_and_description_text
                    description_and_fields = ""
                
                course['Name'] = name_part.strip().replace('|', ' ')

                description_text = ""
                
                if description_and_fields:
                    # FIX: Search for the index of the earliest field label in the remaining text
                    field_indices = [
                        description_and_fields.find(label) 
                        for label in FIELD_LABELS 
                        if description_and_fields.find(label) != -1
                    ]
                    
                    earliest_field_index = min(field_indices) if field_indices else len(description_and_fields)
                    
                    # Description is the text up to this earliest delimiter
                    description_text = description_and_fields[:earliest_field_index].strip()
                    
                
                if description_text:
                    course['Description'] = description_text.replace('|', ' ')
                else:
                    course['Description'] = 'N/A'
                    
            # 2. --- FIELD EXTRACTION using SUBSTRING SEARCHING (Reliable for Specific Fields) ---

            # A. Offered
            offered_value = extract_field_value(block_text, "|When Offered:|")
            if offered_value:
                course['Offered'] = offered_value

            # B. Credits
            credits_value = extract_field_value(block_text, "|Credit Hours:|")
            if credits_value:
                course['Credits'] = credits_value
            
            # C. Prerequisites/Corequisites 
            
            # Prioritize specific Prerequisite labels
            prereq_value = extract_field_value(block_text, "|Prerequisite(s):|")
            if prereq_value:
                course['Prerequisites'] = prereq_value
            else:
                prereq_value = extract_field_value(block_text, "|Prerequisite or Corequisite:|")
                if prereq_value:
                    course['Prerequisites'] = "OR/COMBINED: " + prereq_value
                else:
                    # Fallback check for the generic "Prerequisite" label
                    prereq_value = extract_field_value(block_text, "|Prerequisite:|")
                    if prereq_value:
                        course['Prerequisites'] = prereq_value


            # D. Corequisites
            coreq_value = extract_field_value(block_text, "|Corequisite(s):|")
            if coreq_value:
                course['Corequisites'] = coreq_value
            else:
                # Fallback check for the generic "Corequisite" label
                coreq_value = extract_field_value(block_text, "|Corequisite:|")
                if coreq_value:
                    course['Corequisites'] = coreq_value
            
            all_course_data.append(course)
        
        time.sleep(1) 

    return all_course_data

# --- Execution ---
data = parse_rpi_course_catalog(BASE_CATALOG_URL, num_pages=PAGES_TO_PARSE)

# --- Output the Results ---
if data:
    print("\n--- SUCCESSFULLY PARSED COURSE DATA (FINAL CHECK) ---")
    print(f"Total courses found: {len(data)}")
    
    print(json.dumps(data[:5], indent=4))
    
    with open('rpi_courses.json', 'w') as f:
        json.dump(data, f, indent=4)
        print("\nData saved to 'rpi_courses.json'")
else:
    print("\nParsing failed or no courses were found.")