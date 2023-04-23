import os
import random

import pendulum
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def get_creds(path):
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    return (
        service_account
        .Credentials
        .from_service_account_file(path, scopes=SCOPES)
    )


def gsheet_read_values(creds, spreadsheet_id, range_name):
    try:
        sheet = build('sheets', 'v4', credentials=creds).spreadsheets()
        result = (
            sheet
            .values()
            .get(
                spreadsheetId=spreadsheet_id,
                range=range_name,
            )
            .execute()
        )
        # print(f'cells read: {result.get("values")}.')
    except HttpError as error:
        print(f'An error occurred: {error}')
        return error
    else:
        return result


def gsheet_update_values(creds, spreadsheet_id, range_name, values):
    try:
        service = build('sheets', 'v4', credentials=creds)
        result = (
            service
            .spreadsheets()
            .values()
            .update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body={'values': values},
            )
            .execute()
        )
        print(f"{result.get('updatedCells')} cells updated.")
    except HttpError as error:
        print(f'An error occurred: {error}')
        return error
    else:
        return result


def update_single_bottom_row(
    values,
    entries_range,
    timestamp_range,
    target_range_template,
):
    sheet_id = os.getenv('DASHBOARD_SHEET_ID')
    creds = get_creds(path=os.getenv('GSHEET_WRITER_CREDS_PATH'))

    # find last entry first
    existing = gsheet_read_values(creds, sheet_id, entries_range)
    existing = existing.get('values', [])
    new_row = str(len(existing) + 1)

    # write the update
    target_range = target_range_template.format(new_row)
    gsheet_update_values(creds, sheet_id, target_range, values)

    # post timestamp
    emoji = random.choice(['🤖', '🦄', '🐩', '🔬', '🐉', '🦭', '🐙', '🐈‍⬛', '🎓', '🐊', '🦊'])
    ts = pendulum.now(tz='Europe/Moscow').format('YYYY DD MMMM HH:mm', locale='ru')
    gsheet_update_values(
        creds=creds,
        spreadsheet_id=sheet_id,
        range_name=timestamp_range,
        values=[[f'UPD: {ts}', emoji]],
    )

def update_single_top_row(
    values,
    worksheet_name,
    timestamp_range,
    target_range,
):
    """ insert google sheet row first, """
    sheet_id = os.getenv('DASHBOARD_SHEET_ID')
    creds = get_creds(path=os.getenv('GSHEET_WRITER_CREDS_PATH'))
    service = build('sheets', 'v4', credentials=creds)

    api = service.spreadsheets()
    worksheet_id = None
    for sheet in api.get(spreadsheetId=sheet_id).execute().get('sheets', ''):
        if sheet['properties']['title'] == worksheet_name:
            worksheet_id = sheet['properties']['sheetId']
            break

    assert worksheet_id is not None

    insert_top_row_properties = {
        'range': {'sheetId': worksheet_id, 'dimension': 'ROWS', 'startIndex': 0, 'endIndex': 1},
        'inheritFromBefore': False,
    }

    request_body = {'requests': [{'insertDimension': insert_top_row_properties}]}
    response = (
        api
        .batchUpdate(
            spreadsheetId=sheet_id,
            body=request_body,
        )
        .execute()
    )
    print(response)

    gsheet_update_values(creds, sheet_id, target_range, values)

    # post timestamp
    emoji = random.choice(['👍', '🦄', '🐩', '🐉'])
    ts = pendulum.now(tz='Europe/Moscow').format('DD MMMM HH:mm', locale='ru')
    gsheet_update_values(
        creds=creds,
        spreadsheet_id=sheet_id,
        range_name=timestamp_range,
        values=[[f'UPD: {ts}', emoji]],
    )

def update_score_entry_single_row(values):
    """ values is a tuple of length three, typically: (ds, value, tag) """
    update_single_bottom_row(
        values,
        entries_range=os.getenv('SCORE_LOG_RANGE'),
        timestamp_range=os.getenv('SCORE_TIMESTAMP_RANGE'),
        target_range_template=os.getenv('SCORE_ROW_WRITE_TEMPLATE'),
    )

def update_decisions_entry_single_row(values):
    """ values is a tuple of length four, typically: (year, month, decision, reason) """
    update_single_top_row(
        values,
        worksheet_name=os.getenv('DECISIONS_WORKSHEET_NAME'),
        timestamp_range=os.getenv('DECISIONS_TIMESTAMP_RANGE'),
        target_range=os.getenv('DECISIONS_ROW_WRITE_RANGE'),
    )

def update_reminders_single_row(values):
    """ values is a tuple of length two, : (year, month, decision, reason) """
    update_single_top_row(
        values,
        worksheet_name=os.getenv('REMINDERS_WORKSHEET_NAME'),
        timestamp_range=os.getenv('REMINDERS_TIMESTAMP_RANGE'),
        target_range=os.getenv('REMINDERS_ROW_WRITE_RANGE'),
    )


if __name__ == '__main__':
    ...
    #update_score_entry_single_row([['2048-jan-31 17:15', 5, 'sleep']])
    #update_decisions_entry_single_row(
    #    [['2057', 'may', 'ебать гусей', 'очень круто же']]
    #)
    #update_reminders_single_row(
    #    [['2057-07-01', 'отрефлексировать почему гусей круто ебать']]
    #)
