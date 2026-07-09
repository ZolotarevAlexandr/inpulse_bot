import operator

from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Button, Cancel, Column, ScrollingGroup, Select, SwitchTo
from aiogram_dialog.widgets.text import Const, Format, Multi

from src.bot.states import TaskCreateSG, TaskListSG
from src.db.database import db
from src.db.repositories.users import UserRepository
from src.modules.tasks.service import TaskService


async def list_tasks_getter(dialog_manager: DialogManager, **kwargs):
    user_id = dialog_manager.event.from_user.id
    async with db.session_factory() as session:
        repo = UserRepository(session)
        user = await repo.get_by_telegram_id(user_id)
        if user:
            task_service = TaskService(session)
            tasks = await task_service.list_pending_tasks(user["id"])
            return {"tasks": tasks, "has_tasks": len(tasks) > 0}
    return {"tasks": [], "has_tasks": False}


async def on_task_selected(call: CallbackQuery, widget, dialog_manager: DialogManager, item_id: str):
    dialog_manager.dialog_data["task_id"] = int(item_id)
    await dialog_manager.switch_to(TaskListSG.detail)


async def task_detail_getter(dialog_manager: DialogManager, **kwargs):
    task_id = dialog_manager.dialog_data.get("task_id")
    user_id = dialog_manager.event.from_user.id
    async with db.session_factory() as session:
        repo = UserRepository(session)
        user = await repo.get_by_telegram_id(user_id)
        if user:
            task_service = TaskService(session)
            task = await task_service.get_task(task_id, user["id"])
            if task:
                deadline_str = task.deadline.strftime("%Y-%m-%d") if task.deadline else "None"
                return {
                    "title": task.title,
                    "priority": task.priority,
                    "duration": task.estimated_minutes,
                    "deadline": deadline_str,
                    "status": task.status
                }
    return {}


import logging

logger = logging.getLogger(__name__)

async def mark_done(call: CallbackQuery, button: Button, dialog_manager: DialogManager):
    task_id = dialog_manager.dialog_data.get("task_id")
    user_id = call.from_user.id
    username = call.from_user.username
    async with db.session_factory() as session:
        repo = UserRepository(session)
        user = await repo.get_by_telegram_id(user_id)
        if user:
            task_service = TaskService(session)
            await task_service.mark_done(task_id, user["id"])
            await session.commit()
            logger.info(f"User {user_id} (@{username}) marked task {task_id} as done")
            logger.info(f"[ANALYTICS] User {user_id} (@{username}) COMPLETED task {task_id}")
    await call.answer("Task marked as done!")
    await dialog_manager.switch_to(TaskListSG.list)


async def delete_task(call: CallbackQuery, button: Button, dialog_manager: DialogManager):
    task_id = dialog_manager.dialog_data.get("task_id")
    user_id = call.from_user.id
    username = call.from_user.username
    async with db.session_factory() as session:
        repo = UserRepository(session)
        user = await repo.get_by_telegram_id(user_id)
        if user:
            task_service = TaskService(session)
            await task_service.delete_task(task_id, user["id"])
            await session.commit()
            logger.info(f"User {user_id} (@{username}) deleted task {task_id}")
    await call.answer("Task deleted.")
    await dialog_manager.switch_to(TaskListSG.list)


async def on_add_task_click(call: CallbackQuery, button: Button, dialog_manager: DialogManager):
    is_premium = dialog_manager.middleware_data.get("is_premium", False)
    if not is_premium:
        user_id = call.from_user.id
        username = call.from_user.username
        async with db.session_factory() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_telegram_id(user_id)
            if user:
                task_service = TaskService(session)
                pending = await task_service.list_pending_tasks(user["id"])
                if len(pending) >= 15:
                    logger.warning(f"User {user_id} (@{username}) hit Free tier limits (active tasks)")
                    await call.answer("📋 Free accounts are limited to 15 active tasks! Upgrade to Premium.", show_alert=True)
                    return
    await dialog_manager.start(TaskCreateSG.input_title)


dialog = Dialog(
    Window(
        Const("📝 <b>My Tasks</b>\n"),
        Format("You don't have any pending tasks.", when=lambda data, w, m: not data.get("has_tasks")),
        ScrollingGroup(
            Select(
                Format("📌 {item.title} | ⭐{item.priority} | ⏱{item.estimated_minutes}m"),
                id="s_tasks",
                item_id_getter=operator.attrgetter("id"),
                items="tasks",
                on_click=on_task_selected,
            ),
            id="tasks_sg",
            width=1,
            height=5,
            when="has_tasks",
        ),
        Button(Const("➕ Add Task"), id="add_task", on_click=on_add_task_click),
        Cancel(Const("⬅️ Back")),
        state=TaskListSG.list,
        getter=list_tasks_getter,
    ),
    Window(
        Multi(
            Const("📌 <b>Task Details</b>\n"),
            Format("<b>Title:</b> {title}"),
            Format("<b>Priority:</b> {priority}"),
            Format("<b>Duration:</b> {duration} minutes"),
            Format("<b>Deadline:</b> {deadline}"),
            Format("<b>Status:</b> {status}"),
        ),
        Column(
            Button(Const("✅ Mark Done"), id="done", on_click=mark_done),
            Button(Const("🗑 Delete"), id="delete", on_click=delete_task),
            SwitchTo(Const("⬅️ Back"), id="back", state=TaskListSG.list),
        ),
        state=TaskListSG.detail,
        getter=task_detail_getter,
    ),
)
