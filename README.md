# TRRAM: The Retro Registering Autonomous Manifesto

## hackrpi2025

### Introduction

TRRAM is a web platform designed to help RPI students navigate course registration, understand degree requirements, and build personalized four-year academic plans. The system integrates data scraped from the school's course catalog, major requirement pages, RateMyProfessor, and the school Student Information System (SIS) to generate tailored recommendations.

### Features

1. **Major-Specific Course Guidance**
    - Displays required courses for each major or concentration
    - Provides recommended sequencing based on prerequisites and program structure
    - Highlights prerequisite chains, co-requisites, and courses with limited availability

2. **Registration Assistance**
    - Suggests courses to take each semester based on progress and requirements
    - Shows instructor comparisons using RateMyProfessors data
    - Enables filtering by difficulty, rating, requirement category, and availability

3. **Integrated Scraped Data**
    - Course catalog: descriptions, credits, scheduling, prerequisites
    - Major requirement trees: cores, electives, distributions
    - RateMyProfessors: instructor ratings and feedback
    - SIS data: course offerings and semester availability (only when permitted by institutional policy)

4. **Personalized Four-Year Planning**
    - Auto-generates a four-year plan based on the selected major
    - Allows drag-and-drop reordering of courses across semesters
    - Tracks progress toward graduation requirements in real time

5. **Interest-Based Elective Recommendations**
    - Suggests electives based on interests expressed by the student
    - Identifies themes and clusters of courses related to selected interests
    - Recommends courses outside the major that match student goals

6. **Minor and Dual Major Suggestions**
    - Analyzes requirement overlap to propose viable minors or second majors
    - Estimates additional credits needed and earliest completion timeline
    - Integrates minor/dual-major paths into the four-year plan

### System Overview

#### Data Scraper
- Scrapes course catalog information
- Extracts degree requirements by major
- Collects instructor and course reviews from RateMyProfessors
- Normalizes all scraped data into a unified JSON schema

#### Backend API
- Serves course, requirement, and recommendation data
- Manages user plans, progress, and preference saving
- Includes logic for prerequisite resolution and course sequencing
- Frontend Web Application

#### Searchable course database
- Four-year plan builder
- Major/minor comparison interface
- Registration suggestion dashboard
- Tech Stack:
    1. Frontend: React, TypeScript, Tailwind CSS
    2. Backend: Node.js (Express) or Python (FastAPI)
    3. Database: PostgreSQL or MongoDB
    4. Scraping: Python (BeautifulSoup, Requests, Selenium)
    5. Deployment: Vercel, Netlify, AWS, or Docker

### Installation

1. Clone the repository:
```
git clone https://github.com/trivikak/hackrpi2025
cd hackrpi2025
```

2. Backend Setup
```
cd backend
npm install
npm run dev
```

2. Frontend Setup
```
cd frontend
npm install
npm run dev
```

3. Scraper Setup
```
cd scraper
pip install -r requirements.txt
python scrape.py
```

### Data Use and Compliance
Before scraping or integrating data, confirm compliance with:
- Institutional Terms of Service
- Robots.txt guidelines for external sites
- Policies governing SIS or internal academic systems
- Do not collect or store student-identifiable information.
- Avoid scraping authenticated SIS content unless explicitly permitted.

### Roadmap
- Add multi-major planning support
- Integrate schedule conflict detection
- Expand elective recommendation model
- Enable exporting plans to PDF and calendars
- Add user authentication and cloud data syncing

### Contributing
- Contributions are welcome.
- Open issues for bugs, questions, or feature suggestions.
- Submit pull requests following standard GitHub workflow.

### License
MIT License