# backend/tasks/tests.py
from django.test import SimpleTestCase
from .scoring import analyze_tasks
from datetime import date, timedelta

class ScoringUnitTests(SimpleTestCase):
    def test_ordering_basic_smart(self):
        """Smart balance: urgent / important tasks should be near top."""
        today = date.today()
        tasks = [
            {"id":"t1","title":"Urgent Bug","due_date":(today + timedelta(days=1)).isoformat(),"estimated_hours":1,"importance":9},
            {"id":"t2","title":"Fix bug","due_date":(today + timedelta(days=5)).isoformat(),"estimated_hours":6,"importance":5},
            {"id":"t3","title":"Normal Task","due_date":(today + timedelta(days=14)).isoformat(),"estimated_hours":5,"importance":2},
        ]
        res = analyze_tasks(tasks, strategy="smart", today=today)
        ordered = [t["id"] for t in res["tasks"]]
        self.assertEqual(ordered[0], "t1")
        self.assertIn(ordered[1], ("t2", "t3"))

    def test_past_due_boost_deadline_strategy(self):
        """Past-due tasks should outrank future tasks under deadline-first strategy."""
        today = date.today()
        tasks = [
            {"id":"a","title":"Past","due_date":(today - timedelta(days=2)).isoformat(),"estimated_hours":5,"importance":4},
            {"id":"b","title":"Future High","due_date":(today + timedelta(days=10)).isoformat(),"estimated_hours":5,"importance":9}
        ]
        res = analyze_tasks(tasks, strategy="deadline", today=today)
        self.assertEqual(res["tasks"][0]["id"], "a")

    def test_cycle_detection_flagged(self):
        """Circular dependencies should be detected and flagged."""
        today = date.today()
        tasks = [
            {"id":"x","title":"X","due_date":(today + timedelta(days=5)).isoformat(),"estimated_hours":2,"importance":5,"dependencies":["y"]},
            {"id":"y","title":"Y","due_date":(today + timedelta(days=6)).isoformat(),"estimated_hours":1,"importance":4,"dependencies":["x"]},
        ]
        res = analyze_tasks(tasks, strategy="smart", today=today)
        in_cycle = any(t.get("in_cycle") for t in res["tasks"])
        self.assertTrue(in_cycle)
        self.assertTrue(any("circular" in w.lower() for w in res["warnings"]))
