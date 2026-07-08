from .calendar_setup import dialog as calendar_setup_dialog
from .recommend import dialog as recommend_dialog
from .root import dialog as root_dialog
from .task_create import dialog as task_create_dialog
from .task_list import dialog as task_list_dialog
from .admin import dialog as admin_dialog

__all__ = [
    "root_dialog",
    "calendar_setup_dialog",
    "task_create_dialog",
    "task_list_dialog",
    "recommend_dialog",
    "admin_dialog",
]
