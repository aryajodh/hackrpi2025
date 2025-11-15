import logging
import logging.handlers
import sys

DEBUG = False
LOG_FILENAME = 'logging'

# P3: Logging setup remains identical
logger = logging.getLogger('rpi_courses')

# P3 Fix: The if/else block for NullHandler can be simplified in modern Python, 
# but the original logic is preserved for maximum compatibility across older environments.
if hasattr(logging, 'NullHandler'):
    NullHandler = logging.NullHandler
else:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

# fallback, so there's no warning of no handlers
logger.addHandler(NullHandler())

# P3: These strings are identical and valid
SIS_URL = "http://sis.rpi.edu/reg/"
ROCS_URL = "http://sis.rpi.edu/reg/rocs/"
HTML_URL = "http://sis.rpi.edu/stuclshr.htm"
COMM_URL = "http://www.rpi.edu/dept/srfs/CI"

# P3: The dictionary structure is identical and valid
DEPARTMENTS = dict(
    ARCH="Architecture",
    LGHT="Lighting",
    BMED="Biomedical Engineering",
    CHME="Chemical Engineering",
    CIVL="Civil Engineering",
    ECSE="Electrical, Computer, and Systems Engineering",
    ENGR="General Engineering",
    ENVE="Environmental Engineering",
    ESCI="Engineering Science",
    ISYE="Industrial and Systems Engineering",
    MANE="Mechanical, Aerospace, and Nuclear Engineering",
    MTLE="Materials Science and Engineering",
    ARTS="Arts",
    COMM="Communication",
    IHSS="Interdisciplinary Studies",
    INQR="Inquiry",
    LANG="Foreign Languages",
    LITR="Literature",
    PHIL="Philosophy",
    STSO="Science and Technology Studies (Humanities Courses)",
    WRIT="Writing",
    COGS="Cognitive Science",
    ECON="Economics",
    GSAS="Games Simulation Arts and Sciences",
    PSYC="Psychology",
    ITWS="Information Technology and Web Science",
    MGMT="Management",
    ASTR="Astronomy",
    BCBP="Biochemistry and Biophysics",
    BIOL="Biology",
    CHEM="Chemistry",
    CSCI="Computer Science",
    ISCI="Interdisciplinary Science",
    ERTH="Earth and Environmental Science",
    MATH="Mathematics",
    MATP="Mathematical Programming, Probability, and Statistics",
    PHYS="Physics",
    IENV="Interdisciplinary Environmental Courses",
    USAF="Aerospace Studies (Air Force ROTC)",
    USAR="Military Science (Army ROTC)",
    USNA="Naval Science (Navy ROTC",
)