from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader
import gradio as gr
import os

load_dotenv()
openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


reader = PdfReader("EddieResumeUpdate.pdf")
EddieResumeUpdate = ""
for page in reader.pages:
    text = page.extract_text()
    if text:
        EddieResumeUpdate += text

        EddieResumeUpdate = EddieResumeUpdate.strip()

        print(EddieResumeUpdate)


name = "Eddie"

system_prompt = f"You are acting as {name}. You are answering questions on {name}'s website, \
particularly questions related to {name}'s career, background, skills and experience. \
Your responsibility is to represent {name} for interactions on the website as faithfully as possible. \
You are given a summary of {name}'s background and LinkedIn profile which you can use to answer questions. \
Be professional and engaging, as if talking to a potential client or future employer who came across the website. \
If you don't know the answer, say so and if client or potential employer ask to contact you provide them with email eiddenazario@gmail.com and cel number 804-528-7612."

system_prompt += (
    f"\n\n## Summary:\n{EddieResumeUpdate}\n\n## Resume:\n{EddieResumeUpdate}\n\n"
)
system_prompt += f"With this context, please chat with the user, always staying in character as {name}."

system_prompt


def chat(message, history):
    messages = (
        [{"role": "system", "content": system_prompt}]
        + history
        + [{"role": "user", "content": message}]
    )
    response = openai.chat.completions.create(model="gpt-4o-mini", messages=messages)
    return response.choices[0].message.content


gr.ChatInterface(chat, type="messages").launch()
