// plannerLogic.js
const db = require('./db');

/**
 * Step 1 in the agent: Fetches all academic requirements (Major, Minor, Concentration)
 * from the database.
 */
async function getRequirements(major, minor, concentration) {
    // 1. Combine all programs the user is seeking. Filter out any that are null/empty.
    const programs = [major, minor, concentration].filter(Boolean);
    
    // 2. Fetch the program IDs for the user's selections.
    // Use an array of program names for the SQL IN clause.
    const programIdsQuery = 'SELECT program_id FROM Programs WHERE name = ANY($1)';
    const programIdResult = await db.query(programIdsQuery, [programs]);

    const ids = programIdResult.rows.map(row => row.program_id);

    if (ids.length === 0) {
        throw new Error('No programs found for the selected options.');
    }
    
    // 3. Fetch all requirements linked to those program IDs.
    const requirementsQuery = `
        SELECT r.*, p.name AS program_name
        FROM Requirements r
        JOIN Programs p ON r.program_id = p.program_id
        WHERE r.program_id = ANY($1)
    `;
    const requirementsResult = await db.query(requirementsQuery, [ids]);

    // 4. Fetch the entire course catalog (we need prerequisites and semesters offered)
    const courseCatalogResult = await db.query('SELECT * FROM Courses', []);

    return {
        requirements: requirementsResult.rows,
        catalog: courseCatalogResult.rows
    };
}


const db = require('./db'); 
// Assuming getRequirements is defined and exported in this file as well
// const { getRequirements } = require('./plannerLogic'); 

// --- Helper Function ---
/**
 * Maps all course prerequisites into a structure for easy checking.
 * @param {Array} catalog - The full course catalog array.
 * @returns {Map<string, number>} A Map where key is course_id and value is the count of *unmet* prerequisites.
 */
function initializePrereqStatus(catalog) {
    const prereqStatus = new Map();
    // Initially, assume all prerequisites are unmet (count = number of prereqs)
    for (const course of catalog) {
        const prereqs = course.prerequisites || [];
        prereqStatus.set(course.course_id, prereqs.length);
    }
    return prereqStatus;
}

// --- CORE SCHEDULING AGENT ---
/**
 * Implements the Rule-Based Scheduling Algorithm.
 * @param {Array} requirements - Array of requirements specific to the user's programs.
 * @param {Array} catalog - The full course catalog from the database.
 * @param {Array} completedCourses - Course IDs the student has already taken.
 * @param {number} startYear - The starting year for the 4-year plan.
 * @returns {object} The structured 8-semester course plan.
 */
function generatePlan(requirements, catalog, completedCourses, startYear) {
    
    // 1. Requirement Resolution & Pre-processing (Rule 3.1)
    let requiredCourseIDs = new Set();
    const courseLookup = new Map(catalog.map(c => [c.course_id, c]));
    
    // Simple resolution: For now, we only look at specific courses listed in the options_pool
    // (A real app would handle "choose 3 credits of X" later)
    requirements.forEach(req => {
        if (req.options_pool && Array.isArray(req.options_pool)) {
            req.options_pool.forEach(id => {
                if (courseLookup.has(id)) {
                    requiredCourseIDs.add(id);
                }
            });
        }
    });

    // Remove already completed courses
    completedCourses.forEach(id => requiredCourseIDs.delete(id));

    // Convert Set to an array for easier manipulation
    let coursePool = Array.from(requiredCourseIDs); 
    
    // Initialize Prerequisite Tracking (Rule 3.1)
    const prereqStatus = initializePrereqStatus(catalog);
    
    // Pre-seed the system by fulfilling prereqs for completed courses
    completedCourses.forEach(completedId => {
        const completedCourse = courseLookup.get(completedId);
        if (completedCourse) {
            // Find all courses that depend on this completed course and decrement their unmet count
            catalog.forEach(course => {
                if (course.prerequisites && course.prerequisites.includes(completedId)) {
                    prereqStatus.set(course.course_id, prereqStatus.get(course.course_id) - 1);
                }
            });
        }
    });

    // 2. Initialize 8-Semester Schedule (Rule 3.1)
    const semesters = ['Fall', 'Spring'];
    const schedule = [];
    const MAX_CREDITS = 16; // Standard max credit load per semester

    // 3. Iterative Semester Scheduling (Rule 3.2)
    for (let year = 0; year < 4; year++) {
        for (let semesterIndex = 0; semesterIndex < semesters.length; semesterIndex++) {
            const currentSemester = semesters[semesterIndex];
            const currentYear = startYear + year;
            
            const scheduleSlot = {
                year: currentYear,
                semester: currentSemester,
                courses: [],
                credits: 0
            };

            // 4. Identify and Sort Eligible Courses (Rule 3.3, 3.4)
            const eligibleCourses = coursePool
                .map(id => courseLookup.get(id))
                .filter(course => {
                    // Rule 3.3 Check 1: Must be offered in this semester
                    const isOffered = course.semesters_offered && course.semesters_offered.includes(currentSemester);
                    
                    // Rule 3.3 Check 2: All prerequisites must be met (unmet count is zero)
                    const prereqsMet = prereqStatus.get(course.course_id) === 0;

                    return isOffered && prereqsMet;
                })
                .sort((a, b) => {
                    // Rule 3.4 Priority: Prioritize courses with fewer offerings (only offered in Fall, for example)
                    // and courses that unlock more other courses (highest fan-out).
                    // This is a simplified priority for illustration.
                    return (a.semesters_offered.length - b.semesters_offered.length);
                });

            // 5. Schedule Courses (Rule 3.4)
            const scheduledThisSemester = [];
            for (const course of eligibleCourses) {
                if (scheduleSlot.credits + course.credits <= MAX_CREDITS) {
                    scheduleSlot.courses.push({
                        id: course.course_id,
                        name: course.name,
                        credits: course.credits
                    });
                    scheduleSlot.credits += course.credits;
                    scheduledThisSemester.push(course.course_id);
                }
            }

            // 6. Update State (Rule 3.4)
            scheduledThisSemester.forEach(scheduledId => {
                // Remove from the pool of courses yet to be scheduled
                coursePool = coursePool.filter(id => id !== scheduledId);

                // Update dependents' prereq status
                catalog.forEach(course => {
                    if (course.prerequisites && course.prerequisites.includes(scheduledId)) {
                        prereqStatus.set(course.course_id, prereqStatus.get(course.course_id) - 1);
                    }
                });
            });

            schedule.push(scheduleSlot);
            
            // If no courses were scheduled, we break to avoid infinite loops 
            // and indicate a major scheduling conflict (e.g., core course not offered)
            // A robust planner would handle conflicts more gracefully.
            if (scheduledThisSemester.length === 0 && coursePool.length > 0) {
                 // Do not break yet, let the loop continue to the next year
            }
        }
    }

    // 7. Final Output (Rule 3.5)
    return {
        schedule: schedule,
        unmet_requirements: coursePool.map(id => ({
            course_id: id,
            reason: "Could not be scheduled due to timing, prerequisites, or credit limits."
        })),
        message: `Plan generated successfully, with ${coursePool.length} requirements left unmet.`
    };
}

module.exports = {
    getRequirements: require('./getRequirements'), // Assuming getRequirements is in a separate file or exported here
    generatePlan
};