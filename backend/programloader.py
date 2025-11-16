import json
import psycopg2
import os
from dotenv import load_dotenv

# Load PostgreSQL credentials
load_dotenv()

PROGRAMS_JSON = "normalized_programs.json"  # your scraped JSON file

def load_programs(json_path=PROGRAMS_JSON):
    print("📘 Loading program file...")
    with open(json_path, "r", encoding="utf-8") as f:
        programs = json.load(f)

    # Connect to PostgreSQL
    conn = psycopg2.connect(
        host=os.getenv("PGHOST"),
        database=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
        port=os.getenv("PGPORT")
    )
    cur = conn.cursor()

    print(f"📥 Inserting {len(programs)} programs into the database...")

    for p in programs:
        # 1️⃣ Insert into ProgramsNew table
        cur.execute(
            """
            INSERT INTO ProgramsNew (name, type)
            VALUES (%s, %s)
            ON CONFLICT (name) DO NOTHING
            RETURNING program_id;
            """,
            (p["name"], p["type"])
        )
        # Get the program_id (newly inserted or existing)
        program_id = cur.fetchone()
        if not program_id:
            # Already exists, fetch it
            cur.execute("SELECT program_id FROM ProgramsNew WHERE name=%s", (p["name"],))
            program_id = cur.fetchone()
        program_id = program_id[0]

        # 2️⃣ Insert course links into ProgramCoursesNew
        for course_code in p.get("courses", []):
            cur.execute(
                """
                INSERT INTO ProgramCoursesNew (program_id, course_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING;
                """,
                (program_id, course_code)
            )

    conn.commit()
    cur.close()
    conn.close()
    print("✅ Finished inserting program data!")


if __name__ == "__main__":
    load_programs()
