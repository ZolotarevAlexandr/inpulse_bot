from aiogram.fsm.state import State, StatesGroup


class RootSG(StatesGroup):
    main = State()


class CalendarSetupSG(StatesGroup):
    info = State()
    detail = State()
    input_url = State()
    input_file = State()
    input_start_hour = State()
    input_end_hour = State()


class TaskCreateSG(StatesGroup):
    input_title = State()
    input_deadline = State()
    input_priority = State()
    input_duration = State()


class TaskListSG(StatesGroup):
    list = State()
    detail = State()
    edit_field = State()


class RecommendSG(StatesGroup):
    show = State()

class AdminSG(StatesGroup):
    menu = State()
    input_add = State()
    input_remove = State()
