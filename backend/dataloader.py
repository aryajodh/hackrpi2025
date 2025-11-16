import os
import sys
import json
import psycopg2
from dotenv import load_dotenv
import subprocess 

load_dotenv()

# --- IMPORTING RPI-COURSES LIBRARY FUNCTION ---
try:
    from course_scraper import load_latest_rpi_catalog
except ImportError as e:
    print(f"FATAL ERROR: Could not import required program scraper functions. Run: pip install rpi-courses. Details: {e}")
    sys.exit(1)

# Paths
JSON_FILE_PATH = 'rpi_courses.json'
MASTER_SCRAPER_PATH = 'masterListScraper.py'


def connect_db():
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            user=os.getenv('PGUSER'),
            host=os.getenv('PGHOST'),
            database=os.getenv('PGDATABASE'),
            password=os.getenv('PGPASSWORD'),
            port=os.getenv('PGPORT')
        )
        print("✅ Database connection established.")
        return conn
    except Exception as e:
        print(f"❌ Database connection failed. Check your .env settings: {e}")
        sys.exit(1)


def insert_master_courses(cur, master_courses_list):
    """Inserts canonical course data from the Master List Scraper (via the JSON list)."""
    courses_inserted = 0
    print(f"\n--- Inserting {len(master_courses_list)} Master Courses from JSON ---")
    
    for course_data in master_courses_list:
        course_id = course_data.get('Code')
        
        # Data Transformation
        credits_str = course_data.get('Credits', '0').split(' ')[0]
        try:
            credits = int(float(credits_str))
        except:
            credits = 0 
            
        offered_str = course_data.get('Offered', '').lower()
        semesters = []
        if 'fall' in offered_str: semesters.append('Fall')
        if 'spring' in offered_str: semesters.append('Spring')
        if 'summer' in offered_str: semesters.append('Summer')
            
        prerequisites = [] # Using empty list for structured data consistency

        if course_id and course_id != 'N/A':
            try:
                cur.execute("""
                    INSERT INTO Courses (course_id, name, credits, semesters_offered, prerequisites, description)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (course_id) DO NOTHING;
                """, (
                    course_id,
                    course_data.get('Name'),
                    credits,
                    json.dumps(semesters), 
                    json.dumps(prerequisites),
                    course_data.get('Description')     
                ))
                courses_inserted += 1
            except Exception as e:
                print(f"Error inserting master course {course_id}: {e}")
                
    print(f"✅ Successfully inserted/verified {courses_inserted} courses.")
    return courses_inserted

def insert_programs_and_requirements(cur, master_catalog):
    """Inserts Program and Requirement data from the Program Scraper."""
    programs_inserted = 0
    requirements_inserted = 0
    print(f"\n--- Inserting {len(master_catalog.programs)} Programs and Requirements ---")
    
    for program_name, program_obj in master_catalog.programs.items():
        try:
            # A. Insert the Program (Major/Minor)
            cur.execute("""
                INSERT INTO Programs (name, type)
                VALUES (%s, %s)
                ON CONFLICT (name) DO UPDATE SET type = EXCLUDED.type
                RETURNING program_id;
            """, (program_name, program_obj.type))
            
            program_id = cur.fetchone()[0]
            programs_inserted += 1
            
            # B. Insert all associated Requirements
            for req_detail in program_obj.details:
                options_list = [c['code'] for c in req_detail['courses']] 
                
                cur.execute("""
                    INSERT INTO Requirements (program_id, description, options_pool)
                    VALUES (%s, %s, %s);
                """, (
                    program_id,
                    req_detail['text'],
                    json.dumps(options_list) 
                ))
                requirements_inserted += 1
                
        except Exception as e:
            print(f"Error inserting program {program_name}: {e}")
            
    print(f"✅ Successfully inserted {programs_inserted} programs and {requirements_inserted} requirements.")
    return programs_inserted, requirements_inserted


if __name__ == '__main__':
    conn = None
    try:
        # --- 1. EXECUTE MASTER LIST SCRAPER VIA SUBPROCESS ---
        print(f"Starting external scraper: {MASTER_SCRAPER_PATH}...")
        result = subprocess.run(['python', MASTER_SCRAPER_PATH], capture_output=True, text=True, check=True)
        print(result.stdout)
        
        # --- 2. LOAD DATA FROM JSON FILE ---
        if not os.path.exists(JSON_FILE_PATH):
            raise FileNotFoundError(f"Scraper failed to create required file: {JSON_FILE_PATH}")
            
        with open(JSON_FILE_PATH, 'r') as f:
            master_courses_list = json.load(f)

        # --- 3. EXECUTE PROGRAM/REQUIREMENTS SCRAPER (rpi-courses library) ---
        program_catalog = load_latest_rpi_catalog()     

        # --- 4. CONNECT TO DB & INSERT DATA ---
        conn = connect_db()
        cur = conn.cursor()
        
        insert_master_courses(cur, master_courses_list)
        insert_programs_and_requirements(cur, program_catalog)
        
        conn.commit()
        cur.close()
        print("\n✨ Database fully populated and transaction committed! ✨")

    except subprocess.CalledProcessError as e:
        print(f"\nCRITICAL FAILURE: Master List Scraper failed to run. Output: {e.stdout}")
        if e.stderr: print(f"Error: {e.stderr}")
    except Exception as e:
        print(f"\nCRITICAL FAILURE during DB loading: {e}")
        if conn: conn.rollback()
    finally:
        if conn: conn.close()