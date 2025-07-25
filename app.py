from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader
import gradio as gr
import os

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
    reply = response.choices[0].message.content

    # Check for scheduling intent
    if '{"action": "schedule"' in reply:
        print("\n✅ SCHEDULING REQUEST DETECTED!")
        print(reply)  # We can later replace this with saving or emailing the details

    return reply


gr.ChatInterface(chat, type="messages").launch(
    server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860))
)
