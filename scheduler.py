import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from panopto_folders import PanoptoFolders
from panopto_oauth2 import PanoptoOAuth2
import urllib3
import requests
import json
from datetime import datetime
from urllib.parse import quote
from dateutil import parser, rrule
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import schedule
import argparse
import config
import socket


def parse_argument():
    '''
    Argument definition and handling.
    '''
    arg_parser = argparse.ArgumentParser(description='Schedule videos to panopto')
    arg_parser.add_argument('--client-id', dest='client_id', required=True, help='Client ID of OAuth2 client')
    arg_parser.add_argument('--client-secret', dest='client_secret', required=True,
                            help='Client Secret of OAuth2 client')
    arg_parser.add_argument('--user', dest='user', required=False, help='What is your mail user')
    arg_parser.add_argument('--password', dest='password', required=False, help='What is your mail password?')
    arg_parser.add_argument('--google-json', dest='google_json', required=True, help='What is your mail password?')

    args = arg_parser.parse_args()
    config.PANOPTO_CLIEND_ID = args.client_id
    config.PANOPTO_SECRET = args.client_secret
    config.USER = args.user
    config.TO_SEND = [args.user]
    config.PASSWORD = args.password
    config.GOOGLE_JSON = args.google_json


def authorization(requests_session, oauth2):
    # Go through authorization
    access_token = oauth2.get_access_token_authorization_code_grant()
    # Set the token as the header of requests
    requests_session.headers.update({'Authorization': 'Bearer ' + access_token})


class Recording:
    def __init__(self, row, name, description, folder_id, year, semester, date,
                 start_time, end_time, course_id, recorder, is_presentation, is_repeat):
        self.row = row
        self.name = name
        self.description = description
        self.folder_id = folder_id
        self.year = config.YEARS[year]
        self.semester = config.SEMESTERS[semester]
        self.date = date
        self.start_time = start_time
        self.end_time = end_time
        self.course_id = course_id
        self.recorder = recorder
        self.is_presentation = True
        if is_presentation == 'לא':
            self.is_presentation = False
        self.is_repeat = False
        if is_repeat == 'כן':
            self.is_repeat = True
        self.sessions_id = []
        self.start_dates = []
        self.end_dates = []
        self.names = []
        self.final_date = config.END_DATE_SEMESTER_A if semester == 'Semester 1' else config.END_DATE_SEMESTER_B
        self.success = False

    def __str__(self):
        string = ''
        if not self.success:
            return f"The problem was with {self.course_id} {self.semester}, {self.date} in {self.recorder}\n"
        for start_date, end_date, name, session_id in zip(self.start_dates, self.end_dates, self.names,
                                                          self.sessions_id):
            string += f'Course {self.course_id} {self.semester} in {self.recorder}.\n' \
                      f'Title is {name} and it is in {start_date.strftime("%x")} between {start_date.strftime("%X")}-{end_date.strftime("%X")}' \
                      f'\n' \
                      f'The video will broadcast live in https://huji.cloud.panopto.eu/Panopto/Pages/Viewer.aspx?id={session_id}\n\n'
        return string

    def schedule(self, recorder_server, start_date: datetime, end_date: datetime):
        if self.is_repeat:
            self.start_dates = [start for start in rrule.rrule(rrule.WEEKLY, dtstart=start_date, until=self.final_date)]
            self.end_dates = [end for end in rrule.rrule(rrule.WEEKLY, dtstart=end_date, until=self.final_date)]
        else:
            self.start_dates = [start_date]
            self.end_dates = [end_date]

        for start_date, end_date in zip(self.start_dates, self.end_dates):
            if self.name != '':
                name = start_date.strftime(f"{self.course_id}, {self.name}, %A, %X, %x")
            else:
                name = start_date.strftime(f"{self.course_id}, %A, %X, %x")
            self.names.append(name)
            sr = {
                "Name": name,
                "Description": self.description,
                "StartTime": start_date.isoformat(),
                "EndTime": end_date.isoformat(),
                "FolderId": self.folder_id,
                'Recorders': [
                    {
                        'RemoteRecorderId': recorder_server['Id'],
                        'SuppressPrimary': False,
                        'SuppressSecondary': not self.is_presentation,
                    }
                ],
                'IsBroadcast': True,
            }
            url = config.BASE_URL + "scheduledRecordings?resolveConflicts=false"
            print('Calling POST {0}'.format(url))
            create_resp = requests_session.post(url=url, json=sr).json()
            print("POST returned:\n" + json.dumps(create_resp, indent=2))
            if 'Id' in create_resp:
                self.sessions_id.append(create_resp['Id'])
            else:
                subject = 'לא ניתן לתזמן הקלטה'
                body = f"We have a problem with Scheduling {name}.\n" \
                       f"Probably times are wrong. Please call Multimedia.\n" \
                       f"Error message: {create_resp['Error']['Message']}\n"
                self.document_action(body, subject)
                self.delete_all()
                return
        self.success = True
        subject = 'התזמון בוצע בהצלחה!'
        body = f'The recording was scheduled Successfully. \n' \
               f'The record will be available in https://huji.cloud.panopto.eu/Panopto/Pages/Sessions/List.aspx#folderID={self.folder_id} \n'
        self.document_action(body, subject)

    def document_action(self, body, subject):
        if config.USER is not None and config.PASSWORD is not None:
            self.send_mail_and_meeting(subject, body)
        with open(config.LOG_FILE, 'w') as f:
            f.write(f'{subject}\n{body}\n\n')
            f.flush()

    def send_mail_and_meeting(self, subject, body):
        email_sender = config.USER

        msg = MIMEMultipart()
        msg['From'] = email_sender
        msg['To'] = ", ".join(config.TO_SEND)
        msg['Subject'] = subject

        msg.attach(MIMEText(f'{body}\n {str(self)}', 'plain'))
        try:
            server = smtplib.SMTP('smtp.office365.com', 587)
            server.ehlo()
            server.starttls()
            server.login(config.USER, config.PASSWORD)
            text = msg.as_string()
            server.sendmail(email_sender, config.TO_SEND, text)
            print('email sent')
            server.quit()
        except socket.error:
            print("SMPT server connection error")
        return True

    def delete_all(self):
        for session_id in self.sessions_id:
            url = config.BASE_URL + "scheduledRecordings/{0}".format(session_id)
            print('Calling DELETE {0}'.format(url))
            read_resp = requests_session.delete(url=url).json()
            print("DELETE returned:\n" + json.dumps(read_resp, indent=2))


def search(course_id, year, semester):
    results = folders.search_folders(rf'{course_id}')
    id = None
    for result in results:
        if year in result['Name']:
            if result['ParentFolder']['Name'] == f'{year} -> {semester}' or \
                    result['ParentFolder']['Name'] == f'{year} -> Semester 1 or 2' or \
                    result['ParentFolder']['Name'] == f'{year} -> Semesters 1 or 2' or \
                    result['ParentFolder']['Name'] == f'{year} -> Non-shnaton':
                return result['Id']
    return id


def update_client():
    global client
    client = gspread.authorize(creds)


# Find a workbook by name and open the first sheet
# Make sure you use the right name here.
def schedule_all():
    sheet = client.open("RecordingsSchedule").sheet1
    data = pd.DataFrame(sheet.get_all_records())
    if data.empty:
        return
    data.rename(columns=config.COLUMN_NAMES, inplace=True)

    recordings = [
        Recording(i + 2, name, description, folder_id, year, semester, date, start_time, end_time, course_id,
                  recorder,
                  is_presentation, is_repeat)
        for
        i, (
            name, description, folder_id, year, semester, date, start_time, end_time, course_id, recorder,
            is_presentation,
            is_repeat)
        in enumerate(
            zip(data['TITLE'], data['DESCRIPTION'], data['FOLDER_ID'], data['YEAR'],
                data['SEMESTER'], data['DATE'],
                data['START_TIME'], data['END_TIME'], data['ID'], data['RECORDER'],
                data['IS_PRESENTATION'],
                data['IS_REPEAT']))]

    for recording in recordings:
        recorder = config.SERVERS[recording.recorder]
        url = config.BASE_URL + "remoteRecorders/search?searchQuery={0}".format(quote(recorder))
        print('Calling GET {0}'.format(url))
        resp = requests_session.get(url=url).json()
        recorder = [rr for rr in resp['Results'] if rr['Name'] == recorder]
        if 'Results' not in resp or len(recorder) != 1:
            print("Recorder not found:\n{0}".format(resp))
            subject = 'לא ניתן לתזמן הקלטה'
            body = f"We have a problem with Scheduling.\n" \
                   f"We can't find the Recorder. Please call Multimedia.\n"
            recording.document_action(subject, body)
            continue
        recorder = recorder[0]
        start_date_str = f'{recording.date} {recording.start_time}'
        end_date_str = f'{recording.date} {recording.end_time}'
        datetime_start = parser.parse(start_date_str, dayfirst=True)
        datetime_end = parser.parse(end_date_str, dayfirst=True)
        start_time = config.ISRAEL.localize(datetime_start)
        end_time = config.ISRAEL.localize(datetime_end)
        m = config.REGEX_FOLDER_ID.search(recording.folder_id)
        if m is None:
            recording.folder_id = search(recording.course_id, recording.year, recording.semester)
        else:
            recording.folder_id = m.group(1)
        if recording.folder_id is None:
            subject = 'לא ניתן לתזמן הקלטה'
            body = f"We have a problem with Scheduling. \n" \
                   f"We can't find the course or the folder. Please call Multimedia"
            recording.document_action(subject, body)
        recording.schedule(recorder, start_time, end_time)
        sheet.delete_rows(recording.row)

    sheet.delete_rows(2, len(recordings) + 1)


def main():
    global folders, client, creds, requests_session
    # use creds to create a client to interact with the Google Drive API
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(config.GOOGLE_JSON, scope)
    client = gspread.authorize(creds)
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    # Use requests module's Session object in this example.
    # ref. https://2.python-requests.org/en/master/user/advanced/#session-objects
    requests_session = requests.Session()

    # Load OAuth2 logic
    oauth2 = PanoptoOAuth2(config.PANOPTO_SERVER_NAME, config.PANOPTO_CLIEND_ID, config.PANOPTO_SECRET, False)
    authorization(requests_session, oauth2)
    # Load Folders API logic
    folders = PanoptoFolders(config.PANOPTO_SERVER_NAME, False, oauth2)

    parse_argument()
    schedule.every().minute.do(schedule_all)
    schedule.every(1).hours.do(update_client)
    schedule.every(1).hours.do(authorization, requests_session, oauth2)
    while True:
        schedule.run_pending()


if __name__ == '__main__':
    main()
