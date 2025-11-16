import time 
import sys
from rpi_courses.web import list_catalog_urls
from rpi_courses.parser.course_catalog import CourseCatalog


def load_latest_rpi_catalog():
    """
    Fetches the URLs for the modern catalog's program pages, loads them 
    incrementally, and returns a single CourseCatalog object.
    """
    print("--- Starting RPI Course Catalog Initialization ---")
    
    # 1. Get the list of available program URLs (now targeting preview_program.php)
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
    
    print(f"\nFound {len(catalog_urls)} program requirement pages to scrape.")
    
    # 3. Iterate through each program URL and load requirements incrementally
    for i, url in enumerate(catalog_urls):
        # The URL contains the unique Program ID (poid)
        program_id = url.split('&')[-2].replace('poid=', '') 
        print(f"[{i+1}/{len(catalog_urls)}] Loading data from Program ID: {program_id}...")
        
        try:
            # Merge_from_url fetches the page, parses its headings/lists, and updates catalog.programs
            master_catalog.merge_from_url(url) 
            time.sleep(1) # Be polite!
            
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
        
        # 🛑 Final Fixed Loop: Efficiently iterate over all parsed programs
        for program_name, temp_program in catalog.programs.items():
            
            # Print separator for clarity
            print("--------------------------------------------------")
            print(f"Loaded Program: **{temp_program.name}**")
            print(f"Total Requirements (Sections): {len(temp_program.details)}")
            print(f"Total Credits (Estimated): {temp_program.credit_hours}")
        
            # Print a sample requirement detail from the first item
            if temp_program.details:
                sample_detail = temp_program.details[0]
                print(f"  Sample Req Text: {sample_detail['text'][:70]}...")
                print(f"  Sample Req Credits: {sample_detail['credits']}")
                print(f"  Courses Linked: {[c['code'] for c in sample_detail['courses']]}")