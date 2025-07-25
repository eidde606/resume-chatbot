from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader
import gradio as gr
import os
from fastapi import FastAPI
from pydantic import BaseModel
import json
import smtplib
from email.mime.text import MIMEText


app = FastAPI()


class Booking(BaseModel):
    name: str
    email: str
    datetime: str
    reason: str


@app.post("/schedule")
async def schedule_meeting(data: Booking):
    print("📬 New Meeting Request:")
    print(f"Name: {data.name}")
    print(f"Email: {data.email}")
    print(f"Date/Time: {data.datetime}")
    print(f"Reason: {data.reason}")
    return {"success": True, "message": "Meeting scheduled successfully"}


load_dotenv()
openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


reader = PdfReader("me/EddieResumeUpdate.pdf")
EddieResumeUpdate = ""
for page in reader.pages:
    text = page.extract_text()
    if text:
        EddieResumeUpdate += text

        EddieResumeUpdate = EddieResumeUpdate.strip()

        print(EddieResumeUpdate)


name = "Eddie"

system_prompt = f"You are acting as {name}. You are answering questions on {name}'s website, \
particularly questions related to {name}'s career, background, skills, and experience. \
Your responsibility is to represent {name} for interactions on the website as faithfully as possible. \
You are given a summary of {name}'s background and LinkedIn profile which you can use to answer questions. \
Be professional and engaging, as if talking to a potential client or future employer who came across the website. \
If you don't know the answer, say so. If a client or potential employer asks to contact you, \
provide them with the email eiddenazario@gmail.com and cell number 804-528-7612."

system_prompt += (
    f"\n\n## Summary:\n{EddieResumeUpdate}\n\n## Resume:\n{EddieResumeUpdate}\n\n"
)

system_prompt += f"With this context, please chat with the user, always staying in character as {name}."

# ✨ New functionality: Meeting scheduling instructions
system_prompt += (
    "\n\nIf someone wants to schedule a meeting with Eddie, kindly collect the following details:\n"
    "- Their full name\n"
    "- Their email address\n"
    "- The date and time they want to meet (be flexible and interpret natural language)\n"
    "- The reason for the meeting\n\n"
    "Once you've gathered everything, respond with ONLY this format (no extra text):\n"
    '{ "action": "schedule_meeting", "name": "<FULL NAME>", "email": "<EMAIL>", "datetime": "<DATE AND TIME>", "reason": "<REASON>" }\n\n'
    "If you're missing anything, ask follow-up questions until you have all required information."
)


def chat(message, history):
    messages = (
        [{"role": "system", "content": system_prompt}]
        + history
        + [{"role": "user", "content": message}]
    )
    response = openai.chat.completions.create(model="gpt-4o-mini", messages=messages)
    raw_reply = response.choices[0].message.content

    # Check for scheduling intent
    if '"action": "schedule_meeting"' in raw_reply:
        print("\n📆 SCHEDULING REQUEST DETECTED")
        print(raw_reply)

        try:
            payload = json.loads(raw_reply.split("\n")[-1])
            name = payload["name"]
            email = payload["email"]
            datetime = payload["datetime"]
            reason = payload["reason"]

            send_email_to_client(email, name, datetime, reason)
            send_email_to_me(name, email, datetime, reason)

            # Friendly message for the user instead of raw JSON
            return (
                f"✅ Your meeting has been scheduled!\n\n"
                f"👤 Name: {name}\n"
                f"📧 Email: {email}\n"
                f"🗓️ Date/Time: {datetime}\n"
                f"💬 Reason: {reason}\n\n"
                "I'll see you then!"
            )

        except Exception as e:
            print("❌ Error handling schedule request:", e)
            return "Oops! Something went wrong when trying to schedule the meeting."

    # Fallback: just return the model's reply
    return raw_reply


def send_email_to_client(to_email, name, datetime, reason):
    user = os.getenv("GMAIL_USER")
    password = os.getenv("GMAIL_PASS")

    subject = "Your Meeting with Eddie Nazario"
    body = f"""
    Hi {name},

    This is a confirmation that your meeting with Eddie Nazario has been scheduled.

    📅 Date and Time: {datetime}\n
    💬 Reason: {reason}

    If you have any questions before the meeting, feel free to reply to this email.

    Regards,
    Eddie Nazario
    """

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(user, password)
            server.sendmail(user, to_email, msg.as_string())
        print("✅ Email sent to client")
    except Exception as e:
        print("❌ Error sending email:", e)


def send_email_to_me(name, email, datetime, reason):
    user = os.getenv("GMAIL_USER")
    password = os.getenv("GMAIL_PASS")

    subject = f"📅 New Meeting Scheduled with {name}"
    body = f"""
    You have a new meeting scheduled via NazborgAI.

    👤 Name: {name}
    📧 Email: {email}
    🗓️ Date/Time: {datetime}
    💬 Reason: {reason}

    Make sure to review the details before the meeting.
    """

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = user  # Sending to yourself

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(user, password)
            server.sendmail(user, user, msg.as_string())
        print("✅ Notification email sent to Eddie")
    except Exception as e:
        print("❌ Error sending notification email to Eddie:", e)


gr.ChatInterface(chat, type="messages").launch(
    server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860))
)
