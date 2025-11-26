# backend/tasks/scoring.py
from datetime import date, datetime
from math import log
import json
import copy

# -----------------------------
# Utility Helpers
# -----------------------------

def clamp01(x):
    """Clamp value between 0 and 1"""
    return max(0.0, min(1.0, float(x)))


def parse_date(value):
    """Parse ISO date string into Python date object."""
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(value).date()
    except:
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except:
            return None


# -----------------------------
# Dependency Graph Building
# -----------------------------

def build_graph(tasks):
    """
    Build dependency graph from tasks.
    
    Returns:
        dependents: {node -> set(nodes depending on it)}
        dependencies: {node -> set(nodes it depends on)}
    """
    id_map = {}
    for idx, t in enumerate(tasks):
        tid = str(t.get("id", idx))
        id_map[tid] = t

    dependents = {tid: set() for tid in id_map}
    dependencies = {tid: set() for tid in id_map}

    for idx, t in enumerate(tasks):
        tid = str(t.get("id", idx))
        deps = t.get("dependencies", []) or []

        # Handle string-encoded JSON dependencies
        if isinstance(deps, str):
            try:
                deps = json.loads(deps)
                if not isinstance(deps, list):
                    deps = [deps]
            except:
                deps = [deps] if deps else []

        for d in deps:
            d = str(d)
            if d in id_map:
                dependencies[tid].add(d)
                dependents[d].add(tid)

    return dependents, dependencies


def detect_cycles(dependencies: dict):
    """
    Detect cycles using topological sort (Kahn's algorithm).
    
    Returns:
        List of nodes involved in cycles. Empty list if no cycles.
    """
    graph = {n: set() for n in dependencies}
    indegree = {n: 0 for n in dependencies}

    # Build adjacency list and calculate in-degrees
    for node, deps in dependencies.items():
        for d in deps:
            if d in graph:  # Only add edge if dependency exists
                graph[d].add(node)
                indegree[node] += 1

    # Start with nodes that have no dependencies
    queue = [n for n in dependencies if indegree[n] == 0]
    visited = 0

    while queue:
        n = queue.pop(0)
        visited += 1
        for neighbor in graph[n]:
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                queue.append(neighbor)

    # If we didn't visit all nodes, there's a cycle
    if visited == len(dependencies):
        return []  # No cycle
    
    return [n for n, deg in indegree.items() if deg > 0]


def compute_dependency_scores(dependents):
    """
    Calculate how many tasks depend on each task (directly or indirectly).
    Uses DFS with cycle protection.
    
    Args:
        dependents: dict {task_id: set of tasks that depend on this task}
    
    Returns:
        dict {task_id: normalized score between 0 and 1}
    """
    # Early cycle detection to avoid infinite recursion
    visited = set()
    rec_stack = set()

    def has_cycle(node):
        """DFS-based cycle detection"""
        if node in rec_stack:
            return True
        if node in visited:
            return False
        
        visited.add(node)
        rec_stack.add(node)
        
        for neighbor in dependents.get(node, []):
            if has_cycle(neighbor):
                return True
        
        rec_stack.remove(node)
        return False

    # Check for cycles
    for node in dependents.keys():
        if has_cycle(node):
            # If cycle detected, return zero scores for safety
            return {k: 0.0 for k in dependents}
    
    # No cycles: safe to compute dependency scores
    def count_dependents(node, memo=None):
        """Count total tasks that depend on this node (directly + indirectly)"""
        if memo is None:
            memo = {}
        
        if node in memo:
            return memo[node]
        
        total = 0
        for dependent in dependents.get(node, []):
            total += 1 + count_dependents(dependent, memo)
        
        memo[node] = total
        return total

    raw_scores = {n: count_dependents(n) for n in dependents}
    max_val = max(raw_scores.values()) if raw_scores else 0

    if max_val == 0:
        return {n: 0.0 for n in raw_scores}

    # Log normalization for better score distribution
    return {n: (log(1 + raw_scores[n]) / log(1 + max_val)) for n in raw_scores}


# -----------------------------
# Component Scores
# -----------------------------

def importance_score(x):
    """
    Normalize importance (1-10 scale) to 0-1 range.
    """
    try:
        x = int(x)
        x = max(1, min(10, x))
    except:
        x = 5
    return (x - 1) / 9.0


def effort_score(hours):
    """
    Calculate effort score. Lower effort = higher score (quick wins).
    Uses logarithmic scaling to prevent extreme values.
    """
    try:
        hours = float(hours)
    except:
        hours = 1.0

    if hours <= 0:
        return 1.0

    # Logarithmic decay: quick tasks get higher scores
    return clamp01(1 / (1 + log(1 + hours)))


def urgency_score(due_date, today=None, horizon=30):
    """
    Calculate urgency based on due date.
    
    Args:
        due_date: Task due date
        today: Reference date (defaults to today)
        horizon: Days in future beyond which urgency is 0
    
    Returns:
        Score between 0 and 1 (higher = more urgent)
        Past-due tasks get boosted scores (>1.0 capped at ~1.8)
    """
    if today is None:
        today = date.today()

    if due_date is None:
        return 0.0

    diff = (due_date - today).days

    # Past due: exponentially increase urgency
    if diff < 0:
        overdue_boost = min(0.8, abs(diff) / 30)
        return clamp01(1.0 + overdue_boost)

    # Far future: no urgency
    if diff >= horizon:
        return 0.0

    # Linear decay within horizon
    return clamp01(1 - (diff / horizon))


# -----------------------------
# Strategy Weights
# -----------------------------

WEIGHTS = {
    "smart": {
        "w_u": 0.30,  # Urgency
        "w_i": 0.35,  # Importance
        "w_e": 0.20,  # Effort
        "w_d": 0.15   # Dependencies
    },
    "fastest": {
        "w_u": 0.15,
        "w_i": 0.10,
        "w_e": 0.60,  # Heavy emphasis on low effort
        "w_d": 0.15
    },
    "high_impact": {
        "w_u": 0.10,
        "w_i": 0.70,  # Heavy emphasis on importance
        "w_e": 0.10,
        "w_d": 0.10
    },
    "deadline": {
        "w_u": 0.70,  # Heavy emphasis on due dates
        "w_i": 0.15,
        "w_e": 0.10,
        "w_d": 0.05
    },
}


# -----------------------------
# Main Analyze Function
# -----------------------------

def analyze_tasks(tasks, strategy="smart", today=None):
    """
    Analyze and prioritize tasks based on multiple factors.
    
    Args:
        tasks: List of task dictionaries
        strategy: Prioritization strategy ('smart', 'fastest', 'high_impact', 'deadline')
        today: Reference date for urgency calculation
    
    Returns:
        dict with 'tasks' (sorted list) and 'warnings' (list of issues)
    """
    if today is None:
        today = date.today()

    tasks = copy.deepcopy(tasks)
    warnings = []

    # Assign missing IDs
    for idx, t in enumerate(tasks):
        t.setdefault("id", f"task_{idx}")

    # Build dependency graph
    dependents, dependencies = build_graph(tasks)
    cycle_nodes = detect_cycles(dependencies)
    dep_scores = compute_dependency_scores(dependents)

    if cycle_nodes:
        warnings.append(f"⚠️ Circular dependency detected involving: {', '.join(cycle_nodes)}")

    # Get strategy weights
    weight = WEIGHTS.get(strategy, WEIGHTS["smart"])

    results = []

    for t in tasks:
        tid = str(t["id"])
        due = parse_date(t.get("due_date"))
        
        # Calculate component scores
        imp = importance_score(t.get("importance", 5))
        eff = effort_score(t.get("estimated_hours", 1))
        urg = urgency_score(due, today)
        dep = dep_scores.get(tid, 0.0)

        # Calculate weighted final score
        score = (
            weight["w_u"] * urg +
            weight["w_i"] * imp +
            weight["w_e"] * eff +
            weight["w_d"] * dep
        )

        # Apply cycle penalty
        in_cycle = tid in cycle_nodes
        if in_cycle:
            score *= 0.85  # 15% penalty for circular dependencies

        # Priority label based on score
        if score >= 0.75:
            label = "High"
        elif score >= 0.50:
            label = "Medium"
        else:
            label = "Low"

        # Generate human-readable explanation
        explanation = []

        if due is None:
            explanation.append("No due date set")
        else:
            days = (due - today).days
            if days < 0:
                explanation.append(f"⚠️ Past due by {abs(days)} day{'s' if abs(days) != 1 else ''}")
            elif days == 0:
                explanation.append("Due TODAY")
            elif days == 1:
                explanation.append("Due tomorrow")
            else:
                explanation.append(f"Due in {days} days")

        explanation.append(f"Importance: {t.get('importance', 5)}/10")
        explanation.append(f"Effort: {t.get('estimated_hours', 1)}h")
        
        dependent_count = len(dependents.get(tid, set()))
        if dependent_count > 0:
            explanation.append(f"Blocks {dependent_count} task{'s' if dependent_count != 1 else ''}")

        results.append({
            **t,
            "score": round(score, 4),
            "priority": label,
            "components": {
                "urgency": round(urg, 4),
                "importance": round(imp, 4),
                "effort": round(eff, 4),
                "dependency": round(dep, 4),
            },
            "explanation": " • ".join(explanation),
            "in_cycle": in_cycle
        })

    # Sort by score (descending)
    results.sort(key=lambda x: x["score"], reverse=True)

    return {
        "tasks": results,
        "warnings": warnings
    }