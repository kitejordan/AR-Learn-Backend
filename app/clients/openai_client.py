# This client will be used by all managers to connect to OpenAI , basically creates a langchain client (OK POOKIE ?)

from langchain_openai import ChatOpenAI
from app.config.settings import settings

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2, api_key=settings.OPENAI_API_KEY)
