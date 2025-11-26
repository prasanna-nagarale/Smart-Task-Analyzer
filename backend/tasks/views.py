# backend/tasks/views.py
import json
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from .scoring import analyze_tasks
from .serializers import validate_tasks_list

@csrf_exempt
def analyze_view(request):
    """
    POST /api/tasks/analyze/
    Body JSON: { "strategy": "smart", "tasks": [ {...}, ... ] }
    """
    if request.method != "POST":
        return HttpResponseBadRequest(json.dumps({"error": "Use POST"}), content_type="application/json")

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest(json.dumps({"error": "Invalid JSON"}), content_type="application/json")

    strategy = (data.get("strategy") or "smart").lower()
    tasks, errors = validate_tasks_list(data)
    if tasks is None:
        return HttpResponseBadRequest(json.dumps({"error": errors}), content_type="application/json")

    result = analyze_tasks(tasks, strategy=strategy)
    response = {"tasks": result["tasks"], "warnings": result["warnings"], "validation_warnings": errors}
    return JsonResponse(response, safe=True)

@csrf_exempt
def suggest_view(request):
    """
    GET /api/tasks/suggest/?strategy=smart&tasks=<urlencoded-json>
    Also supports POST with same body as analyze_view but returns only top 3 with explanations.
    """
    if request.method == "GET":
        tasks_param = request.GET.get("tasks")
        if not tasks_param:
            return HttpResponseBadRequest(json.dumps({"error": "Provide 'tasks' query param as JSON string or use POST"}), content_type="application/json")
        try:
            payload = json.loads(tasks_param)
        except Exception:
            return HttpResponseBadRequest(json.dumps({"error": "Invalid JSON in 'tasks' param"}), content_type="application/json")
        strategy = (request.GET.get("strategy") or payload.get("strategy") or "smart").lower()
        tasks, errors = validate_tasks_list(payload if isinstance(payload, dict) and payload.get("tasks") else {"tasks": payload})
        if tasks is None:
            return HttpResponseBadRequest(json.dumps({"error": errors}), content_type="application/json")
        res = analyze_tasks(tasks, strategy=strategy)
    else:
        # POST
        try:
            data = json.loads(request.body.decode("utf-8"))
        except Exception:
            return HttpResponseBadRequest(json.dumps({"error": "Invalid JSON"}), content_type="application/json")
        strategy = (data.get("strategy") or "smart").lower()
        tasks, errors = validate_tasks_list(data)
        if tasks is None:
            return HttpResponseBadRequest(json.dumps({"error": errors}), content_type="application/json")
        res = analyze_tasks(tasks, strategy=strategy)

    top3 = res["tasks"][:3]
    return JsonResponse({"suggestions": top3, "warnings": res["warnings"], "validation_warnings": errors}, safe=True)
