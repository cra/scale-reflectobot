# Scale-reflectobot way overengineered than necessary

Based on aiogram and aigram-dialogs. Helps you track some stuff

Telegram integration is way simpler than the google sheet part. Good luck

Maybe there would be some docs I dunno

## install packages

Use python3.10, aiogram dev-3, or even take a look at the [requirements.txt](./requirements.txt)

```shell
pip install -U --pre aiogram aiogram-dialog
pip install pendulum
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

see [quickstart to setup google stuff for spreadsheets](https://developers.google.com/sheets/api/quickstart/python)

Don't forget to allow writer to write to the sheet, permission-wise.


## Airflow

Airflow dag is handling reminders. It can be used with same bot or another token (I find it's better to use another bot for that), but it reads the same spreadsheet

You need to define the following variables: `dashboard_spreadsheet_id`, `dashboard_schedule_range` and also install [google sheet stuff](https://developers.google.com/sheets/api/quickstart/python), save creds, etc

Creds path is expected to be in FS connection `gsheets_writer_service_acc_keyfile_path`.

You'll need telegram connection, the example dag uses `tg_connection_azaza` specifically to annoy you and prompt to change it to something reasonable.

## env

Check [envrc\_template](./envrc_template)

```shell
export BOT_TOKEN=616111111:AAHHHHHHHHHHHHHHHMooooooooooooooooO
export GSHEET_WRITER_CREDS_PATH=/home/shrimpsizemoose/airflow/credentials/lunar-stone-333333-bebebe555555.json
export DASHBOARD_SHEET_ID=1ZZZZhQXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXVkDE

export SCORE_LOG_RANGE='🤖 scoring'
export SCORE_TIMESTAMP_RANGE='🤖 scoring!F1:G1'
export SCORE_ROW_WRITE_TEMPLATE='🤖 scoring!A{0}:C{0}'

export DECISIONS_WORKSHEET_NAME='Дисижнс'
export DECISIONS_TIMESTAMP_RANGE='🤖 scoring!F2:G2'
export DECISIONS_ROW_WRITE_RANGE='Дисижнс!A1:D1'

export REMINDERS_WORKSHEET_NAME='🤖 напоминания'
export REMINDERS_TIMESTAMP_RANGE='🤖 scoring!F3:G3'
export REMINDERS_ROW_WRITE_RANGE='🤖 напоминания!A1:B1'
```
