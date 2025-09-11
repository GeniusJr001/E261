"""
Main conversation configuration and flow for the Voice Claims system.
This module contains all conversation prompts, field mappings, and dialogue logic.
"""

# CLAIM_FIELDS defines the exact fields the voice flow will collect (order matters).
CLAIM_FIELDS = [
    "Passenger_Name",
    "Booking_Reference",
    "Flight_Number",
    "Flight_Date",
    "Departure_Airport",
    "Departure_time",
    "Arrival_Airport",
    "Arrival_time",
    "Delay_Hours",
    "Compensation_Amount",
    "Claim_Status",
    "Airline",           # airline name
    "Airline_Response"   # collect airline response last
]

# Friendly prompts to ask for each field (used by the voice flow)
FIELD_PROMPTS = {
    "Passenger_Name": "What's your full name as it appears on your ticket?",
    "Booking_Reference": "Please tell me your booking reference or reservation code.",
    "Flight_Number": "What's your flight number? For example, BA123.",
    "Flight_Date": "When was your flight? Please give the date.",
    "Departure_Airport": "Which airport did you depart from (name or IATA code)?",
    "Departure_time": "What time did the flight depart (local time)?",
    "Arrival_Airport": "Which airport were you supposed to arrive at (name or IATA code)?",
    "Arrival_time": "What time were you supposed to arrive (local time)?",
    "Delay_Hours": "Roughly how many hours was your flight delayed?",
    "Compensation_Amount": "If you know it, what's the compensation amount offered so far (or leave blank)?",
    "Claim_Status": "What's the current status of your claim (e.g., New, Pending, Resolved)?",
    "Airline": "Which airline were you flying with?",
    "Airline_Response": "Finally, what did the airline say about your claim? Please describe their response."
}

# Example prompts for clarification when user input is unclear
EXAMPLE_PROMPTS = {
    "Passenger Name": "Please provide your full name as it appears on your ticket (e.g., John Doe).",
    "Contact Email": "Please provide your email address (for example: name@example.com).",
    "Flight Number": "Please provide your flight number (for example: BA123).",
    "Flight Date": "Please provide the date of the flight (Year, Month & Date , an example is., 2023, July 15th).",
    "Airline": "Please provide the airline name (for example: British Airways).",
    "Departure Airport": "Please provide the departure airport (for example: London Heathrow).",
    "Arrival Airport": "Please provide the arrival airport (for example: Amsterdam Schiphol).",
    "Delay Hours": "Please tell me the delay duration in hours (for example: 3).",
    "Airline Response": "Please describe how the airline responded (for example: they offered meal vouchers)."
}

# Conversation flow configuration
CONVERSATION_CONFIG = {
    "intro_message": (
        "Hi, welcome to 261 Claims. I understand how frustrating flight delays can be, "
        "and I'm here to help you resolve it. Let's get started."
    ),
    "open_ended_prompt": (
        "Can you explain what really happened? You can include as many details as you want, "
        "such as your name, flight number, airline, and the delay duration."
    ),
    "completion_message": "Thank you. I have all the details. Please wait while I prepare your claim review...",
    "error_message": "An error occurred. Please try again.",
    "invalid_email_message": "That doesn't look like a valid email address. Please provide a valid email (for example: name@example.com).",
    "clarification_prefix": "Sorry, I didn't catch that."
}

# Claim status flow configuration
CLAIM_STATUS_FLOW = {
    "step_0": {
        "prompt": "Have you submitted a claim before?",
        "next_step": 1
    },
    "step_1": {
        "yes_prompt": "Have you received compensation?",
        "no_response": "New Claim",
        "no_completion": "Thank you. I have all the details.",
        "clarify_prompt": "Please answer yes or no. Have you submitted a claim before?",
        "next_step": 2
    },
    "step_2": {
        "yes_response": "Resolved",
        "no_response": "Pending",
        "completion": "Thank you. I have all the details.",
        "clarify_prompt": "Please answer yes or no. Have you received compensation?"
    }
}

# Timeout configurations (in milliseconds)
TIMEOUTS = {
    "open_ended": 10000,  # 10 seconds for initial open-ended question
    "standard": 2500,     # 2.5 seconds for standard follow-up questions
    "completion": 2500    # 2.5 seconds for completion message
}

def get_initial_prompt():
    """Get the initial conversation prompt combining intro and open-ended question."""
    return f"{CONVERSATION_CONFIG['intro_message']} {CONVERSATION_CONFIG['open_ended_prompt']}"

def get_field_prompt(field_name, newly_filled=True):
    """Get the appropriate prompt for a given field."""
    if newly_filled:
        return FIELD_PROMPTS.get(field_name, f"Could you tell me your {field_name.lower()}?")
    else:
        example = EXAMPLE_PROMPTS.get(field_name)
        if example:
            return f"{CONVERSATION_CONFIG['clarification_prefix']} {example} You also can use the text bar."
        else:
            return f"Could you please provide your {field_name.lower()}?"

def get_claim_status_prompt(step, user_text=""):
    """Get the appropriate claim status prompt based on the current step."""
    user_lower = user_text.lower()
    
    if step == 0:
        return CLAIM_STATUS_FLOW["step_0"]["prompt"], CLAIM_STATUS_FLOW["step_0"]["next_step"]
    elif step == 1:
        if "yes" in user_lower:
            return CLAIM_STATUS_FLOW["step_1"]["yes_prompt"], CLAIM_STATUS_FLOW["step_1"]["next_step"]
        elif "no" in user_lower:
            return CLAIM_STATUS_FLOW["step_1"]["no_completion"], None, CLAIM_STATUS_FLOW["step_1"]["no_response"]
        else:
            return CLAIM_STATUS_FLOW["step_1"]["clarify_prompt"], step
    elif step == 2:
        if "yes" in user_lower:
            return CLAIM_STATUS_FLOW["step_2"]["completion"], None, CLAIM_STATUS_FLOW["step_2"]["yes_response"]
        elif "no" in user_lower:
            return CLAIM_STATUS_FLOW["step_2"]["completion"], None, CLAIM_STATUS_FLOW["step_2"]["no_response"]
        else:
            return CLAIM_STATUS_FLOW["step_2"]["clarify_prompt"], step
    
    return "Please try again.", step

def get_completion_message():
    """Get the completion message when all fields are collected."""
    return CONVERSATION_CONFIG["completion_message"]

def get_invalid_email_message():
    """Get the invalid email error message."""
    return CONVERSATION_CONFIG["invalid_email_message"]

def get_error_message():
    """Get the general error message."""
    return CONVERSATION_CONFIG["error_message"]

def get_timeout(context="standard"):
    """Get the appropriate timeout for the given context."""
    return TIMEOUTS.get(context, TIMEOUTS["standard"])
