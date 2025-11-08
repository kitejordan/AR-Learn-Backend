from fastapi import APIRouter, HTTPException
from app.dtos.qa import (
    AskAboutPartIn, 
    AskAboutPartOut, 
    FindPartByFunctionIn, 
    FindPartByFunctionOut,
    AskAboutPartAudioIn,
    AskAboutPartAudioOut
)
from app.managers.graph_manager import GraphManager
from app.managers.rag_manager import ask_hybrid
from app.clients.openai_client import client
import base64, io

router = APIRouter(prefix="/qa", tags=["qa"])
graph = GraphManager()

@router.post("/ask-about-part", response_model=AskAboutPartOut)
def ask_about_part(inp: AskAboutPartIn):
    # Hybrid: pgvector + Neo4j
    answer = ask_hybrid(
        question=inp.user_question,
        model_id=inp.model_id,
        model_name=inp.model_name,
        part_name=inp.part_name,
        scene=None  # optional: pass scene from Unity later
    )
    return AskAboutPartOut(response_text=answer)

@router.post("/find-part-by-function", response_model=FindPartByFunctionOut)
def find_part_by_function(inp: FindPartByFunctionIn):
    part = graph.find_part_by_function(inp.user_question)
    return FindPartByFunctionOut(part_name_to_highlight=part or "")

@router.post("/ask-about-part-audio", response_model=AskAboutPartAudioOut)
def ask_about_part_audio(inp: AskAboutPartAudioIn):
    try:
        user_q = transcribe_audio(inp.audio_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audio transcription failed: {e}")

    text_response = ask_about_part(
        AskAboutPartIn(
            model_id=inp.model_id,
            model_name=inp.model_name,
            part_name=inp.part_name, 
            scene=inp.scene,
            user_question=user_q,
        )
    ).response_text

    try:
        audio_reply = text_to_speech(text_response)
    except Exception:
        audio_reply = None

    return AskAboutPartAudioOut(response_text=text_response, audio_reply=audio_reply)

def transcribe_audio(base64_audio_data: str) -> str:
    audio_bytes = base64.b64decode(base64_audio_data)
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = "audio.wav"
    transcription = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file
    )
    return transcription.text

def text_to_speech(text: str) -> str:
    response = client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=text,
        response_format="wav"
    )
    return base64.b64encode(response.content).decode("utf-8")
