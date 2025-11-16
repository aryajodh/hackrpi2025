import requests
from bs4 import BeautifulSoup
import json
import time

BASE_CATALOG_URL = "https://catalog.rpi.edu/content.php?catoid=33&navoid=873"
OUTPUT_FILE = "normalized_programs.json"

def fetch_soup(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")

def parse_main_catalog():
    print(f"Fetching main catalog page: {BASE_CATALOG_URL}")
    soup = fetch_soup(BASE_CATALOG_URL)
    programs = []

    current_type = None

    # Loop through all strong and li elements to detect type and program links
    for elem in soup.find_all(['strong', 'li']):
        if elem.name == 'strong':
            text = elem.get_text(strip=True).lower()
            if "baccalaureate - dual major" in text or "baccalaureate" in text:
                current_type = "major"
            elif "minor" in text:
                current_type = "minor"
            else:
                current_type = None
        elif elem.name == 'li' and current_type:
            a = elem.find('a', href=True)
            if a:
                program_name = a.get_text(strip=True)
                program_url = "https://catalog.rpi.edu/" + a['href']
                programs.append({
                    "type": current_type,
                    "name": program_name,
                    "url": program_url
                })

    print(f"✅ Found {len(programs)} programs on main catalog page.")
    return programs

def parse_program_courses(program_url):
    """
    Given a program URL, extract all course codes listed on the page.
    Returns a list of course codes as strings.
    """
    soup = fetch_soup(program_url)
    course_codes = set()

    # Find all text nodes that look like course codes (e.g., CSCI 1100)
    for li in soup.find_all('li'):
        text = li.get_text(strip=True)
        matches = [m for m in text.split() if len(m) > 0]
        # Quick regex-style match: 3-4 letters + 4 digit number (optionally trailing letter)
        import re
        code_match = re.findall(r"[A-Z]{3,4}\s\d{4}[A-Z]?", text)
        for code in code_match:
            course_codes.add(code.strip())

    return list(course_codes)

def main():
    programs = parse_main_catalog()

    # Fetch courses for each program
    for idx, prog in enumerate(programs):
        print(f"[{idx+1}/{len(programs)}] Fetching courses for: {prog['name']}")
        try:
            courses = parse_program_courses(prog['url'])
            prog['courses'] = courses
        except Exception as e:
            print(f"⚠️ Failed to fetch courses for {prog['name']}: {e}")
            prog['courses'] = []

        time.sleep(1)  # polite delay

    # Save output
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(programs, f, indent=4, ensure_ascii=False)
    print(f"\n✅ Saved {len(programs)} programs to '{OUTPUT_FILE}'")

if __name__ == "__main__":
    main()
