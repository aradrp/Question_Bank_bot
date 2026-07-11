"""
states/upload_states.py – FSM state groups for every multi-step admin flow.
"""
from aiogram.fsm.state import State, StatesGroup


class AddSubjectStates(StatesGroup):
    waiting_name = State()


class AddChapterStates(StatesGroup):
    selecting_subject = State()
    waiting_name = State()


class AddTopicStates(StatesGroup):
    selecting_subject = State()
    selecting_chapter = State()
    waiting_name = State()


class UploadQuestionStates(StatesGroup):
    selecting_subject = State()
    selecting_chapter = State()
    selecting_topic = State()
    uploading_file = State()


class DeleteQuestionStates(StatesGroup):
    selecting_subject = State()
    selecting_chapter = State()
    selecting_topic = State()
    selecting_question = State()
    confirming = State()


class ListQuestionsStates(StatesGroup):
    selecting_subject = State()
    selecting_chapter = State()
    selecting_topic = State()


class BuildZipStates(StatesGroup):
    selecting_subject = State()
    selecting_chapter = State()
    selecting_topic = State()
