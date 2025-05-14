import os
from dotenv import load_dotenv
from crewai import LLM
# from langchain_community.chat_models import ChatTogether
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv
# Load environment variables
load_dotenv()


medical_ai=ChatGoogleGenerativeAI(
    api_key=os.getenv("GEMINI_API_KEY"),  # <-- Replace with your actual key
    model="gemini-2.0-flash",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)
def handle_medical_query(user_input):
    """
    Processes medical-related queries and provides an AI-generated response.
    """

    prompt = f"""
    You are Dr. AI, a licensed medical professional. Provide factual and helpful medical information in clear and concise language. If a question is outside your medical knowledge, politely state that you cannot answer. Use plain text only, without special characters or markdown formatting.

    **User's Question:** {user_input}
    
    **Your Answer:**
    """

    try:
        response = medical_ai.invoke(prompt).content.strip()
        return response

    except Exception as e:
        return f"Error processing medical query: {str(e)}"
