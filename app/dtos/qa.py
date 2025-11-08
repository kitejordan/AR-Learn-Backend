from pydantic import BaseModel

class AskAboutPartIn(BaseModel):
    model_id: str | None = None
    model_name: str | None = None
    part_name: str | None = None
    scene: str | None = None
    user_question: str

class AskAboutPartOut(BaseModel):
    response_text: str

class FindPartByFunctionIn(BaseModel):
    user_question: str

class FindPartByFunctionOut(BaseModel):
    part_name_to_highlight: str

class AskAboutPartAudioIn(BaseModel):
    model_id: str | None = None
    model_name: str | None = None
    part_name: str | None = None
    scene: str | None = None
    audio_data: str  # Base64 encoded WAV audio from Unity

class AskAboutPartAudioOut(BaseModel):
    response_text: str
    audio_reply: str | None  # Base64 encoded WAV audio from OpenAI TTS
