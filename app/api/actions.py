from fastapi import APIRouter
from app.dtos.actions import ResolveActionIn, ResolveActionOut, TimelineItem
from app.managers.action_manager import ActionManager
from app.managers.narration_manager import NarrationManager

router = APIRouter(prefix="/actions", tags=["actions"])                   # builds a timeline of steps for the action using graph data.
am = ActionManager()                                                      # Unity just executes the timeline (effects on targets, optional flow path) and shows narration
nm = NarrationManager()

@router.post("/resolve", response_model=ResolveActionOut)
def resolve_action(inp: ResolveActionIn):
    pb = am.build_playbook(inp.actionId)
    narration = nm.build_lines(inp.actionId, pb["timeline"])
    return ResolveActionOut(
        actionId=inp.actionId,
        timeline=[TimelineItem(**x) for x in pb["timeline"]],
        labels=[],
        narration=narration,
        sources=[]
    )
