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
from app.clients.openai_client import llm, client # <-- Import both clients
import base64
import io

router = APIRouter(prefix="/qa", tags=["qa"])
graph = GraphManager()

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
    # We still use the LangChain client for this text-based task
    out = llm.invoke(prompt)
    return AskAboutPartOut(response_text=out.content)

@router.post("/find-part-by-function", response_model=FindPartByFunctionOut)
def find_part_by_function(inp: FindPartByFunctionIn):
    part = graph.find_part_by_function(inp.user_question)
    return FindPartByFunctionOut(part_name_to_highlight=part or "")


# --- NEW AUDIO ENDPOINT AND HELPER FUNCTIONS ---

@router.post("/ask-about-part-audio", response_model=AskAboutPartAudioOut)
def ask_about_part_audio(inp: AskAboutPartAudioIn):
    """
    Handles the full STT -> AI Tutor -> TTS pipeline.
    """
    # Step 1: Transcribe audio to text with Whisper
    try:
        user_question_text = transcribe_audio(inp.audio_data)
        print(f"Whisper Transcription: '{user_question_text}'")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audio transcription failed: {e}")

    # Step 2: Get AI text response (reusing our existing text endpoint logic)
    text_response = ask_about_part(AskAboutPartIn(part_name=inp.part_name, user_question=user_question_text)).response_text
    print(f"AI Tutor Response: '{text_response}'")

    # Step 3: Convert the AI's text response back to speech
    try:
        audio_reply_base64 = text_to_speech(text_response)
        print("TTS audio generation successful.")
    except Exception as e:
        # If TTS fails, we can still send back the text response as a fallback
        print(f"TTS failed: {e}")
        return AskAboutPartAudioOut(response_text=text_response, audio_reply=None)

    # Step 4: Return both the text and the Base64 encoded audio
    return AskAboutPartAudioOut(response_text=text_response, audio_reply=audio_reply_base64)


def transcribe_audio(base64_audio_data: str) -> str:
    """Decodes Base64 audio and sends it to OpenAI Whisper for transcription."""
    audio_bytes = base64.b64decode(base64_audio_data)
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = "audio.wav"

    # Use the standard OpenAI client for audio tasks
    transcription = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file
    )
    return transcription.text


def text_to_speech(text: str) -> str:
    """Converts text to speech using OpenAI TTS and returns it as a Base64 string."""
    # Use the standard OpenAI client for audio tasks
    response = client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=text,
        response_format="wav"
    )
    
    audio_bytes = response.content
    return base64.b64encode(audio_bytes).decode('utf-8')
