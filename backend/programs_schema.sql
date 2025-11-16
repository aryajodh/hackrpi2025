-- ---------------------------------------------------------------------
-- New tables for storing program/course outlines (without touching old tables)
-- ---------------------------------------------------------------------

-- Drop only if exists (safe)
DROP TABLE IF EXISTS ProgramCoursesNew;

-- Programs table (new)
CREATE TABLE ProgramsNew (
    program_id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    type VARCHAR(50) -- Major, Minor, Dual Major, etc.
);

-- Link table for program requirements / courses
CREATE TABLE ProgramCoursesNew (
    program_course_id SERIAL PRIMARY KEY,
    program_id INTEGER NOT NULL REFERENCES ProgramsNew(program_id),
    course_id VARCHAR(10) NOT NULL, -- links to Courses.course_id
    semester_order INTEGER,          -- optional: order in curriculum
    placeholder BOOLEAN DEFAULT FALSE -- mark as user-selectable/flexible
);
