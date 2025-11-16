-- SCHEMA.SQL
-- Creates the required tables: Programs, Courses, and Requirements.

-- ---------------------------------------------------------------------
-- DROP EXISTING TABLES (for safe re-runs during development)
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS Requirements;
DROP TABLE IF EXISTS Courses;
DROP TABLE IF EXISTS Programs;

-- ---------------------------------------------------------------------
-- 1. Programs Table
-- Stores the list of academic programs (Majors, Minors, Concentrations)
-- ---------------------------------------------------------------------
CREATE TABLE Programs (
    program_id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    type VARCHAR(50) -- e.g., 'Major', 'Minor', 'Concentration'
);

-- ---------------------------------------------------------------------
-- 2. Courses Table
-- The full course catalog, including all constraints for the planner logic.
-- Note: JSONB is used for arrays (prerequisites, semesters_offered)
-- ---------------------------------------------------------------------
CREATE TABLE Courses (
    course_id VARCHAR(10) PRIMARY KEY, -- e.g., 'CSCI 1100'
    name VARCHAR(255) NOT NULL,
    credits INTEGER NOT NULL,
    
    -- An array of strings: ['Fall', 'Spring', 'Summer']
    semesters_offered JSONB NOT NULL,
    
    -- An array of strings: ['MATH 1010', 'CSCI 1100']
    prerequisites JSONB
);

-- ---------------------------------------------------------------------
-- 3. Requirements Table
-- Links a program to a specific requirement, listing the courses that satisfy it.
-- ---------------------------------------------------------------------
CREATE TABLE Requirements (
    requirement_id SERIAL PRIMARY KEY,
    program_id INTEGER NOT NULL REFERENCES Programs(program_id),
    
    -- Descriptive text for the requirement (e.g., "Introductory Programming Sequence")
    description TEXT,
    
    -- An array of valid course IDs that satisfy this requirement.
    -- The planner must pick one from this list.
    options_pool JSONB NOT NULL
);