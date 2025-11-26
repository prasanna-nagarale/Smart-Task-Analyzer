# backend/tasks/views.py
import json
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt

from .scoring import analyze_tasks
from .serializers import validate_tasks_payload


@csrf_exempt
def analyze_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Use POST"}, status=400)

    try:
        data = json.loads(request.body.decode())
    except:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    tasks, errors = validate_tasks_payload(data)
    if tasks is None:
        return JsonResponse({"error": errors}, status=400)

    strategy = data.get("strategy", "smart")

    result = analyze_tasks(tasks, strategy=strategy)

    return JsonResponse({
        "tasks": result["tasks"],
        "warnings": result["warnings"],
        "validation_warnings": errors
    })
    

@csrf_exempt
def suggest_view(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode())
        except:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        tasks, errors = validate_tasks_payload(data)
        if tasks is None:
            return JsonResponse({"error": errors}, status=400)

        strategy = data.get("strategy", "smart")
        result = analyze_tasks(tasks, strategy=strategy)

        return JsonResponse({
            "suggestions": result["tasks"][:3],
            "warnings": result["warnings"],
            "validation_warnings": errors
        })

    return JsonResponse({"error": "Use POST"}, status=400)
