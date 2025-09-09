from pydantic import BaseModel

# --- Existing DTOs ---
class AskAboutPartIn(BaseModel):
    part_name: str
    user_question: str

class AskAboutPartOut(BaseModel):
    response_text: str

class FindPartByFunctionIn(BaseModel):
    user_question: str

class FindPartByFunctionOut(BaseModel):
    part_name_to_highlight: str

# --- New DTOs for the Audio Endpoint ---
class AskAboutPartAudioIn(BaseModel):
    part_name: str
    audio_data: str # Base64 encoded WAV audio from Unity

class AskAboutPartAudioOut(BaseModel):
    response_text: str
    audio_reply: str | None # Base64 encoded WAV audio from OpenAI TTS
