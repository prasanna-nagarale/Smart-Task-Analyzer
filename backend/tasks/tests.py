# backend/tasks/tests.py
from django.test import SimpleTestCase
from .scoring import analyze_tasks
from datetime import date, timedelta

class ScoringTests(SimpleTestCase):

    def test_basic_ordering_smart(self):
        today = date.today()
        tasks = [
            {"id":"t1","title":"Urgent small","due_date":(today + timedelta(days=1)).isoformat(),"estimated_hours":1,"importance":5},
            {"id":"t2","title":"Later high impact","due_date":(today + timedelta(days=20)).isoformat(),"estimated_hours":2,"importance":9},
            {"id":"t3","title":"Far low","due_date":(today + timedelta(days=60)).isoformat(),"estimated_hours":4,"importance":3}
        ]
        res = analyze_tasks(tasks, strategy="smart", today=today)
        ids = [t["id"] for t in res["tasks"]]
        # Expect urgent small or high impact first; ensure top is one of t1 or t2
        self.assertIn(ids[0], ("t1","t2"))

    def test_past_due_boost(self):
        today = date.today()
        tasks = [
            {"id":"a","title":"Past","due_date":(today - timedelta(days=2)).isoformat(),"estimated_hours":5,"importance":4},
            {"id":"b","title":"Future high","due_date":(today + timedelta(days=10)).isoformat(),"estimated_hours":5,"importance":9}
        ]
        res = analyze_tasks(tasks, strategy="deadline", today=today)
        # Past due should be top in deadline mode
        self.assertEqual(res["tasks"][0]["id"], "a")

    def test_cycle_detection_flags(self):
        today = date.today()
        tasks = [
            {"id":"x","title":"X","due_date":(today + timedelta(days=5)).isoformat(),"estimated_hours":2,"importance":5,"dependencies":["y"]},
            {"id":"y","title":"Y","due_date":(today + timedelta(days=6)).isoformat(),"estimated_hours":1,"importance":4,"dependencies":["x"]},
        ]
        res = analyze_tasks(tasks, strategy="smart", today=today)
        # ensure in_cycle flag exists for at least one task and warnings include cycle
        in_cycle_flags = [t["in_cycle"] for t in res["tasks"]]
        self.assertTrue(any(in_cycle_flags))
        self.assertTrue(any("circular_dependency_nodes" in w or "circular dependency" in w for w in res["warnings"]))
