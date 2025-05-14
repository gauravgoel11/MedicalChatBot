import os
import sqlite3
import json
import datetime
import re
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

# Load environment variables
load_dotenv()

# Add these state management variables at the top
conversation_states = {}


# Azure LLM Initialization
# llm = AzureChatOpenAI(
#     azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
#     azure_deployment="gpt-4o",
#     api_version= "2023-09-01-preview",
#     api_key=os.getenv("AZURE_OPENAI_API_KEY"),
#     temperature=0
# )
llm=ChatGoogleGenerativeAI(
    api_key=os.getenv("GEMINI_API_KEY"),  # <-- Replace with your actual key
    model="gemini-2.0-flash",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

# Database functions (imported from database.py)
from database import book_appointment, reschedule_appointment, cancel_appointment, get_appointments

# Add these state management variables at the top
conversation_states = {}

def handle_web_request(user_input, session_id):
    # Initialize or retrieve conversation state
    if session_id not in conversation_states:
        conversation_states[session_id] = {
            'step': 'initial',
            'extracted_data': None,
            'missing_fields': []
        }
    
    state = conversation_states[session_id]
    
    # Initial request handling
    if state['step'] == 'initial':
        extracted_data = extract_intent_and_details(user_input)
        state['extracted_data'] = extracted_data
        state['step'] = 'collecting_details'
    
    # Handle details collection
    if state['step'] == 'collecting_details':
        # Update current field with user input
        current_field = state['missing_fields'][0]
        state['extracted_data'][current_field] = user_input
        state['missing_fields'].pop(0)
        
        # Check if more fields needed
        missing = check_missing_fields(state['extracted_data'])
        if missing:
            state['missing_fields'] = missing
            return {'status': 'collecting', 'next_field': missing[0]}
        else:
            # Process complete data
            result = process_web_request(state['extracted_data'])
            del conversation_states[session_id]  # Clear state
            return {'status': 'complete', 'result': result}
    
    return {'error': 'Invalid conversation state'}

def check_missing_fields(data):
    required = []
    if data.get('intent') == 'book':
        required = ["name", "appointment_date", "appointment_time", 
                   "age", "gender", "contact_number", "email", 
                   "department"]
    # Add other intents as needed...
    
    return [field for field in required if not data.get(field)]

def process_web_request(data):
    # Modified version of process_request without CLI inputs
    if data["intent"] == "book":
        department = data.get("medical_history") or data.get("department") or ""
        return book_appointment(
            data["name"], data["age"], data["gender"],
            data["contact_number"], data.get("email", ""),
            department, data["appointment_date"],
            data["appointment_time"]
        )
    # Handle other intents...


def convert_to_24hour_format(time_str):
    """Convert 12-hour time format to 24-hour format"""
    if not time_str:
        return None
        
    # Check if already in 24-hour format (no AM/PM)
    if "AM" not in time_str.upper() and "PM" not in time_str.upper() and ":" in time_str:
        return time_str
    
    # Handle formats like "5 PM", "5PM", "5:30 PM", etc.
    time_str = time_str.strip().upper()
    
    # Extract hours, minutes, and AM/PM
    match = re.match(r"(\d+)(?::(\d+))?\s*(AM|PM)?", time_str)
    if match:
        hours, minutes, period = match.groups()
        hours = int(hours)
        minutes = int(minutes) if minutes else 0
        
        # Convert to 24-hour format
        if period == "PM" and hours < 12:
            hours += 12
        elif period == "AM" and hours == 12:
            hours = 0
            
        return f"{hours:02d}:{minutes:02d}"
    
    return time_str

def convert_relative_date(date_text):
    """Convert relative date terms to actual dates if they weren't converted by the LLM"""
    today = datetime.date.today()
    
    if not date_text:
        return None
        
    # Check if date is already in YYYY-MM-DD format
    if isinstance(date_text, str) and len(date_text) == 10 and date_text[4] == '-' and date_text[7] == '-':
        return date_text
        
    date_text = str(date_text).lower()
    
    if date_text == "today":
        return today.strftime('%Y-%m-%d')
    elif date_text == "tomorrow":
        return (today + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    elif date_text == "day after tomorrow":
        return (today + datetime.timedelta(days=2)).strftime('%Y-%m-%d')
    elif "next week" in date_text:
        return (today + datetime.timedelta(days=7)).strftime('%Y-%m-%d')
    
    # Handle formats like "22March", "22-March", "March22", etc.
    date_patterns = [
        # Day first patterns (22March, 22-March, 22 March)
        r"(\d{1,2})[\s-]?(january|february|march|april|may|june|july|august|september|october|november|december)",
        r"(\d{1,2})[\s-]?(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)",
        # Month first patterns (March22, March-22, March 22)
        r"(january|february|march|april|may|june|july|august|september|october|november|december)[\s-]?(\d{1,2})",
        r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[\s-]?(\d{1,2})"
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, date_text, re.IGNORECASE)
        if match:
            groups = match.groups()
            day = groups[0] if groups[0].isdigit() else groups[1]
            month_str = groups[1] if groups[0].isdigit() else groups[0]
            
            # Convert month name to number
            months = {
                'jan': 1, 'january': 1,
                'feb': 2, 'february': 2,
                'mar': 3, 'march': 3,
                'apr': 4, 'april': 4,
                'may': 5,
                'jun': 6, 'june': 6,
                'jul': 7, 'july': 7,
                'aug': 8, 'august': 8,
                'sep': 9, 'september': 9,
                'oct': 10, 'october': 10,
                'nov': 11, 'november': 11,
                'dec': 12, 'december': 12
            }
            
            month = months.get(month_str.lower())
            if month:
                try:
                    return datetime.date(today.year, month, int(day)).strftime('%Y-%m-%d')
                except ValueError:
                    pass  # Invalid date (e.g., February 30)
    
    # Try to parse date in common formats
    try:
        # Month name formats like "March 15"
        for fmt in ["%B %d", "%b %d", "%B %dth", "%b %dth"]:
            try:
                parsed_date = datetime.datetime.strptime(date_text, fmt)
                # Set the year to current year
                return datetime.date(today.year, parsed_date.month, parsed_date.day).strftime('%Y-%m-%d')
            except ValueError:
                pass
        
        # Try more formats like MM/DD or MM-DD
        for fmt in ["%m/%d", "%m-%d"]:
            try:
                parsed_date = datetime.datetime.strptime(date_text, fmt)
                # Set the year to current year
                return datetime.date(today.year, parsed_date.month, parsed_date.day).strftime('%Y-%m-%d')
            except ValueError:
                pass
    except Exception:
        # If all parsing fails, return the original text
        pass
    
    return date_text

def extract_intent_and_details(user_input):
    today_date = datetime.date.today().strftime('%Y-%m-%d')
    tomorrow_date = (datetime.date.today() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    
    prompt = f"""
    You are an AI assistant that extracts structured details from user requests about doctor appointments.  
    **Return only a valid JSON object** with the following keys:  
    - `"intent"`: "book", "reschedule", "cancel", or "view"
    - `"name"`: Name of the patient (Necessary)  
    - `"appointment_date"`: Date of the appointment (Necessary): Convert relative terms like "today", "tomorrow", or "next week" into actual dates in format "YYYY-MM-DD"
    - `"appointment_time"`: Time of the appointment (if mentioned, else null)  
    - `"doctor"`: Doctor's name or specialization (if mentioned, else null)  
    - `"age"`: Patient's age (if mentioned, else null)  
    - `"gender"`: Patient's gender (if mentioned, else null)
    - `"contact_number"`: Contact number (if mentioned, else null)  
    - `"email"`: Email address (if mentioned, else null)
    - `"department"`: Department if no doctors mentioned already(if mentioned, else null)  Capitalise the first letter of the department Name
    
    For reschedule intent, also include:
    - `"old_date"`: Original appointment date (if mentioned, else null)
    - `"old_time"`: Original appointment time (if mentioned, else null)
    - `"new_date"`: New appointment date (if mentioned, else null)
    - `"new_time"`: New appointment time (if mentioned, else null)

    IMPORTANT: For any relative dates like "today", "tomorrow", or "next Tuesday", convert them to the actual date in YYYY-MM-DD format. Today's date is {today_date}.

    Example Inputs and Outputs:
    1. **User:** "Book an appointment for Alice at 4:30 PM with Dr. Smith tomorrow."  
       **Output:**  
       ```json
       {{"intent": "book", "name": "Alice", "appointment_date": "{tomorrow_date}", "appointment_time": "4:30 PM", "doctor": "Dr. Smith", "age": null, "gender": null, "contact_number": null, "email": null, "department": null}}
       ```

    2. **User:** "Cancel my appointment with Dr. Brown on March 10."  
       **Output:**  
       ```json
       {{"intent": "cancel", "name": null, "appointment_date": "2025-03-10", "appointment_time": null, "doctor": "Dr. Brown", "age": null, "gender": null, "contact_number": null, "email": null, "department": null}}
       ```
       
    3. **User:** "Reschedule my March 15th appointment from 2:00 PM to 4:00 PM on March 20th."
       **Output:**
       ```json
       {{"intent": "reschedule", "name": null, "old_date": "2025-03-15", "old_time": "2:00 PM", "new_date": "2025-03-20", "new_time": "4:00 PM", "doctor": null, "age": null, "gender": null, "contact_number": null, "email": null, "department": null}}
       ```
       
    4. **User:** "Show me my appointments"
       **Output:**
       ```json
       {{"intent": "view", "name": null, "appointment_date": null, "appointment_time": null, "doctor": null, "age": null, "gender": null, "contact_number": null, "email": null, "department": null}}
       ```

    **User Input:** "{user_input}"  
    **Output:** (JSON format only)
    """
    
    response = llm.invoke(prompt).content.strip()

    try:
        # Remove potential markdown code block formatting if present
        if response.startswith("```json"):
            response = response.replace("```json", "", 1)
        if response.endswith("```"):
            response = response.rsplit("```", 1)[0]
            
        extracted_data = json.loads(response.strip())  # Parse JSON safely
        
        # Apply date conversion as a fallback in case the LLM didn't convert properly
        if "appointment_date" in extracted_data and extracted_data["appointment_date"]:
            extracted_data["appointment_date"] = convert_relative_date(extracted_data["appointment_date"])
        
        if "old_date" in extracted_data and extracted_data["old_date"]:
            extracted_data["old_date"] = convert_relative_date(extracted_data["old_date"])
            
        if "new_date" in extracted_data and extracted_data["new_date"]:
            extracted_data["new_date"] = convert_relative_date(extracted_data["new_date"])
        
        # Convert times to 24-hour format
        if "appointment_time" in extracted_data and extracted_data["appointment_time"]:
            extracted_data["appointment_time"] = convert_to_24hour_format(extracted_data["appointment_time"])
            
        if "old_time" in extracted_data and extracted_data["old_time"]:
            extracted_data["old_time"] = convert_to_24hour_format(extracted_data["old_time"])
            
        if "new_time" in extracted_data and extracted_data["new_time"]:
            extracted_data["new_time"] = convert_to_24hour_format(extracted_data["new_time"])

         # Add conversions for all date/time fields
        date_fields = ["appointment_date", "old_date", "new_date"]
        time_fields = ["appointment_time", "old_time", "new_time"]
        
        for field in date_fields:
            if extracted_data.get(field):
                extracted_data[field] = convert_relative_date(extracted_data[field])
                
        for field in time_fields:
            if extracted_data.get(field):
                extracted_data[field] = convert_to_24hour_format(extracted_data[field])
        
        return extracted_data    
    except json.JSONDecodeError:
        print(f"❌ JSON Parsing Error: GPT-4o Response: {response}")
        return {"error": "Could not process input"}

# Collect missing details from the user
def collect_missing_details(data):
    if "error" in data:
        print("❌ Error: Could not understand your request.")
        return None

    if data["intent"] == "book":
        print("\n🔹 Booking an Appointment")
        if not data.get("name"):
            data["name"] = input("Enter patient's name: ").strip()
            
        # Convert appointment date if needed
        if data.get("appointment_date"):
            data["appointment_date"] = convert_relative_date(data["appointment_date"])
        else:
            date_input = input("Enter appointment date (e.g., March 15): ").strip()
            data["appointment_date"] = convert_relative_date(date_input)
            
        if not data.get("appointment_time"):
            time_input = input("Enter appointment time (e.g., 4:30 PM): ").strip()
            data["appointment_time"] = convert_to_24hour_format(time_input)
        else:
            # Ensure time is in 24-hour format
            data["appointment_time"] = convert_to_24hour_format(data["appointment_time"])
            
        if not data.get("age"):
            data["age"] = input("Enter patient's age: ").strip()
        if not data.get("gender"):
            data["gender"] = input("Enter patient's gender: ").strip()
        if not data.get("contact_number"):
            data["contact_number"] = input("Enter contact number: ").strip()
        if not data.get("email"):
            data["email"] = input("Enter email address (or type 'None'): ").strip()
        if not data.get("department") and not data.get("medical_history"):
            department = input("Department: ").strip()
            data["department"] = department
            data["medical_history"] = department  # For backward compatibility
        
        return data

    elif data["intent"] == "reschedule":
        print("\n🔹 Rescheduling an Appointment")
        if not data.get("name"):
            data["name"] = input("Enter patient's name: ").strip()
            
        # Convert old date if needed
        if data.get("old_date"):
            data["old_date"] = convert_relative_date(data["old_date"])
        else:
            old_date_input = input("Enter original appointment date: ").strip()
            data["old_date"] = convert_relative_date(old_date_input)
            
        if not data.get("old_time"):
            old_time_input = input("Enter original appointment time: ").strip()
            data["old_time"] = convert_to_24hour_format(old_time_input)
        else:
            # Ensure time is in 24-hour format
            data["old_time"] = convert_to_24hour_format(data["old_time"])
            
        # Convert new date if needed
        if data.get("new_date"):
            data["new_date"] = convert_relative_date(data["new_date"])
        else:
            new_date_input = input("Enter new appointment date: ").strip()
            data["new_date"] = convert_relative_date(new_date_input)
            
        if not data.get("new_time"):
            new_time_input = input("Enter new appointment time: ").strip()
            data["new_time"] = convert_to_24hour_format(new_time_input)
        else:
            # Ensure time is in 24-hour format
            data["new_time"] = convert_to_24hour_format(data["new_time"])
        
        return data

    elif data["intent"] == "cancel":
        print("\n🔹 Canceling an Appointment")
        if not data.get("name"):
            data["name"] = input("Enter patient's name: ").strip()
            
        # Convert appointment date if needed
        if data.get("appointment_date"):
            data["appointment_date"] = convert_relative_date(data["appointment_date"])
        else:
            date_input = input("Enter appointment date: ").strip()
            data["appointment_date"] = convert_relative_date(date_input)
            
        if not data.get("appointment_time"):
            time_input = input("Enter appointment time: ").strip()
            data["appointment_time"] = convert_to_24hour_format(time_input)
        else:
            # Ensure time is in 24-hour format
            data["appointment_time"] = convert_to_24hour_format(data["appointment_time"])
        
        return data
        
    elif data["intent"] == "view":
        print("\n🔹 Viewing Appointments")
        return data

    return None

# Confirm and process request
def process_request(data):
    if data["intent"] == "book":
        print(f"\n✅ Confirming appointment for {data['name']} on {data['appointment_date']} at {data['appointment_time']}.")
        confirm = input("Confirm? (yes/no): ").strip().lower()
        if confirm == "yes":
            # Get department from either medical_history or department field
            department = data.get("medical_history") or data.get("department") or ""
            
            # Match the exact parameter order and names from database.py
            result = book_appointment(
                data["name"],
                data["age"],
                data["gender"],
                data["contact_number"],
                data["email"] if data["email"] != "None" else "",
                department,
                data["appointment_date"],
                data["appointment_time"]
            )
            
            if isinstance(result, dict) and "error" not in result:
                print(f"📅 Appointment Booked! {result.get('message', '')}")
            else:
                error_msg = result.get("error") if isinstance(result, dict) else str(result)
                print(f"❌ Error: {error_msg}")
        else:
            print("❌ Booking Canceled.")

    elif data["intent"] == "reschedule":
        print(f"\n✅ Confirm rescheduling appointment for {data['name']} from {data['old_date']} at {data['old_time']} to {data['new_date']} at {data['new_time']}.")
        confirm = input("Confirm? (yes/no): ").strip().lower()
        if confirm == "yes":
            # Match the exact parameter order from database.py
            result = reschedule_appointment(
                data["name"],
                data["old_date"],
                data["old_time"],
                data["new_date"],
                data["new_time"]
            )
            print("📅 Appointment Rescheduled!" if result else "❌ Could not reschedule appointment. Please check the details.")
        else:
            print("❌ Rescheduling Canceled.")

    elif data["intent"] == "cancel":
        print(f"\n✅ Confirm canceling appointment for {data['name']} on {data['appointment_date']} at {data['appointment_time']}.")
        confirm = input("Confirm? (yes/no): ").strip().lower()
        if confirm == "yes":
            # Match the exact parameter order from database.py
            result = cancel_appointment(
                data["name"],
                data["appointment_date"],
                data["appointment_time"]
            )
            print("🗑️ Appointment Canceled!" if result else "❌ Could not cancel appointment. Please check the details.")
        else:
            print("❌ Cancellation Canceled.")
            
    elif data["intent"] == "view":
        appointments = get_appointments()
        if appointments and len(appointments) > 0:
            print("\n📋 All Appointments:")
            for i, appt in enumerate(appointments, 1):
                print(f"{i}. Patient: {appt['patientName']} | Doctor: {appt['doctorName']} | Date: {appt['date']} | Time: {appt['time']} | Status: {appt['status']}")
        else:
            print("ℹ️ No appointments found")
