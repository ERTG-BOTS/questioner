from aiogram.fsm.state import StatesGroup, State


class AdminChangeRole(StatesGroup):
    role = State()

class Question(StatesGroup):
    message_id = State()
    question = State()
    clever_link = State()