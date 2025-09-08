from typing import List, Dict
from app.clients.openai_client import llm

SYSTEM = ("You are a concise AR tutor. "
          "Write short, simple lines aligned with the timeline steps.")

class NarrationManager:
    def build_lines(self, action_id: str, timeline: List[Dict]) -> List[Dict]:
        # Minimal stub: derive lines from effect/target; you can enrich via LLM later
        lines = []
        for i, st in enumerate(timeline):
            target = st.get("target") or (st.get("path") or ["Flow"])[-1]
            txt = f"{target}: {st['effect']}"
            lines.append({"t": st["t"], "text": txt})
        return lines
