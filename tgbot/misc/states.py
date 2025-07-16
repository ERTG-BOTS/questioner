from aiogram.fsm.state import State, StatesGroup


class AdminChangeRole(StatesGroup):
    role = State()


class Question(StatesGroup):
    message_id = State()
    question = State()
    clever_link = State()