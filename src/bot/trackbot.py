import asyncio
import calendar
import logging
import os
from datetime import datetime as dt
from typing import Any

import pendulum
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, ContentType, Message
from aiogram_dialog import (
    ChatEvent,
    Dialog,
    DialogManager,
    StartMode,
    Window,
    setup_dialogs,
)
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import (
    Button,
    NumberedPager,
    Select,
    StubScroll,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format
from gsheet import (
    update_decisions_entry_single_row,
    update_reminders_single_row,
    update_score_entry_single_row,
)

SCALE = {
   '1': 'Feeling active, vital, alert, or wide awake',
   '2': 'Functioning at high levels, but not at peak; able to concentrate',
   '3': 'Awake, but relaxed, responsive but not fully alert',
   '4': 'Somewhat foggy, let down',
   '5': 'Foggy: losing interest in remaining awake; slowed down',
   '6': 'Sleepy, woozy, fighting sleep; prefer to lie down',
   '7': 'No longer fighting sleep, sleep onset soon, having dream-like thoughts',
   'X': 'Asleep',
}
scale_values = list(SCALE.keys())  # ironsk
scale_legend = list(SCALE.values())

DECISION_DELAY_WEEKS = {
    4: 'через месяц',
    12: 'через 12 недель',
    26: 'через полгода',
}
DECISION_DELAY_OPTIONS = list(DECISION_DELAY_WEEKS.values())
DECISION_OPTION2WEEKNUMBER = {v: k for k, v in DECISION_DELAY_WEEKS.items()}
DECISION_DELAY_WEEKS[-1] = 'через пока не договорились сколько'


class MainDialog(StatesGroup):
    MAIN = State()
    DECISION_INPUT = State()
    DECISION_REASON_INPUT = State()
    DECISION_SUBMIT = State()
    SCORE = State()


async def paging_getter(dialog_manager: DialogManager, **_kwargs):
    current_page = await dialog_manager.find('stub_scroll').get_page()
    return {
        'pages': 8,
        'current_score': current_page + 1,
        'score': scale_values[current_page],
        'legend': scale_legend[current_page],
    }


async def submit_score(c: CallbackQuery, button: Button, dialog_manager: DialogManager):
    current_page = await dialog_manager.find('stub_scroll').get_page()
    score = scale_values[current_page]
    legend = scale_legend[current_page]
    message = f'Submitting score of {score}\n<i>{legend}</i>'
    await dialog_manager.done()

    await c.message.answer(message)

    ds = dt.now().strftime('%Y-%b-%d %H:%M').lower()
    update_score_entry_single_row(values=[[ds, score, 'sleep']])


async def decision_delay_getter(dialog_manager: DialogManager, **kwargs):
    decision = dialog_manager.dialog_data.get('decision')
    delay = dialog_manager.dialog_data.get('delay', -1)
    return {
        'decision': decision,
        'delay': DECISION_DELAY_WEEKS.get(int(delay)),
    }

async def decision_handler(
    message: Message,
    message_input: MessageInput,
    manager: DialogManager,
):
    manager.dialog_data['decision'] = message.text
    await manager.next()

async def decision_reason_handler(
    message: Message,
    message_input: MessageInput,
    manager: DialogManager,
):
    manager.dialog_data['reason'] = message.text
    await manager.next()


async def on_reminder_delay_changed(
    callback: ChatEvent,
    select: Any,
    manager: DialogManager,
    item_id: str,
):
    manager.dialog_data['delay'] = item_id


async def submit_decision(c: CallbackQuery, button: Button, dialog_manager: DialogManager):
    decision = dialog_manager.dialog_data.get('decision')
    reason = dialog_manager.dialog_data.get('reason')
    delay = dialog_manager.dialog_data.get('delay')
    if delay is None:
        await c.answer(
            'надо определиться когда напомнить',
            show_alert=True,
        )
        return

    delay_weeks = int(delay)

    idag = pendulum.today()
    row = [
        idag.year,
        calendar.month_abbr[idag.month].lower(),
        decision,
        reason,
    ]
    update_decisions_entry_single_row(values=[row])

    remind_when = (idag + pendulum.duration(weeks=delay_weeks)).strftime('%Y-%m-%d')
    remind_text = f'🤖 Отрефлексировать решение "{decision}"'
    update_reminders_single_row([[remind_when, remind_text]])

    #delay_human = DECISION_DELAY_WEEKS[delay_weeks]
    #await c.message.answer(f'Записываю решение\n  <i>{decision=}</i>\n\nнапомню <b>{delay_human=}</b>')
    await dialog_manager.done()


async def entrypoint(message: Message, dialog_manager: DialogManager):
    # it is important to reset stack because user wants to restart everything
    await dialog_manager.start(MainDialog.MAIN, mode=StartMode.RESET_STACK)



MAIN_MENU_BTN = SwitchTo(Const('Main menu'), id='main', state=MainDialog.MAIN)
dialog = Dialog(
    Window(
        Const('Ну давай залогаем что-то'),
        SwitchTo(Const('Бодрость/Сонливость'), id='stub', state=MainDialog.SCORE),
        SwitchTo(Const('Какое-то решение'), id='decision', state=MainDialog.DECISION_INPUT),
        state=MainDialog.MAIN,
    ),
    Window(
        Const('Sleepiness scale score submission\n'),
        Format('You are at score {current_score} out of {pages}'),
        Format('Score {score}'),
        Format('Verbose: {legend}'),
        StubScroll(id='stub_scroll', pages='pages'),
        NumberedPager(scroll='stub_scroll'),
        Button(Const('Submit'), id='submit_score', on_click=submit_score),
        MAIN_MENU_BTN,
        state=MainDialog.SCORE,
        getter=paging_getter,
    ),
    Window(
        Const('Что за решение?\n'),
        MessageInput(decision_handler, content_types=[ContentType.TEXT]),
        state=MainDialog.DECISION_INPUT,
    ),
    Window(
        Const('Почему принял это решение?\n'),
        MessageInput(decision_reason_handler, content_types=[ContentType.TEXT]),
        state=MainDialog.DECISION_REASON_INPUT,
    ),
    Window(
        Format('Записываем решение\n<i>{decision}</i>'),
        Format('Напомню отрефлексировать <b>{delay}</b>'),
        Select(
            Format('{item}'),
            items=DECISION_DELAY_OPTIONS,
            item_id_getter=lambda x: DECISION_OPTION2WEEKNUMBER.get(x),
            id='reminder',
            on_click=on_reminder_delay_changed,
        ),
        Button(Const('Submit'), id='submit_decision', on_click=submit_decision),
        MAIN_MENU_BTN,
        state=MainDialog.DECISION_SUBMIT,
        getter=decision_delay_getter,
    ),
)


async def main():
    # real main
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=os.getenv('BOT_TOKEN'), parse_mode='HTML')

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.message.register(entrypoint, Command('track'))
    dp.include_router(dialog)
    setup_dialogs(dp)

    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
