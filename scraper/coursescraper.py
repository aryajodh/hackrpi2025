import time 
import sys
import re
import json 
from rpi_courses.web import list_catalog_urls
from rpi_courses.parser.course_catalog import CourseCatalog

# --- Configuration ---
COURSE_DETAILS_FILE = 'rpi_courses.json'
OUTPUT_PROGRAM_FILE = 'rpi_program_requirements.json' # New output file name


def load_course_details(filepath):
    """
    Loads the detailed course data from the master list (rpi_courses.json)
    and indexes it by course 'Code' for fast lookup.
    """
    course_details = {}
    print(f"Loading detailed course data from {filepath}...")
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            for course in data:
                # Use the 'Code' (e.g., CSCI 1100) as the primary key
                course_code = course.get("Code", "N/A")
                if course_code != "N/A":
                    course_details[course_code] = course
        print(f"Successfully loaded and indexed {len(course_details)} individual course entries.")
    except FileNotFoundError:
        print(f"Warning: {filepath} not found. Cannot enrich program data.")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {filepath}: {e}")
    return course_details


def load_latest_rpi_catalog():
    """
    Fetches the URLs for the modern catalog's program pages, loads them 
    incrementally, and returns a single CourseCatalog object.
    """
    print("--- Starting RPI Program Requirements Scraper ---")
    
    # Get the list of available program URLs (from the main index page)
    try:
        catalog_urls = list_catalog_urls()
    except Exception as e:
        print(f"Error fetching catalog URLs: {e}")
        return None

    if not catalog_urls:
        print("Failed to retrieve any program URLs. Check web.py or if the site is blocking.")
        return None

    # Initialize the master CourseCatalog object
    master_catalog = CourseCatalog() 
    
    print(f"\nFound {len(catalog_urls)} program requirement pages to scrape.")
    
    # Iterate through each program URL and load requirements incrementally
    for i, url in enumerate(catalog_urls):
        # The URL structure is long, so we just show the index for progress.
        print(f"[{i+1}/{len(catalog_urls)}] Loading program data from: {url.split('poid=')[-1]}...")
        
        try:
            # merge_from_url fetches the page, parses its content blocks, and updates catalog.programs
            master_catalog.merge_from_url(url) 
            time.sleep(1) # Be polite with server requests
            
        except Exception as e:
            print(f"Failed to parse {url}. Error: {e}")
            
    # 4. Final results
    print("\nProgram Scraping Complete!")
    print(f"Total Programs Loaded: {len(master_catalog.programs)}")
    
    return master_catalog

if __name__ == '__main__':
    # Load detailed course information from the JSON file first
    detailed_courses_db = load_course_details(COURSE_DETAILS_FILE)
    
    # Load the program requirements data
    catalog = load_latest_rpi_catalog()

    all_program_output = []
    
    if catalog and catalog.programs:
        print("\n--- Generating Enriched Program Data ---")
        
        for program_name, program_data in catalog.programs.items():
            
            required_courses_enriched = {}
            
            # The parsing feature is now designed to return a cleaned list of elective sections
            elective_sections_list = program_data.get('elective_and_track_details', [])
            
            # 1. Collect and ENRICH required courses (Subject Codes)
            # The parsing feature has already extracted the codes and heuristic credits into this list
            for course_ref in program_data.get('required_course_codes', []): 
                code = course_ref['code']
                
                if code not in required_courses_enriched:
                    
                    # Cross-reference with the master course database (rpi_courses.json)
                    # We prioritize detailed info from the master list, falling back to scraped info if necessary
                    course_info = detailed_courses_db.get(code, {
                        'Code': code,
                        'Name': '[Name Not Found]',
                        'Credits': course_ref.get('credits', 'N/A'), # Use heuristic credit from parsing feature
                        'Prerequisites': '[Details Not Found]',
                        'Offered': '[Details Not Found]',
                        'Description': '[Details Not Found]'
                    })
                    
                    # Store the simplified, enriched structure
                    required_courses_enriched[code] = {
                        'Code': course_info['Code'],
                        'Name': course_info['Name'],
                        # Use the Credits field from the master list for accuracy, which is loaded above.
                        'Credits': course_info['Credits'], 
                        'Prerequisites': str(course_info.get('Prerequisites', '[Details Not Found]')), 
                        'Description': str(course_info.get('Description', '[Details Not Found]'))
                    }
            
            # Compile the final structured output for this program
            program_output = {
                'program_name': program_name,
                # The parsing feature has provided the estimated credits
                'total_estimated_credits': program_data.get('total_estimated_credits', 'N/A'), 
                'required_courses': sorted(required_courses_enriched.values(), key=lambda x: x['Code']),
                'elective_and_track_details': elective_sections_list
            }
            
            all_program_output.append(program_output)

        # --- Write Final Output to JSON File ---
        try:
            with open(OUTPUT_PROGRAM_FILE, 'w') as outfile:
                json.dump(all_program_output, outfile, indent=4)
            print(f"\n--- SUCCESS ---")
            print(f"Data for {len(all_program_output)} programs successfully written to {OUTPUT_PROGRAM_FILE}")
        except Exception as e:
            print(f"FATAL ERROR: Could not write output file {OUTPUT_PROGRAM_FILE}. Error: {e}")