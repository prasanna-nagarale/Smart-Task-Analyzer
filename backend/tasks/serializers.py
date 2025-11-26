# backend/tasks/serializers.py
import json
from datetime import datetime

def validate_tasks_list(data):
    """
    Expect: {"strategy": "smart", "tasks": [ {...}, ... ] }
    Returns: (tasks_list, errors)
    """
    if not isinstance(data, dict):
        return None, "Expected JSON object with 'tasks' key."

    tasks = data.get("tasks")
    if tasks is None:
        return None, "'tasks' key missing."
    if not isinstance(tasks, list):
        return None, "'tasks' must be a list."

    validated = []
    errors = []
    for idx, t in enumerate(tasks):
        if not isinstance(t, dict):
            errors.append(f"task at index {idx} is not an object")
            continue
        # simple field fixes
        title = t.get("title") or t.get("name") or f"Task {idx}"
        importance = t.get("importance", 5)
        try:
            importance = int(importance)
            if importance < 1 or importance > 10:
                raise ValueError()
        except Exception:
            importance = 5
            errors.append(f"task {title}: invalid importance; defaulting to 5")

        est = t.get("estimated_hours", 1)
        try:
            est = float(est)
            if est < 0:
                raise ValueError()
        except Exception:
            est = 1.0
            errors.append(f"task {title}: invalid estimated_hours; defaulting to 1")

        due = t.get("due_date")
        if due:
            try:
                # accept ISO date
                datetime.fromisoformat(due)
            except Exception:
                # try yyyy-mm-dd
                try:
                    datetime.strptime(due, "%Y-%m-%d")
                except Exception:
                    errors.append(f"task {title}: invalid due_date format; setting to None")
                    due = None

        deps = t.get("dependencies", [])
        if deps is None:
            deps = []
        # ensure list
        if not isinstance(deps, list):
            deps = [deps]

        validated.append({
            "id": t.get("id"),
            "title": title,
            "due_date": due,
            "estimated_hours": est,
            "importance": importance,
            "dependencies": deps,
        })

    return validated, errors
