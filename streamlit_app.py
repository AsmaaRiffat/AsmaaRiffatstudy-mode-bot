import streamlit as st
import os
import io
from PIL import Image

from google import genai
from google.genai import types

import pdfplumber
from docx import Document
from openai import OpenAI

# ---- Setup clients ----
API_KEY_GEMINI = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
API_KEY_OPENAI = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")

if not API_KEY_GEMINI and not API_KEY_OPENAI:
    st.error("⚠️ No API keys found. Add GEMINI_API_KEY and/or OPENAI_API_KEY in Streamlit Secrets.")
    st.stop()

# Gemini client
client_gemini = genai.Client(api_key=API_KEY_GEMINI) if API_KEY_GEMINI else None
MODEL_ID_GEMINI = "gemini-1.5-flash"

# OpenAI client
client_openai = OpenAI(api_key=API_KEY_OPENAI) if API_KEY_OPENAI else None
MODEL_ID_OPENAI = "gpt-4o-mini"  # or gpt-3.5-turbo for cheaper

# --- Title ---
st.title("🎓 Smart Study Buddy")

# --- Session State ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "file_content" not in st.session_state:
    st.session_state.file_content = ""

# --- Upload notes (txt / pdf / docx) ---
uploaded_file = st.file_uploader("📂 Upload your study notes (.txt, .pdf, .docx)", type=["txt", "pdf", "docx"])
if uploaded_file is not None:
    try:
        file_bytes = uploaded_file.read()
        mime = uploaded_file.type or ""
        if "pdf" in mime or uploaded_file.name.lower().endswith(".pdf"):
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                pages = [p.extract_text() or "" for p in pdf.pages]
            text = "\n\n".join(pages).strip()
        elif "plain" in mime or uploaded_file.name.lower().endswith(".txt"):
            text = file_bytes.decode("utf-8", errors="ignore")
        else:
            doc = Document(io.BytesIO(file_bytes))
            text = "\n".join([p.text for p in doc.paragraphs]).strip()

        st.session_state.file_content = text
        st.success("✅ File processed successfully!")
    except Exception as e:
        st.error(f"Failed to process uploaded file: {e}")

# --- Upload image (jpg/png) ---
uploaded_image = st.file_uploader("🖼️ Upload an image (jpg, png)", type=["jpg", "jpeg", "png"])
image_bytes = None
if uploaded_image is not None:
    try:
        image_bytes = uploaded_image.read()
        pil_img = Image.open(io.BytesIO(image_bytes))
        st.image(pil_img, caption="Uploaded image", use_container_width=True)
    except Exception as e:
        st.error(f"Failed to read image: {e}")
        image_bytes = None

# --- Clear chat ---
if st.button("🗑️ Clear Chat"):
    st.session_state.chat_history = []

# --- Study Mode ---
mode = st.radio("Choose a study mode:", ["Explain", "Quiz", "Review"], horizontal=True)

# --- Chat Input ---
user_input = st.chat_input("Type your question or topic...")

def call_ai(prompt_text, image_bytes=None):
    """
    Try Gemini first. If quota exceeded, fall back to OpenAI.
    """
    # --- Try Gemini ---
    if client_gemini:
        try:
            if image_bytes:
                mime = uploaded_image.type if uploaded_image is not None else "image/jpeg"
                image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime)
                contents = [image_part, prompt_text]
                response = client_gemini.models.generate_content(model=MODEL_ID_GEMINI, contents=contents)
            else:
                response = client_gemini.models.generate_content(model=MODEL_ID_GEMINI, contents=prompt_text)
            return response.text + "\n\n _(Answered with Google Gemini)_"
        except Exception as e:
            error_msg = str(e)
            if "RESOURCE_EXHAUSTED" not in error_msg:
                return f"⚠️ Gemini error: {error_msg}"
            # else: fall back

    # --- Fall back to OpenAI ---
    if client_openai:
        try:
            response = client_openai.chat.completions.create(
                model=MODEL_ID_OPENAI,
                messages=[
                    {"role": "system", "content": "You are a helpful and friendly study buddy 😊. Always keep explanations clear, supportive, and engaging."},
                    {"role": "user", "content": prompt_text}
                ]
            )
            return response.choices[0].message.content + "\n\n _(Answered with OpenAI GPT)_"
        except Exception as e2:
            return f"⚠️ OpenAI error: {e2}"

    return "⚠️ No available AI service. Please check your API keys."

# --- Handle input ---
if user_input or image_bytes:
    if user_input:
        st.session_state.chat_history.append(("You", user_input))
        query_text = user_input
    else:
        st.session_state.chat_history.append(("You", "📷 Sent an image"))
        query_text = "Please describe and explain this image, and give 2 short flashcards."

    context = st.session_state.file_content
    if mode == "Explain":
        prompt = f"You are a teacher. Explain step by step in simple terms.\n\nTopic: {query_text}\n\nReference notes:\n{context}"
    elif mode == "Quiz":
        prompt = f"You are a quiz master. Create 3-5 quiz questions (with answers hidden) about:\n{query_text}\n\nReference notes:\n{context}"
    else:  # Review
        prompt = f"You are a study coach. Summarize and review:\n{query_text}\n\nReference notes:\n{context}"

    with st.spinner("⏳ Thinking..."):
        reply = call_ai(prompt, image_bytes=image_bytes)

    st.session_state.chat_history.append(("Bot", reply))

# --- Chat Display ---
for role, msg in st.session_state.chat_history:
    if role == "You":
        st.markdown(
            f"""<div style='text-align:right; background:#DCF8C6; padding:10px; border-radius:12px; margin:6px; max-width:85%; float:right; clear:both;'>
                <b>🧑 You:</b><br>{msg}</div>""",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""<div style='text-align:left; background:#F1F0F0; padding:10px; border-radius:12px; margin:6px; max-width:85%; float:left; clear:both;'>
                <b>🤖 Bot:</b><br>{msg}</div>""",
            unsafe_allow_html=True
        )
