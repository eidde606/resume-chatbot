from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader
import gradio as gr
import os
from fastapi import FastAPI
from pydantic import BaseModel, EmailStr, ValidationError
import json
import smtplib
import logging
from email.mime.text import MIMEText
from typing import List, Tuple, Optional


# -----------------------------
# App setup
# -----------------------------
app = FastAPI()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# -----------------------------
# Models
# -----------------------------
class Booking(BaseModel):
    name: str
    email: EmailStr
    datetime: str
    reason: str


# -----------------------------
# FastAPI route
# -----------------------------
@app.post("/schedule")
async def schedule_meeting(data: Booking):
    logging.info("📬 New Meeting Request:")
    logging.info(f"Name: {data.name}")
    logging.info(f"Email: {data.email}")
    logging.info(f"Date/Time: {data.datetime}")
    logging.info(f"Reason: {data.reason}")

    email_sent_to_client = send_email_to_client(
        to_email=data.email,
        name=data.name,
        datetime_value=data.datetime,
        reason=data.reason
    )

    email_sent_to_me = send_email_to_me(
        name=data.name,
        email=data.email,
        datetime_value=data.datetime,
        reason=data.reason
    )

    if email_sent_to_client and email_sent_to_me:
        return {"success": True, "message": "Meeting scheduled successfully"}
    return {
        "success": False,
        "message": "Meeting was captured, but one or more emails failed to send."
    }


# -----------------------------
# Resume loading
# -----------------------------
def load_resume_text(pdf_path: str) -> str:
    try:
        reader = PdfReader(pdf_path)
        extracted_text = ""

        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted_text += text + "\n"

        extracted_text = extracted_text.strip()

        if not extracted_text:
            logging.warning("⚠️ Resume PDF was loaded, but no text was extracted.")
        else:
            logging.info("✅ Resume PDF loaded successfully.")

        return extracted_text

    except FileNotFoundError:
        logging.error(f"❌ Resume file not found at path: {pdf_path}")
        return ""
    except Exception as e:
        logging.error(f"❌ Error loading resume PDF: {e}")
        return ""


resume_text = load_resume_text("me/SoftwareEngineer1.pdf")


# -----------------------------
# Prompt building
# -----------------------------
name = "Eddie"

system_prompt = f"""
You are acting as {name}. You are answering questions on {name}'s website,
particularly questions related to {name}'s career, background, skills, and experience.
Your responsibility is to represent {name} for interactions on the website as faithfully as possible.
You are given {name}'s resume/background context which you can use to answer questions.
Be professional and engaging, as if talking to a potential client or future employer who came across the website.
If you don't know the answer, say so. If a client or potential employer asks to contact you,
provide them with the email eiddenazario@gmail.com and cell number 804-528-7612.
""".strip()

if resume_text:
    system_prompt += f"\n\n## Resume:\n{resume_text}"

system_prompt += f"""

With this context, please chat with the user, always staying in character as {name}.

If someone wants to schedule a meeting with Eddie, kindly collect the following details:
- Their full name
- Their email address
- The date and time they want to meet (be flexible and interpret natural language)
- The reason for the meeting

Once you've gathered everything, respond with ONLY valid JSON in this exact structure:
{{
  "action": "schedule_meeting",
  "name": "<FULL NAME>",
  "email": "<EMAIL>",
  "datetime": "<DATE AND TIME>",
  "reason": "<REASON>"
}}

If you're missing anything, ask follow-up questions until you have all required information.
Do not include markdown code fences.
""".strip()


# -----------------------------
# Email helpers
# -----------------------------
def build_email_message(subject: str, body: str, from_email: str, to_email: str) -> MIMEText:
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    return msg


def send_email_via_gmail(to_email: str, subject: str, body: str) -> bool:
    user = os.getenv("GMAIL_USER")
    password = os.getenv("GMAIL_PASS")

    if not user or not password:
        logging.error("❌ Missing GMAIL_USER or GMAIL_PASS in environment variables.")
        return False

    msg = build_email_message(subject, body, user, to_email)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(user, password)
            server.sendmail(user, to_email, msg.as_string())

        logging.info(f"✅ Email sent successfully to {to_email}")
        return True

    except Exception as e:
        logging.error(f"❌ Error sending email to {to_email}: {e}")
        return False


def send_email_to_client(to_email: str, name: str, datetime_value: str, reason: str) -> bool:
    subject = "Your Meeting with Eddie Nazario"
    body = f"""
Hi {name},

This is a confirmation that your meeting with Eddie Nazario has been scheduled.

📅 Date and Time: {datetime_value}
💬 Reason: {reason}

If you have any questions before the meeting, feel free to reply to this email.

Regards,
Eddie Nazario
""".strip()

    return send_email_via_gmail(to_email, subject, body)


def send_email_to_me(name: str, email: str, datetime_value: str, reason: str) -> bool:
    user = os.getenv("GMAIL_USER")

    if not user:
        logging.error("❌ Missing GMAIL_USER in environment variables.")
        return False

    subject = f"📅 New Meeting Scheduled with {name}"
    body = f"""
You have a new meeting scheduled via NazborgAI.

👤 Name: {name}
📧 Email: {email}
🗓️ Date/Time: {datetime_value}
💬 Reason: {reason}

Make sure to review the details before the meeting.
""".strip()

    return send_email_via_gmail(user, subject, body)


# -----------------------------
# AI response helpers
# -----------------------------
def try_parse_schedule_payload(raw_reply: str) -> Optional[Booking]:
    """
    Attempts to parse the model's response as JSON and validate it as a Booking.
    Returns a Booking object if successful, otherwise None.
    """
    cleaned_reply = raw_reply.strip()

    try:
        payload = json.loads(cleaned_reply)
    except json.JSONDecodeError:
        logging.info("Reply was not valid JSON; treating as normal chat response.")
        return None

    if not isinstance(payload, dict):
        logging.warning("Parsed JSON is not an object.")
        return None

    if payload.get("action") != "schedule_meeting":
        return None

    try:
        booking = Booking(
            name=payload["name"],
            email=payload["email"],
            datetime=payload["datetime"],
            reason=payload["reason"]
        )
        return booking

    except KeyError as e:
        logging.error(f"❌ Missing required booking field: {e}")
        return None
    except ValidationError as e:
        logging.error(f"❌ Booking validation failed: {e}")
        return None
    except Exception as e:
        logging.error(f"❌ Unexpected error validating booking payload: {e}")
        return None


def build_messages(message: str, history: List[Tuple[str, str]]) -> list:
    messages = [{"role": "system", "content": system_prompt}]

    for user_msg, assistant_msg in history:
        messages.append({"role": "user", "content": user_msg})
        messages.append({"role": "assistant", "content": assistant_msg})

    messages.append({"role": "user", "content": message})
    return messages


def get_ai_reply(messages: list) -> str:
    response = client.chat.completions.create(
        model="gpt-5",
        messages=messages
    )

    content = response.choices[0].message.content

    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(item.get("text", ""))
        return "".join(text_parts).strip()

    return (content or "").strip()


# -----------------------------
# Main chat function
# -----------------------------
def chat(message, history):
    try:
        messages = build_messages(message, history)
        raw_reply = get_ai_reply(messages)

        if not raw_reply:
            return "Sorry, I didn't get a response. Please try again."

        booking = try_parse_schedule_payload(raw_reply)

        if booking:
            client_email_sent = send_email_to_client(
                to_email=str(booking.email),
                name=booking.name,
                datetime_value=booking.datetime,
                reason=booking.reason
            )

            my_email_sent = send_email_to_me(
                name=booking.name,
                email=str(booking.email),
                datetime_value=booking.datetime,
                reason=booking.reason
            )

            if client_email_sent and my_email_sent:
                return (
                    f"✅ Your meeting has been scheduled!\n\n"
                    f"👤 Name: {booking.name}\n"
                    f"📧 Email: {booking.email}\n"
                    f"🗓️ Date/Time: {booking.datetime}\n"
                    f"💬 Reason: {booking.reason}\n\n"
                    f"I'll see you then!"
                )

            return (
                "Your meeting details were collected successfully, "
                "but there was a problem sending one or more confirmation emails."
            )

        return raw_reply

    except Exception as e:
        logging.error(f"❌ Error in chat function: {e}")
        return "Oops! Something went wrong on my end. Please try again."


# -----------------------------
# Launch Gradio app
# -----------------------------
gr.ChatInterface(
    fn=chat,
    title="NazborgAI",
    description="Ask Eddie about his background, experience, or schedule a meeting."
).launch(
    server_name="0.0.0.0",
    server_port=int(os.environ.get("PORT", 7860))
)