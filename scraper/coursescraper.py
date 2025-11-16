# Assuming this is your main entry point (e.g., coursescraper.py)

import time 
import sys
# Ensure imports work regardless of module structure
try:
    from rpi_courses.web import list_catalog_urls
    from rpi_courses.parser.course_catalog import CourseCatalog
except ImportError:
    print("FATAL ERROR: Could not import rpi_courses modules. Check your directory structure and PYTHONPATH.")
    sys.exit(1)


def load_latest_rpi_catalog():
    """
    Fetches the URLs for the modern catalog, loads them incrementally, 
    and returns a single CourseCatalog object.
    """
    print("--- Starting RPI Course Catalog Initialization ---")
    
    # 1. Get the list of available catalog URLs
    try:
        catalog_urls = list_catalog_urls()
    except Exception as e:
        print(f"❌ Error fetching catalog URLs: {e}")
        return None

    if not catalog_urls:
        print("❌ Failed to retrieve any catalog URLs. Check web.py or if the site is blocking.")
        return None

    # 2. Initialize the master CourseCatalog object
    master_catalog = CourseCatalog() 
    
    print(f"\nFound {len(catalog_urls)} department course pages to scrape.")
    
    # 3. Iterate through each department URL and load programs incrementally
    for i, url in enumerate(catalog_urls):
        dept_info = url.split('&')[-1] 
        print(f"[{i+1}/{len(catalog_urls)}] Loading data from {dept_info}...")
        
        try:
            master_catalog.merge_from_url(url) 
            time.sleep(1) 
            
        except Exception as e:
            print(f"   ❌ Failed to parse {url}. Error: {e}")
            
    # 4. Final results
    print("\n✅ Catalog Scraping Complete!")
    print(f"Catalog Name: {master_catalog.name}")
    print(f"Total Program Requirement Blocks Loaded: {len(master_catalog.programs)}")
    
    return master_catalog

if __name__ == '__main__':
    catalog = load_latest_rpi_catalog()

    if catalog and catalog.programs:
        print("\n--- Example Program Access ---")
        
        # Access the first program found
        first_program_name = list(catalog.programs.keys())[0]
        first_program = catalog.programs[first_program_name]
        
        print(f"Loaded Program: **{first_program.name}**")
        print(f"Total Requirements: {len(first_program.details)}")
        print(f"Total Credits (Estimated): {first_program.credit_hours}")
        
        # Print a sample requirement detail
        if first_program.details:
            sample_detail = first_program.details[0]
            print(f"  Sample Req Text: {sample_detail['text'][:70]}...")
            print(f"  Sample Req Credits: {sample_detail['credits']}")
            print(f"  Courses Linked: {[c['code'] for c in sample_detail['courses']]}")