require('dotenv').config();
const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors'); 

const app = express();
// Setting the port to 3001 is common for backends when the frontend uses 3000
const PORT = 3001; 

// --- Middleware Setup ---
app.use(cors()); // Allows frontend to make requests
app.use(bodyParser.json()); // Allows server to read incoming JSON data

// Basic Test Route
app.get('/', (req, res) => {
    res.send('Course Planning Backend is Ready!');
});

// --- CORE FEATURE ENDPOINT: Plan Generation ---
app.post('/api/plan/generate', (req, res) => {
    // Destructure the expected data from the request body
    const { major, minor, concentration, start_year } = req.body;

    console.log(`Received request for: ${major} (Starting Year: ${start_year})`);

    // In the future, this is where your database logic and planning algorithm will go.
    
    // --- DUMMY RESPONSE (for testing the connection) ---
    const coursePlan = {
        major: major,
        year_1: [
            { course_id: 'CSCI 1100', name: 'CS I', semester: 'Fall', credits: 4 },
            { course_id: 'MATH 1010', name: 'Calc I', semester: 'Fall', credits: 4 },
        ],
        message: `Plan generated successfully for ${major}. Now connect the frontend!`
    };

    // Send the structured data back to the frontend
    res.json(coursePlan);
});

// Start the server and listen on the defined port
app.listen(PORT, () => {
    console.log(`Server listening on port ${PORT}`);
    console.log(`Test API at http://localhost:${PORT}/api/plan/generate`);
});