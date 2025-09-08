

from typing import Dict, Any, List
from app.managers.graph_manager import GraphManager

class ActionManager:                                           # Builds the final playbook (timeline) for Unity:
    def __init__(self):
        self.graph = GraphManager()

    def build_playbook(self, action_id: str) -> Dict[str, Any]:
        data = self.graph.resolve_action(action_id)["rows"]
        timeline = []
        t = 0
        for row in data:
            step = {"t": t, "effect": row["effect"], "params": row.get("params") or {}}
            if row.get("target"):
                step["target"] = row["target"]
            if row.get("path"):
                step["path"] = row["path"]
            timeline.append(step)
            t += step["params"].get("gapMs", 1200)
        return {"timeline": timeline}
