from pydantic import BaseModel

class AskAboutPartIn(BaseModel):
    part_name: str
    user_question: str                              # determine which part the user is asking about, and what they want to know

class AskAboutPartOut(BaseModel):                      # basically the schema for each endpoint
    response_text: str

class FindPartByFunctionIn(BaseModel):
    user_question: str

class FindPartByFunctionOut(BaseModel):
    part_name_to_highlight: str
