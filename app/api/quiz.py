from fastapi import APIRouter, HTTPException
from app.dtos.quiz import GenerateQuizIn, GenerateQuizOut, MCQ
from app.managers.quiz_manager import QuizManager

router = APIRouter(prefix="/quiz", tags=["quiz"])
qm = QuizManager()

@router.post("/generate", response_model=GenerateQuizOut)
def generate_quiz(inp: GenerateQuizIn):
    """
    Generates MCQs strictly from the model-scoped graph context.
    No persistence; returns JSON for Unity to render.
    """
    if not inp.model_id and not inp.model_name:
        raise HTTPException(400, "Provide either model_id or model_name")

    try:
        qs = qm.generate_quiz(
            model_id=inp.model_id,
            model_name=inp.model_name,
            num_questions=inp.num_questions,
            difficulty=inp.difficulty,
            include_parts=inp.include_parts,
        )
    except Exception as e:
        # Surface a clean error up; logs can capture more detail if needed
        raise HTTPException(500, f"Quiz generation failed: {e}")

    return GenerateQuizOut(
        model_id=inp.model_id,
        model_name=inp.model_name,
        difficulty=inp.difficulty,
        questions=[MCQ(**x) for x in qs],
    )
