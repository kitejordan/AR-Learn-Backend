from fastapi import APIRouter
from app.dtos.qa import AskAboutPartIn, AskAboutPartOut, FindPartByFunctionIn, FindPartByFunctionOut
from app.managers.graph_manager import GraphManager
from app.clients.openai_client import llm

router = APIRouter(prefix="/qa", tags=["qa"])
graph = GraphManager()

# New endpoint to ask about a part

@router.post("/ask-about-part", response_model=AskAboutPartOut)
def ask_about_part(inp: AskAboutPartIn):
    ctx = graph.get_part_context(inp.part_name)
    prompt = (
      "You are an expert AR tutor. Use ONLY this context.\n"
      f"Part: {ctx.get('name')}\n"
      f"Description: {ctx.get('description')}\n"
      f"Functions: {', '.join(ctx.get('functions', []))}\n"
      f"ConnectsTo: {', '.join(ctx.get('connects_to', []))}\n"
      f"Q: {inp.user_question}\nA:"
    )
    out = llm.invoke(prompt)
    return AskAboutPartOut(response_text=out.content)

# New endpoint to find part by function

@router.post("/find-part-by-function", response_model=FindPartByFunctionOut)
def find_part_by_function(inp: FindPartByFunctionIn):
    part = graph.find_part_by_function(inp.user_question)
    return FindPartByFunctionOut(part_name_to_highlight=part or "")
