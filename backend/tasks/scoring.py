# backend/tasks/scoring.py
from datetime import date, datetime, timedelta
from math import log
from typing import List, Dict, Tuple, Set
import copy
import json

# --- Helper functions -------------------------------------------------------

def parse_date(datestr):
    if not datestr:
        return None
    if isinstance(datestr, date):
        return datestr
    try:
        return datetime.fromisoformat(datestr).date()
    except Exception:
        try:
            return datetime.strptime(datestr, "%Y-%m-%d").date()
        except Exception:
            return None

def clamp01(x):
    return max(0.0, min(1.0, float(x)))

# --- Dependency utilities ---------------------------------------------------

def build_graph(tasks: List[dict]) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
    """
    Build graph where edge A->B means A is depended-on by B (i.e., B depends on A).
    Return:
      - dependents: node_id -> set(nodes that depend on node_id)
      - dependencies: node_id -> set(nodes it depends on)
    """
    id_map = {}
    for idx, t in enumerate(tasks):
        tid = str(t.get("id", idx))
        id_map[tid] = t

    dependencies = {tid: set() for tid in id_map}
    dependents = {tid: set() for tid in id_map}

    for idx, t in enumerate(tasks):
        tid = str(t.get("id", idx))
        raw_deps = t.get("dependencies", []) or []
        if isinstance(raw_deps, str):
            try:
                raw_deps = json.loads(raw_deps)
            except Exception:
                raw_deps = [raw_deps]
        for dep in raw_deps:
            depid = str(dep)
            if depid not in id_map:
                # ignore missing dependency (caller will receive a warning)
                continue
            dependencies[tid].add(depid)
            dependents[depid].add(tid)
    return dependents, dependencies

def detect_cycles_kahn(dependencies: Dict[str, Set[str]]) -> List[str]:
    """
    Kahn's algorithm to detect cycles.
    dependencies: node -> set(nodes it depends on)
    returns list of node ids that are part of cycle (empty list if none)
    """
    # compute in-degrees
    nodes = set(dependencies.keys())
    in_deg = {n: 0 for n in nodes}
    graph = {n: set() for n in nodes}
    for n, deps in dependencies.items():
        for d in deps:
            graph[d].add(n)  # d -> n
            in_deg[n] += 1

    queue = [n for n, deg in in_deg.items() if deg == 0]
    visited = 0
    q_idx = 0
    while q_idx < len(queue):
        n = queue[q_idx]; q_idx += 1
        visited += 1
        for m in graph[n]:
            in_deg[m] -= 1
            if in_deg[m] == 0:
                queue.append(m)

    if visited == len(nodes):
        return []  # no cycles

    # nodes with in_deg > 0 are part of cycles
    cycle_nodes = [n for n, deg in in_deg.items() if deg > 0]
    return cycle_nodes

def compute_reachability_count(dependents: Dict[str, Set[str]]) -> Dict[str, float]:
    """
    For each node, compute how many tasks (directly or indirectly) it blocks.
    Use DFS + memoization. Return raw counts.
    """
    memo = {}

    def dfs(n, seen):
        if n in memo:
            return memo[n]
        total = 0
        for d in dependents.get(n, []):
            if d in seen:
                continue
            seen.add(d)
            total += 1
            total += dfs(d, seen)
        memo[n] = total
        return total

    counts = {}
    for n in dependents:
        counts[n] = dfs(n, set())
    return counts

# --- Scoring subcomponents --------------------------------------------------

def importance_score(importance):
    # Map 1..10 -> 0..1
    try:
        i = int(importance)
    except Exception:
        i = 5
    i = max(1, min(10, i))
    return (i - 1) / 9.0

def effort_score(hours, max_effort=40.0):
    # Lower hours -> higher score (quick wins get >)
    try:
        h = float(hours)
    except Exception:
        h = 1.0
    if h <= 0:
        return 1.0
    # Use inverse with log scaling to avoid huge drop for big numbers
    v = 1.0 / (1.0 + log(1.0 + h))
    # normalize roughly to range (0,1], but clamp
    return clamp01(v)

def urgency_score(due_date: date, today: date = None, horizon_days=30):
    if today is None:
        today = date.today()
    if due_date is None:
        # no due date = low urgency
        return 0.0
    delta = (due_date - today).days
    if delta < 0:
        # past-due -> urgency boost (cap added)
        boost = min(0.8, abs(delta) / 30.0)  # max boost 0.8
        return clamp01(1.0 + boost)
    # within horizon -> linear decay
    if delta >= horizon_days:
        return 0.0
    return clamp01(1.0 - (delta / horizon_days))

def dependency_score(raw_counts: Dict[str, float]):
    # raw_counts is integer counts, normalize using log scale
    if not raw_counts:
        return {}
    max_count = max(raw_counts.values())
    scores = {}
    for k, c in raw_counts.items():
        if c <= 0:
            scores[k] = 0.0
        else:
            # use log to dampen
            scores[k] = clamp01(log(1 + c) / (log(1 + max_count) if max_count > 0 else 1))
    return scores

# --- Strategy weights ------------------------------------------------------

DEFAULT_WEIGHTS = {
    "smart": {"w_u": 0.30, "w_i": 0.35, "w_e": 0.20, "w_d": 0.15},
    "fastest": {"w_u": 0.15, "w_i": 0.10, "w_e": 0.60, "w_d": 0.15},
    "high_impact": {"w_u": 0.15, "w_i": 0.70, "w_e": 0.05, "w_d": 0.10},
    "deadline": {"w_u": 0.70, "w_i": 0.15, "w_e": 0.10, "w_d": 0.05},
}

# --- Main analyze function -------------------------------------------------

def analyze_tasks(tasks: List[dict], strategy: str = "smart", today: date = None) -> dict:
    """
    Input: tasks list of dicts (each may have id/title/due_date/estimated_hours/importance/dependencies)
    Output: dict with:
        - tasks: list of tasks enriched with score (0..1), priority label, explanation, component scores
        - warnings: list of warnings (missing dependencies, cycles, invalid fields)
    """
    if today is None:
        today = date.today()
    # shallow copy to avoid mutation
    tasks_in = copy.deepcopy(tasks or [])
    # assign ids for tasks without id
    for idx, t in enumerate(tasks_in):
        if "id" not in t:
            t["id"] = f"__auto_{idx}"

    # Build graphs
    dependents, dependencies = build_graph(tasks_in)
    cycle_nodes = detect_cycles_kahn(dependencies)
    reach_counts = compute_reachability_count(dependents)
    dep_scores = dependency_score(reach_counts)

    warnings = []
    if cycle_nodes:
        warnings.append(f"circular_dependency_nodes: {cycle_nodes}")

    # collect missing deps
    ids_present = {str(t["id"]) for t in tasks_in}
    for t in tasks_in:
        raw_deps = t.get("dependencies", []) or []
        if isinstance(raw_deps, str):
            try:
                raw_deps = json.loads(raw_deps)
            except Exception:
                raw_deps = [raw_deps]
        for dep in raw_deps:
            if str(dep) not in ids_present:
                warnings.append(f"task {t.get('id')} dependency {dep} missing")

    weights = DEFAULT_WEIGHTS.get(strategy, DEFAULT_WEIGHTS["smart"])
    w_u, w_i, w_e, w_d = weights["w_u"], weights["w_i"], weights["w_e"], weights["w_d"]

    results = []
    for t in tasks_in:
        tid = str(t["id"])
        title = t.get("title", f"Task {tid}")
        due = parse_date(t.get("due_date"))
        imp = t.get("importance", 5)
        est = t.get("estimated_hours", 1)

        U = urgency_score(due, today)
        I = importance_score(imp)
        E = effort_score(est)
        D = dep_scores.get(tid, 0.0)

        score_raw = w_u * U + w_i * I + w_e * E + w_d * D

        # if in cycle, add warning and slightly deprioritize (multiplier)
        in_cycle = tid in cycle_nodes
        if in_cycle:
            warnings.append(f"task {tid} is in a circular dependency")
            score_raw *= 0.85  # slight penalty to force human attention to resolve

        score = clamp01(score_raw)

        # priority label
        if score >= 0.75:
            label = "High"
        elif score >= 0.5:
            label = "Medium"
        else:
            label = "Low"

        # explanation
        explanation = []
        # urgency wording
        if due is None:
            explanation.append("No due date (low urgency)")
        else:
            days = (due - today).days
            if days < 0:
                explanation.append(f"Past due by {abs(days)} days (urgent boost)")
            else:
                explanation.append(f"Due in {days} day(s)")

        explanation.append(f"Importance {int(imp)}/10")
        explanation.append(f"Effort ≈ {est} hour(s)")
        if reach_counts.get(tid, 0) > 0:
            explanation.append(f"Blocks {int(reach_counts.get(tid,0))} task(s)")

        explanation_text = "; ".join(explanation)

        results.append({
            "id": tid,
            "title": title,
            "due_date": due.isoformat() if due else None,
            "estimated_hours": est,
            "importance": int(imp) if isinstance(imp, (int, float)) else imp,
            "dependencies": list(dependencies.get(tid, [])) if dependencies.get(tid) else [],
            "score": round(score, 4),
            "priority": label,
            "components": {"urgency": round(U, 4), "importance": round(I, 4), "effort": round(E, 4), "dependency": round(D, 4)},
            "explanation": explanation_text,
            "in_cycle": in_cycle
        })

    # sort by score desc
    results.sort(key=lambda x: x["score"], reverse=True)

    return {"tasks": results, "warnings": list(dict.fromkeys(warnings))}  # remove dupes
