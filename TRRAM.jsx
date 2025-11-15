import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { RefreshCw, Search, Save, Loader, X, Sun, Moon, Terminal } from 'lucide-react';
import { initializeApp } from 'firebase/app';
import { getAuth, signInAnonymously, signInWithCustomToken, onAuthStateChanged } from 'firebase/auth';
import { 
  getFirestore, doc, onSnapshot, setDoc, serverTimestamp, setLogLevel
} from 'firebase/firestore';

// --- Global Variables (Provided by Canvas Environment) ---
const appId = typeof __app_id !== 'undefined' ? __app_id : 'default-trram-planner';
const firebaseConfig = typeof __firebase_config !== 'undefined' ? JSON.parse(__firebase_config) : null;
const initialAuthToken = typeof __initial_auth_token !== 'undefined' ? __initial_auth_token : null;
const API_KEY = ""; // Placeholder for the Gemini API Key

// --- Course Data Structure for AI Output (JSON Schema) ---
const COURSE_PLAN_SCHEMA = {
  type: "ARRAY",
  items: {
    type: "OBJECT",
    properties: {
      "semester": { "type": "STRING", "description": "e.g., Fall 1, Spring 2, Summer Arch" },
      "year": { "type": "INTEGER", "description": "Academic year number (1-4)" },
      "courses": {
        "type": "ARRAY",
        "items": {
          type: "OBJECT",
          properties: {
            "code": { "type": "STRING", "description": "Course code, e.g., CSCI 1100" },
            "title": { "type": "STRING", "description": "Course full title" },
            "credits": { "type": "INTEGER" },
            "isCore": { "type": "BOOLEAN", "description": "True if mandatory core/major requirement" },
            "isComplete": { "type": "BOOLEAN", "description": "False initially, toggled by user" }
          },
          required: ["code", "title", "credits", "isCore", "isComplete"]
        }
      }
    },
    required: ["semester", "year", "courses"]
  }
};

// --- System Instruction for Gemini (The RPI Academic Advisor) ---
const SYSTEM_INSTRUCTION = `
You are a highly specialized RPI Academic Advisor. Your task is to generate a comprehensive, 4-year (8-semester) course plan for a student based on their declared major(s).

Constraint: Every plan must adhere to the RPI "Arch" requirement: Year 2 ends with a mandatory Summer term ("Summer Arch"), and the following Fall or Spring term ("Year 3") must be an "Away" semester (empty courses).

RPI Core Requirements to Incorporate (Unless major is HASS/Arch, assume Engineering/Science default):
1.  **Total Credits:** Target 128 credits total (4-credit courses are typical).
2.  **Semester Load:** Target 16 credits (4 courses) per Fall/Spring semester.
3.  **HASS Core:** 20 credits (Engineering) or 24 credits (Science/Mgmt/HASS). Must include:
    * 1 HASS Inquiry (INQR) course (Year 1).
    * 1 HASS Communication Intensive (CI) course (Years 1-2).
    * 1 HASS 4000-level course (Years 3-4).
    * A 12-credit Integrative Pathway (4 courses in depth).
4.  **Science Core:** Includes core Math (Calc I/II, Diff Eq, etc.) and Physics I/II.
5.  **Arch:** Summer Arch (Year 2) is a full semester; one away semester (Year 3) is empty.

Create a sequential, logical plan, ensuring prerequisites are met (e.g., Calc I before Calc II, CS I before Data Structures). You must ONLY return the JSON object following the provided schema. DO NOT include any explanatory text, markdown formatting, or notes outside the JSON block.
`;

// --- Utility Components for Retro Styling ---

/** Custom Hook for Dark Mode */
const useDarkMode = () => {
  const [isDarkMode, setIsDarkMode] = useState(false);

  useEffect(() => {
    // Check local storage for theme preference
    const savedTheme = localStorage.getItem('trram-theme');
    if (savedTheme === 'dark') {
      setIsDarkMode(true);
      document.documentElement.classList.add('dark');
    } else if (savedTheme === 'light') {
      setIsDarkMode(false);
      document.documentElement.classList.remove('dark');
    }
  }, []);

  const toggleDarkMode = useCallback(() => {
    setIsDarkMode(prev => {
      const newMode = !prev;
      if (newMode) {
        document.documentElement.classList.add('dark');
        localStorage.setItem('trram-theme', 'dark');
      } else {
        document.documentElement.classList.remove('dark');
        localStorage.setItem('trram-theme', 'light');
      }
      return newMode;
    });
  }, []);

  return [isDarkMode, toggleDarkMode];
};

/** Applies the CRT Terminal style to the entire app. */
const TerminalWrapper = ({ children, isDarkMode, toggleDarkMode, userId, appId }) => (
  <div className={`min-h-screen p-4 sm:p-8 flex flex-col items-center 
    ${isDarkMode 
        ? 'bg-[#111111] text-[#00ff00] font-mono' 
        : 'bg-gray-100 text-gray-900 font-mono'
    }`}
  >
    {/* Screen Container with Retro Look */}
    <div className={`w-full max-w-6xl p-4 sm:p-6 md:p-8 relative z-10
      ${isDarkMode
        ? 'border-4 border-[#00ff00] shadow-[0_0_20px_#00ff00,inset_0_0_10px_#00ff00] bg-[#001a00]'
        : 'border-4 border-gray-900 shadow-xl bg-white'
      } rounded-none overflow-hidden
    `}>
      {/* Scanline and CRT Glare Effects (CSS only) */}
      <style jsx="true">{`
        .crt::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: repeating-linear-gradient(
            #000000 0%,
            #000000 1px,
            #00000000 1px,
            #00000000 2px
          );
          opacity: 0.1;
          pointer-events: none;
          z-index: 100;
        }
        .crt::after {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          box-shadow: ${isDarkMode ? 'inset 0 0 100px #00ff0050' : 'none'};
          pointer-events: none;
          z-index: 101;
        }
        .cursor-blink::after {
          content: '_';
          animation: blink-cursor 1s step-end infinite;
          font-weight: bold;
        }
        @keyframes blink-cursor {
            0%, 100% { opacity: 0; }
            50% { opacity: 1; }
        }
      `}</style>
      
      <header className={`mb-6 border-b-4 pb-3 flex justify-between items-start 
          ${isDarkMode ? 'border-[#ffcc00]' : 'border-gray-900'}`
      }>
        <div>
          <h1 className={`text-2xl sm:text-3xl font-bold uppercase cursor-blink flex items-center`}>
            <Terminal className="w-5 h-5 sm:w-6 sm:h-6 mr-2 mb-1 text-[#ffcc00] dark:text-[#ffcc00]" />
            T.R.R.A.M. 
          </h1>
          <p className={`text-sm ml-7 italic ${isDarkMode ? 'text-[#ffcc00]' : 'text-indigo-600'}`}>
            The Retro Registration Autonomous Machine
          </p>
        </div>
        <div className="flex flex-col items-end">
            <button 
                onClick={toggleDarkMode}
                className={`p-2 border-2 text-sm transition-colors 
                ${isDarkMode 
                    ? 'border-[#00ff00] bg-[#004400] text-[#00ff00] hover:bg-[#006600]' 
                    : 'border-gray-900 bg-gray-300 text-gray-900 hover:bg-gray-400'
                }`}
                title="Toggle Theme"
            >
                {isDarkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>
            <p className={`mt-2 text-xs ${isDarkMode ? 'text-[#008800]' : 'text-gray-600'}`}>User ID: {userId ? userId.substring(0, 8) + '...' : 'N/A'}</p>
        </div>
      </header>

      <div className="crt text-sm sm:text-base">
        {children}
      </div>
    </div>
    <p className={`mt-4 text-xs ${isDarkMode ? 'text-[#008800]' : 'text-gray-500'}`}>
        System Status: Operational | App ID: {appId}
    </p>
  </div>
);

/** Generic button with retro styling */
const TerminalButton = ({ children, onClick, disabled, icon: Icon, className = '', isDarkMode }) => (
  <button
    onClick={onClick}
    disabled={disabled}
    className={`flex items-center justify-center space-x-2 px-3 py-2 border-2 font-bold uppercase disabled:opacity-50 disabled:cursor-not-allowed transition duration-150 rounded-none
    ${isDarkMode 
        ? 'border-[#00ff00] bg-[#004400] text-[#00ff00] shadow-[2px_2px_0_#00ff00] hover:bg-[#006600] hover:shadow-[3px_3px_0_#00ff00]' 
        : 'border-gray-900 bg-indigo-500 text-white shadow-[2px_2px_0_#333] hover:bg-indigo-600 hover:shadow-[3px_3px_0_#333]'
    }
    ${className}`}
  >
    {Icon && <Icon className="w-4 h-4" />}
    <span className="text-xs sm:text-sm">{children}</span>
  </button>
);

/** Display for a single course item */
const CourseItem = ({ course, onToggle, isDarkMode }) => (
  <div
    className={`p-2 border-b flex justify-between items-center cursor-pointer transition duration-100 rounded-none
    ${isDarkMode ? 'border-[#004400]' : 'border-gray-200'}
    ${course.isComplete
        ? `opacity-50 line-through ${isDarkMode ? 'text-[#008800]' : 'text-gray-500'}`
        : `${isDarkMode ? 'text-[#00ff00] hover:bg-[#002a00]' : 'text-gray-900 hover:bg-gray-100'}`
    }`}
    onClick={() => onToggle(course)}
    title="Click to toggle completion status"
  >
    <span className="font-bold w-1/4 truncate">{course.code}</span>
    <span className="w-1/2 truncate">{course.title}</span>
    <span className="w-1/4 text-right font-bold text-sm">
      {course.credits} cr.
      {course.isCore && 
        <span 
          className={`ml-2 text-xs px-1 py-0 border rounded-none 
            ${isDarkMode ? 'text-[#ffcc00] border-[#ffcc00]' : 'text-red-600 border-red-600'}
          `}
        >
          CORE
        </span>
      }
    </span>
  </div>
);


// --- Main Application Component ---
const App = () => {
  const [programs, setPrograms] = useState('');
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [db, setDb] = useState(null);
  const [auth, setAuth] = useState(null);
  const [userId, setUserId] = useState(null);
  const [authReady, setAuthReady] = useState(false);
  const [isDarkMode, toggleDarkMode] = useDarkMode();
  const documentId = 'default-plan'; 

  // --- Firebase Initialization and Authentication ---
  useEffect(() => {
    if (!firebaseConfig) {
      setError("System Error: Firebase config is missing.");
      setAuthReady(true);
      return;
    }
    
    try {
      setLogLevel('debug');
      const app = initializeApp(firebaseConfig);
      const authInstance = getAuth(app);
      const dbInstance = getFirestore(app);
      setDb(dbInstance);
      setAuth(authInstance);

      const unsubscribe = onAuthStateChanged(authInstance, async (user) => {
        if (user) {
          setUserId(user.uid);
          console.log("Auth State: Signed in. User ID:", user.uid);
        } else {
          // Attempt sign-in if needed
          if (initialAuthToken) {
            try {
              const userCredential = await signInWithCustomToken(authInstance, initialAuthToken);
              setUserId(userCredential.user.uid);
            } catch (err) {
              console.warn("Custom Token Sign-In Failed. Falling back to Anonymous.");
              const userCredential = await signInAnonymously(authInstance);
              setUserId(userCredential.user.uid);
            }
          } else {
            // No custom token, sign in anonymously
            const userCredential = await signInAnonymously(authInstance);
            setUserId(userCredential.user.uid);
          }
        }
        setAuthReady(true); 
      });

      return () => unsubscribe();
    } catch (err) {
      console.error("Firebase Init Error:", err);
      setError("System Error: Could not initialize Firebase services.");
      setAuthReady(true);
    }
  }, [initialAuthToken]);

  // --- Firestore Path Helper ---
  const getPlanDocRef = useCallback(() => {
    if (!db || !userId) return null;
    // Private data path: /artifacts/{appId}/users/{userId}/course_plans/default-plan
    return doc(db, 'artifacts', appId, 'users', userId, 'course_plans', documentId);
  }, [db, userId, appId, documentId]);

  // --- Load Plan from Firestore (Real-time Listener) ---
  useEffect(() => {
    const docRef = getPlanDocRef();
    if (!authReady || !docRef) return;
    
    const unsubscribe = onSnapshot(docRef, (docSnap) => {
      if (docSnap.exists()) {
        const data = docSnap.data();
        setPrograms(data.programs || '');
        setPlan(data.plan || null);
        console.log("Plan loaded from Firestore.");
      } else {
        console.log("No existing plan found in Firestore.");
        setPlan(null); 
      }
    }, (err) => {
      console.error("Firestore onSnapshot error:", err);
      setError("Error: Failed to load plan data.");
    });

    return () => unsubscribe();
  }, [authReady, getPlanDocRef]);

  // --- Save Plan to Firestore ---
  const savePlan = useCallback(async (currentPlan = plan) => {
    const docRef = getPlanDocRef();
    if (!docRef || !currentPlan) {
      setError("Error: Cannot save. Authentication or plan data is missing.");
      return;
    }
    
    setLoading(true);
    setError(null);
    try {
      await setDoc(docRef, {
        programs: programs,
        plan: currentPlan,
        userId: userId,
        updatedAt: serverTimestamp()
      }, { merge: true });
      console.log("Plan saved successfully!");
    } catch (e) {
      console.error("Error saving document: ", e);
      setError("Error: Failed to save the plan.");
    } finally {
      setLoading(false);
    }
  }, [getPlanDocRef, plan, programs, userId]);

  // --- Gemini API Call for Plan Generation ---
  const fetchPlan = async () => {
    if (!programs.trim()) {
      setError("Please enter your RPI program(s) first (e.g., 'CS, Dual Math').");
      return;
    }
    
    setLoading(true);
    setError(null);
    const userQuery = `Generate a 4-year, 8-semester course plan for a student entering RPI with the following program(s): ${programs.trim()}.`;
    
    const apiUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key=${API_KEY}`;

    const payload = {
        contents: [{ parts: [{ text: userQuery }] }],
        systemInstruction: { parts: [{ text: SYSTEM_INSTRUCTION }] },
        generationConfig: {
            responseMimeType: "application/json",
            responseSchema: COURSE_PLAN_SCHEMA,
        }
    };

    let attempts = 0;
    const maxAttempts = 5;
    let success = false;
    let generatedPlan = null;

    while (attempts < maxAttempts && !success) {
      attempts++;
      try {
        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        const jsonText = result.candidates?.[0]?.content?.parts?.[0]?.text;

        if (jsonText) {
          generatedPlan = JSON.parse(jsonText);
          success = true;
        } else {
          throw new Error("API returned no content.");
        }
      } catch (e) {
        // console.error(`Attempt ${attempts} failed.`, e); // Suppressing retry log
        if (attempts < maxAttempts) {
            await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, attempts - 1)));
        } else {
            setError("Error: Failed to generate plan after multiple retries. Try simplifying your input.");
        }
      }
    }

    if (success && generatedPlan) {
      setPlan(generatedPlan);
      await savePlan(generatedPlan); // Save immediately after successful generation
    }
    setLoading(false);
  };
  
  // --- Plan Modification Logic: Toggle Course Status ---
  const toggleCourseCompletion = useCallback((courseToToggle) => {
    setPlan(prevPlan => {
      if (!prevPlan) return prevPlan;

      // Ensure the course object passed includes the semester name for accurate targeting
      const updatedPlan = prevPlan.map(semester => ({
        ...semester,
        courses: semester.courses.map(course =>
          (course.code === courseToToggle.code && semester.semester === courseToToggle.semester)
            ? { ...course, isComplete: !course.isComplete }
            : course
        ),
      }));
      // Save the updated plan to Firestore immediately
      savePlan(updatedPlan); 
      return updatedPlan;
    });
  }, [savePlan]);

  // --- Credit Calculations ---
  const { totalCredits, completedCredits } = useMemo(() => {
    if (!plan) return { totalCredits: 0, completedCredits: 0 };
    
    const total = plan.reduce((sum, semester) => 
      sum + semester.courses.reduce((semSum, course) => semSum + course.credits, 0)
    , 0);

    const completed = plan.reduce((sum, semester) => 
      sum + semester.courses.reduce((semSum, course) => semSum + (course.isComplete ? course.credits : 0), 0)
    , 0);
    
    return { totalCredits: total, completedCredits: completed };
  }, [plan]);


  // --- Main Render ---
  const terminalAccent = isDarkMode ? 'text-[#ffcc00]' : 'text-indigo-600';
  const errorColor = isDarkMode ? 'border-[#ff0000] bg-[#440000] text-[#ff0000]' : 'border-red-600 bg-red-100 text-red-800';
  const infoColor = isDarkMode ? 'border-[#00ff00] bg-[#004400]' : 'border-green-600 bg-green-100';

  return (
    <TerminalWrapper isDarkMode={isDarkMode} toggleDarkMode={toggleDarkMode} userId={userId} appId={appId}>
      
      {/* Input Section */}
      <div className="w-full mb-6">
        <label htmlFor="programs" className="block mb-2 text-sm uppercase">
          PROGRAM INPUT:
        </label>
        <div className="flex flex-col sm:flex-row space-y-3 sm:space-y-0 sm:space-x-2">
          <input
            id="programs"
            type="text"
            value={programs}
            onChange={(e) => setPrograms(e.target.value)}
            disabled={loading || !authReady}
            className={`flex-grow p-2 border-2 focus:ring-0 focus:outline-none rounded-none
              ${isDarkMode 
                ? 'bg-[#111111] border-[#00ff00] text-[#00ff00] placeholder-[#008800]' 
                : 'bg-white border-gray-900 text-gray-900 placeholder-gray-500'
              }
            `}
            placeholder="> Enter programs and press GENERATE"
          />
          <TerminalButton onClick={fetchPlan} disabled={loading || !authReady} icon={Search} isDarkMode={isDarkMode}>
            {loading ? 'COMPUTING...' : 'GENERATE PLAN'}
          </TerminalButton>
        </div>
      </div>

      {/* Status and Error Messages */}
      {error && (
        <div className={`w-full p-3 mb-4 border-2 rounded-none flex items-center space-x-2 ${errorColor}`}>
          <X className="w-5 h-5" />
          <span className="font-bold">ERROR:</span> <span>{error}</span>
        </div>
      )}

      {loading && (
        <div className={`w-full p-3 mb-4 text-center border-2 rounded-none flex items-center justify-center space-x-2 animate-pulse ${infoColor} ${isDarkMode ? 'text-[#00ff00]' : 'text-green-800'}`}>
          <Loader className="w-5 h-5 animate-spin" />
          <span className="uppercase">Contacting Autonomous Logic Core... Analyzing Data Stream...</span>
        </div>
      )}
      
      {/* Plan Summary and Controls */}
      {plan && (
        <div className={`w-full mb-6 p-4 border-2 rounded-none ${isDarkMode ? 'border-[#00ff00] bg-[#001a00]' : 'border-gray-900 bg-gray-50'}`}>
          <h2 className={`text-xl uppercase font-bold mb-3 border-b pb-1 ${isDarkMode ? 'border-[#004400]' : 'border-gray-300'}`}>
            T.R.R.A.M. Output: Programs ({programs})
          </h2>
          <div className="flex justify-between text-sm mb-3">
            <p>
              <span className={terminalAccent}>TOTAL CREDITS:</span> {totalCredits} / ~128
            </p>
            <p>
              <span className={terminalAccent}>COMPLETED CREDITS:</span> {completedCredits}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <TerminalButton onClick={() => savePlan(plan)} disabled={loading || !authReady} icon={Save} isDarkMode={isDarkMode}>
              Save Progress
            </TerminalButton>
            <TerminalButton onClick={() => setPlan(null)} disabled={loading} icon={X} className={isDarkMode ? 'bg-[#440000]' : 'bg-red-500'} isDarkMode={isDarkMode}>
              Clear Plan
            </TerminalButton>
            <TerminalButton onClick={fetchPlan} disabled={loading || !authReady} icon={RefreshCw} isDarkMode={isDarkMode}>
              Regenerate Plan
            </TerminalButton>
          </div>
        </div>
      )}

      {/* Schedule Display Grid */}
      {plan ? (
        <div className="w-full grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
          {plan.map((semester, index) => (
            <div
              key={index}
              className={`border-2 p-3 rounded-none 
                ${semester.semester.includes('Away')
                  ? `${isDarkMode ? 'border-dashed border-[#ffcc00] bg-[#1a001a]' : 'border-dashed border-yellow-600 bg-yellow-50'}`
                  : `${isDarkMode ? 'border-[#00ff00] bg-[#001a00]' : 'border-gray-900 bg-white'}`
                }`
              }
            >
              <h3 className={`text-lg font-bold mb-2 uppercase text-center border-b pb-1 
                  ${isDarkMode ? 'border-[#00ff00]' : 'border-gray-700'}`
              }>
                {semester.semester} (Year {semester.year})
              </h3>
              
              {semester.courses.length === 0 ? (
                <p className={`italic text-center py-4 ${terminalAccent}`}>
                  {semester.semester.includes('Away') ? 'ARCH AWAY SEMESTER' : 'FREE TERM'}
                </p>
              ) : (
                <>
                  {semester.courses.map((course, courseIndex) => (
                    <CourseItem 
                      key={courseIndex} 
                      course={{...course, semester: semester.semester}} // Add semester for unique toggle
                      onToggle={toggleCourseCompletion} 
                      isDarkMode={isDarkMode}
                    />
                  ))}
                  <div className={`text-sm mt-2 pt-2 border-t text-right 
                    ${isDarkMode ? 'border-[#004400] text-[#008800]' : 'border-gray-300 text-gray-600'}`}>
                    Total: {semester.courses.reduce((sum, c) => sum + c.credits, 0)} Credits
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className={`w-full text-center p-12 border-2 border-dashed rounded-none mt-10 
          ${isDarkMode ? 'border-[#00ff00] text-[#00ff00]' : 'border-gray-500 text-gray-600'}`}>
            <Terminal className={`w-10 h-10 mx-auto mb-4 animate-pulse ${terminalAccent}`} />
            <p className="text-lg uppercase">Awaiting Student Program Data.</p>
            <p className="text-sm mt-2">Enter your major(s) above and click 'Generate Plan' to begin system processing.</p>
        </div>
      )}
    </TerminalWrapper>
  );
};

export default App;
