import pytz
import locale
import re
from datetime import datetime

USER = None
PASSWORD = None
TO_SEND = None

ISRAEL = pytz.timezone('Israel')
locale.setlocale(locale.LC_ALL, "he_IL")

REGEX_FOLDER_ID = re.compile(r'folderID=%22(.*)%22')

SEMESTERS = {'סמסטר א': 'Semester 1',
             'סמסטר ב': 'Semester 2',
             'סמסטר קיץ': 'Summer',
             'קורס שנתי': 'Semester 1 or 2'}

YEARS = {2020: '2020-21',
         2019: '2019-20'}

SERVERS = {'A300 - אודוטוריום הנדסה': 'PNPSERVER-A300',
           'מתמטיקה 2': 'PNPSERVER-MATH-2',
           'אולם קנדה': 'PNPSERVER-CANAD',
           'קפלן': 'PNPSERVER-KAPLA',
           'רוטברג': 'PNPSERVER-ROTBERG',
           'פלדמן א': 'PNPSERVER-FELD-A',
           'פלדמן ב': 'PNPSERVER-FELD-B',
           'כימיה 7': 'PNPSERVER-CHEM7',
           'לוין': 'PNPSERVER-LEVIN',
           'שפרינצק 115': 'PNPSERVER-SP115',
           'שפרינצק 117': 'PNPSERVER-SP117',
           'שפרינצק 215': 'PNPSERVER-SP215',
           'שפרינצק 214': 'PNPSERVER-SP214',
           'שפרינצק 217': 'PNPSERVER-SP217',
           'מדעי המחשב - C220': 'PNPSERVER-C220',
           'מדעי המחשב - C320': 'PNPSERVER-C320',
           'מדעי המחשב - C221': 'PNPSEREVR-C221',
           'מתמטיקה 110': 'PNPSERVER-MATH-110',
           'לוי 6': 'PNPSERVER-LEVI-6',
           'לוי 7': 'PNPSERVER-LEVI-7',
           'כדור הארץ 102': 'PNPSERVER-EARTH-102',
           'ראשל': 'PNPSERVER-RASHEL',
           'סילברמן 502': 'PNPSERVER-502'}

COLUMN_NAMES = {'Timestamp': 'TIMESTAP',
                'בחרו תיאור להקלטה (לא חובה)': 'DESCRIPTION',
                'בחרו כותרת להקלטה (לא חובה)': 'TITLE',
                'בחרו שעת סיום': 'END_TIME',
                'בחרו שעת התחלה': 'START_TIME',
                'בחרו תאריך הקלטה': 'DATE',
                'אולם הקלטה': 'RECORDER',
                'מהי שנת הלימודים? (בחרו את השנה הלועזית שהשנה מתחילה)': 'YEAR',
                'מה הסמסטר?': 'SEMESTER',
                'מה מספר הקורס?': 'ID',
                'האם יש מצגת?': 'IS_PRESENTATION',
                'קישור לתיקייה': 'FOLDER_ID',
                'האם ההקלטה חוזרת על עצמה כל שבוע?': 'IS_REPEAT'}

PANOPTO_SERVER_NAME = 'huji.cloud.panopto.eu'
PANOPTO_CLIEND_ID = None
PANOPTO_SECRET = None
BASE_URL = 'https://{0}/Panopto/api/v1/'.format(PANOPTO_SERVER_NAME)
END_DATE_SEMESTER_A = datetime(year=2021, day=29, month=1, tzinfo=pytz.UTC)
END_DATE_SEMESTER_B = datetime(year=2021, day=1, month=7, tzinfo=pytz.UTC)

