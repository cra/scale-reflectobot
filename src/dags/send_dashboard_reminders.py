import operator
import pendulum

from airflow.hooks.filesystem import FSHook
from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import get_current_context
from airflow.providers.telegram.operators.telegram import TelegramOperator
from airflow.utils.trigger_rule import TriggerRule
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


SCHED = '7 7 * * *'
START = pendulum.datetime(2021, 7, 25)


def get_creds(path):
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    return (
        service_account
        .Credentials
        .from_service_account_file(path, scopes=SCOPES)
    )


def gsheet_read_values(creds, spreadsheet_id, range_name):
    try:
        service = build('sheets', 'v4', credentials=creds)
        result = (
            service
            .spreadsheets()
            .values()
            .get(
                spreadsheetId=spreadsheet_id,
                range=range_name,
            )
            .execute()
        )
        print(f'cells read: {result.get("values")}.')
    except HttpError as error:
        print(f'An error occurred: {error}')
        return error
    else:
        return result


@dag(schedule=SCHED, start_date=START, catchup=False)
def send_dashboard_reminders():
    start = EmptyOperator(task_id='start')
    do_nothing = EmptyOperator(task_id='do_nothing')

    @task()
    def read_schedule_from_spreadsheet():
        hook = FSHook('gsheets_writer_service_acc_keyfile_path')
        spreadsheet_id = Variable.get('dashboard_spreadsheet_id')
        range_name_main_chart = Variable.get('dashboard_schedule_range')
        creds = get_creds(path=hook.get_path())

        attempt = gsheet_read_values(
            creds=creds,
            spreadsheet_id=spreadsheet_id,
            range_name=range_name_main_chart,
        )

        return attempt['values']

    @task.branch(task_id='decide_what_to_send')
    def branch_func(values):
        ctx = get_current_context()

        idag = ctx['data_interval_end'].date()
        print(f"Filtering events for today's date: {idag=}")
        reminders = '\n'.join(
            f'<b>{ds}</b>: {reminder}\n'
            for ds, reminder in filter(
                lambda ds_msg: pendulum.parse(ds_msg[0]).date() == idag,
                map(operator.itemgetter(0, 1), values)
            )
        )
        if reminders:
            message = f'Напоминаю\n{reminders}'
            ctx['ti'].xcom_push('reminder_full_message', message)
            return 'send_reminder_dm'
        
        return 'do_nothing'

    send_reminder_dm = TelegramOperator(
        task_id='send_reminder_dm',
        telegram_conn_id='tg_connection_azaza',
        telegram_kwargs={'parse_mode': 'HTML'},
        text="{{ ti.xcom_pull(key='reminder_full_message') }}",
        trigger_rule=TriggerRule.ONE_SUCCESS,
    )

    read_schedule = read_schedule_from_spreadsheet()
    start >> read_schedule
    branch_func(read_schedule) >> [do_nothing, send_reminder_dm]

my_dag = send_dashboard_reminders()

if __name__ == '__main__':
    my_dag.test()
