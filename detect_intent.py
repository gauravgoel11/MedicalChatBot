import os
from langchain_openai import AzureChatOpenAI
from crewai import LLM
from langchain_google_genai import ChatGoogleGenerativeAI

import os
llm=ChatGoogleGenerativeAI(
    api_key=os.getenv("GEMINI_API_KEY"),  # <-- Replace with your actual key
    model="gemini-2.0-flash",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

def detect_intent(user_input: str) -> str:
    """
    Classify the user's query as 'medical' or 'appointment'.
    No session or conversation memory is used here.
    """

    classification_prompt = f"""
    You are a classification agent. The user said: "{user_input}"

    Classify this query into exactly one of two categories:
    1) "medical" if the user is asking about symptoms, diseases, treatments, medications, or general health.
    2) "appointment" if the user is asking about booking, rescheduling, or canceling appointments, or viewing appointments.

    Return ONLY one word: either "medical" or "appointment".
    """

    try:
        response = llm.invoke(classification_prompt).content.strip().lower()
        if response.startswith("medical"):
            return "medical"
        return "appointment"
    except Exception as e:
        print("LLM Classification Error:", e)
        # Default to 'appointment' on error
        return "appointment"
