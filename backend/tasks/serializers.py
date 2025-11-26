# backend/tasks/serializers.py
import json
from datetime import datetime

def validate_tasks_payload(payload):
    """
    Validates incoming request {
        "strategy": "...",
        "tasks": []
    }
    """
    if not isinstance(payload, dict):
        return None, "Payload must be a JSON object"

    if "tasks" not in payload:
        return None, "'tasks' field missing"

    tasks = payload["tasks"]
    if not isinstance(tasks, list):
        return None, "'tasks' must be a list"

    cleaned = []
    errors = []

    for idx, t in enumerate(tasks):
        if not isinstance(t, dict):
            errors.append(f"Task at index {idx} must be an object")
            continue

        title = t.get("title", f"Task {idx}")

        imp = t.get("importance", 5)
        try:
            imp = int(imp)
            if not (1 <= imp <= 10):
                raise ValueError
        except:
            errors.append(f"{title}: invalid importance, defaulting to 5")
            imp = 5

        est = t.get("estimated_hours", 1)
        try:
            est = float(est)
            if est < 0:
                raise ValueError
        except:
            est = 1
            errors.append(f"{title}: invalid estimated hours, defaulting to 1")

        due = t.get("due_date")
        if due:
            try:
                datetime.fromisoformat(due)
            except:
                errors.append(f"{title}: invalid date, setting to None")
                due = None

        deps = t.get("dependencies", [])
        if isinstance(deps, str):
            try:
                deps = json.loads(deps)
            except:
                deps = [deps]

        cleaned.append({
            "id": t.get("id"),
            "title": title,
            "due_date": due,
            "importance": imp,
            "estimated_hours": est,
            "dependencies": deps,
        })

    return cleaned, errors
