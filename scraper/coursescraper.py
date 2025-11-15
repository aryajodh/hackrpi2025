# Import the necessary modules from your fixed library structure
from rpi_courses.web import list_sis_files
from rpi_courses.parser.course_catalog import CourseCatalog

def load_latest_rpi_catalog():
    """
    Fetches the URL for the latest SIS course catalog file and loads it 
    into a CourseCatalog object.
    """
    print("--- Starting RPI Course Catalog Initialization ---")
    
    # 1. Get the list of available SIS file URLs
    try:
        # This calls the list_sis_files function you converted
        sis_files = list_sis_files()
    except Exception as e:
        print(f"Error fetching SIS file URLs. Ensure 'list_sis_files' and 'get' in web.py are fixed. Error: {e}")
        return None

    if not sis_files:
        print("Failed to retrieve any SIS catalog URLs.")
        return None

    # 2. Identify the latest catalog URL
    # Assumes the latest (most recent) file is at the end of the list
    latest_catalog_url = sis_files[-1] 
    print(f"\nFound {len(sis_files)} catalog URLs.")
    print(f"Loading latest catalog from: {latest_catalog_url}")
    
    # 3. Instantiate and load the catalog
    try:
        # This calls CourseCatalog.from_url, which uses get() from web.py
        # This loads and parses the data using all your fixed feature functions.
        course_catalog = CourseCatalog.from_url(latest_catalog_url)
        
        print("\n✅ Catalog Initialization Successful!")
        print(f"Catalog Name: {course_catalog.name}")
        print(f"Total Courses Loaded: {len(course_catalog.courses)}")
        
        return course_catalog
        
    except Exception as e:
        print(f"\n❌ Error initializing Course Catalog: {e}")
        print("HINT: Check your import fixes inside rpi_courses/parser/course_catalog.py and rpi_courses/web.py.")
        return None

if __name__ == '__main__':
    catalog = load_latest_rpi_catalog()

    if catalog and catalog.courses:
        print("\n--- Example Course Access ---")
        
        # Access a known department for a quick check
        try:
            cs_courses = [c for c in catalog.get_courses() if c.dept == 'CSCI']
            
            if cs_courses:
                example_course = cs_courses[0]
                print(f"Found {len(cs_courses)} CSCI courses.")
                print(f"Example: {example_course.code} - {example_course.name}")
                print(f"  Sections Available: {len(example_course.sections)}")
            else:
                print("No CSCI courses found in the catalog.")
                
        except AttributeError:
            print("Error: Course objects may not have a 'dept' attribute. Check your model definitions.")