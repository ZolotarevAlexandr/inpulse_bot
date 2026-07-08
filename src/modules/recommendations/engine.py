import datetime
import logging

from openai import AsyncOpenAI

from src.config import settings
from src.modules.calendar.models import FreeWindow
from src.modules.tasks.models import Task


def score_task(task: Task, window: FreeWindow, now: datetime.datetime) -> float:
    # 1. Hard filter: skip tasks that don't fit in the window
    if task.estimated_minutes > window.duration_minutes:
        return -1.0

    # 2. Deadline urgency (0–1, higher = more urgent)
    if task.deadline:
        hours_until_deadline = (task.deadline - now).total_seconds() / 3600
        # If deadline is passed, urgency is 1.0. If it's more than a week, 0.0.
        urgency = max(0.0, min(1.0, 1.0 - hours_until_deadline / 168.0))
    else:
        urgency = 0.1  # low urgency if no deadline

    # 3. Priority factor (0.2–1.0)
    priority_factor = task.priority / 5.0

    # 4. Time fit bonus (prefer tasks that fill the window well)
    fit = task.estimated_minutes / window.duration_minutes  # 0–1
    fit_bonus = 1.0 - abs(fit - 0.8)  # Optimal is ~80% of window

    # 5. Final score
    score = urgency * 0.5 + priority_factor * 0.3 + fit_bonus * 0.2
    return score


async def generate_explanation(task: Task, window: FreeWindow) -> str:
    window_until = window.end.strftime("%H:%M")
    
    reasons = []
    if task.deadline:
        reasons.append("upcoming deadline")
    if task.priority >= 4:
        reasons.append("high priority")
    reasons.append("fits well in this window")
    
    reason_str = ", ".join(reasons)
    
    if window.current_event_name:
        window_info_str = f"📍 You're scheduled for <b>{window.current_event_name}</b>, but you have {window.duration_minutes} min until <b>{window.next_event_name}</b> at {window_until}"
        window_info_llm = f"They are currently scheduled for an event called '{window.current_event_name}', but they actually have {window.duration_minutes} mins of free time right now until their next event ('{window.next_event_name}')."
    else:
        window_info_str = f"📍 Free window: {window.duration_minutes} min (until {window_until} before <b>{window.next_event_name}</b>)"
        window_info_llm = f"They have {window.duration_minutes} mins of free time right now until their next event ('{window.next_event_name}')."

    base_text = (
        f"{window_info_str}\n"
        f"🎯 <b>Recommended:</b> {task.title}\n"
        f"⏱ ~{task.estimated_minutes} min | ⭐ Priority: {task.priority}\n\n"
        f"<b>Why:</b> {reason_str.capitalize()}."
    )

    if settings.llm:
        try:
            client = AsyncOpenAI(
                api_key=settings.llm.api_key.get_secret_value(),
                base_url=settings.llm.base_url
            )
            prompt = (
                f"You are a friendly and encouraging assistant for students.\n"
                f"The student needs to do the following task right now: \"{task.title}\"\n\n"
                f"Context about the task and their schedule:\n"
                f"- Estimated time to complete: {task.estimated_minutes} mins\n"
                f"- Priority: {task.priority} (1-5)\n"
                f"- Schedule context: {window_info_llm}\n"
                f"- Why now is a good time: {reason_str}\n\n"
                f"Write a very short, friendly, and motivating message (2-3 sentences max) "
                f"encouraging them to start the task \"{task.title}\" right now. "
                f"Make it sound natural and supportive. Do not act like a robot and do not mix up the task with their schedule events."
            )
            
            response = await client.chat.completions.create(
                model=settings.llm.model,
                messages=[{"role": "user", "content": prompt}]
            )
            llm_text = response.choices[0].message.content.strip()
            if not llm_text:
                logging.warning("LLM returned empty response. Falling back to base text.")
                return base_text
            
            return (
                f"{window_info_str}\n"
                f"🎯 <b>{task.title}</b>\n"
                f"⏱ ~{task.estimated_minutes} min | ⭐ Priority: {task.priority}\n\n"
                f"🤖 {llm_text}"
            )
        except Exception as e:
            logging.error(f"LLM generation failed: {e}")
            return base_text

    return base_text
