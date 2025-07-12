from aiogram.fsm.state import StatesGroup, State


class AdminChangeRole(StatesGroup):
    role = State()

