import datetime
import json
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")


def get_google_sheets_service():
    if not SERVICE_ACCOUNT_JSON:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON not set")
    credentials = service_account.Credentials.from_service_account_info(
        json.loads(SERVICE_ACCOUNT_JSON), scopes=SCOPES
    )
    return build("sheets", "v4", credentials=credentials)


def save_chat_to_sheets(question, answer):
    if not SPREADSHEET_ID:
        return False
    try:
        service = get_google_sheets_service()
        values = [[datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S"), question, answer]]
        body = {"values": values}
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range="Data1!A:C",
            valueInputOption="RAW",
            body=body,
        ).execute()
        return True
    except Exception as e:
        print(f"Error saving to Google Sheets: {e}")
        return False


def save_feedback_to_sheets(answer, feedback):
    if not SPREADSHEET_ID:
        return False
    try:
        service = get_google_sheets_service()
        values = [[datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S"), answer, feedback]]
        body = {"values": values}
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range="feedback!A:C",
            valueInputOption="RAW",
            body=body,
        ).execute()
        return True
    except Exception as e:
        print(f"Error saving feedback to Google Sheets: {e}")
        return False
