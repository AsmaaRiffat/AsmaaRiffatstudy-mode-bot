import streamlit as st
import os
import io
from PIL import Image

from google import genai
from google.genai import types

import pdfplumber
from docx import Document

# ---- Setup client ----
API_KEY = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
if not API_KEY:
    st.error("No GEMINI_API_KEY found. Add it in Streamlit Secrets (GEMINI_API_KEY).")
    st.stop()

client = genai.Client(api_key=API_KEY)
MODEL_ID = "gemini-1.5-flash"

# --- Title ---
st.title("🎓 Smart Study Buddy")

# --- Session State ---
if "conversation" not in st.session_state:
    st.session_state.conversation = []  # stores [{"role":"user","content":...},{"role":"model","content":...}]
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
    st.session_state.conversation = []

# --- Study Mode ---
mode = st.radio("Choose a study mode:", ["Explain", "Quiz", "Review"], horizontal=True)

# --- Chat Input ---
user_input = st.chat_input("Type your question or topic...")

def call_gemini(prompt_text, image_bytes=None):
    """Call Gemini API (with optional image)."""
    try:
        if image_bytes:
            mime = uploaded_image.type if uploaded_image is not None else "image/jpeg"
            image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime)
            text_part = types.Part.from_text(prompt_text)   # ✅ only one argument
            contents = [image_part, text_part]
            response = client.models.generate_content(model=MODEL_ID, contents=contents)
        else:
            text_part = types.Part.from_text(prompt_text)   # ✅ only one argument
            response = client.models.generate_content(model=MODEL_ID, contents=[text_part])
        return response.text

    except Exception as e:
        error_msg = str(e)
        if "RESOURCE_EXHAUSTED" in error_msg:
            return "⚠️ Oops! You’ve used up today’s free quota (50 requests/day). Please try again tomorrow, or upgrade your Gemini plan for more usage."
        elif "PERMISSION_DENIED" in error_msg:
            return "⚠️ API key is invalid or missing required permissions. Check your Google AI Studio settings."
        else:
            return f"⚠️ Something went wrong: {error_msg}"


        # Add image if uploaded
        if image_bytes:
            mime = "image/jpeg"
            contents.append(types.Content(role="user", parts=[types.Part.from_bytes(image_bytes, mime_type=mime)]))

        response = client.models.generate_content(model=MODEL_ID, contents=contents)
        return response.text

    except Exception as e:
        error_msg = str(e)
        if "RESOURCE_EXHAUSTED" in error_msg:
            return "⚠️ Oops! You’ve used up today’s free quota (50 requests/day). Please try again tomorrow, or upgrade your Gemini plan."
        elif "PERMISSION_DENIED" in error_msg:
            return "⚠️ API key is invalid or missing permissions. Check your Google AI Studio settings."
        else:
            return f"⚠️ Something went wrong: {error_msg}"

# --- Handle input ---
if user_input or image_bytes:
    if user_input:
        st.session_state.conversation.append({"role": "user", "content": user_input})
        query_text = user_input
    else:
        st.session_state.conversation.append({"role": "user", "content": "📷 Sent an image"})
        query_text = "Please describe and explain this image, and give 2 short flashcards."

    context = st.session_state.file_content
    if mode == "Explain":
        system_prompt = f"You are a teacher. Explain this step by step in simple terms. Do not ask follow-up questions.\n\nReference notes:\n{context}"
    elif mode == "Quiz":
        system_prompt = f"You are a quiz master. Create 3-5 quiz questions (answers hidden). Keep it concise.\n\nReference notes:\n{context}"
    else:  # Review
        system_prompt = f"You are a study coach. Summarize and review this clearly. End after summary.\n\nReference notes:\n{context}"

    # Insert system role at the start
    st.session_state.conversation.append({"role": "user", "content": f"{system_prompt}\n\nTopic: {query_text}"})

    with st.spinner("⏳ Thinking..."):
        reply = call_gemini(st.session_state.conversation, image_bytes=image_bytes)

    st.session_state.conversation.append({"role": "model", "content": reply})

# --- Chat Display ---
for msg in st.session_state.conversation:
    if msg["role"] == "user":
        st.markdown(
            f"""
            <div style='text-align:right; background:#DCF8C6; color:#000000;
                        padding:10px; border-radius:12px; margin:6px; 
                        max-width:85%; float:right; clear:both;'>
                <b>🧑 You:</b><br>{msg["content"]}
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""
            <div style='text-align:left; background:#F1F0F0; color:#000000;
                        padding:10px; border-radius:12px; margin:6px; 
                        max-width:85%; float:left; clear:both;'>
                <b>🤖 Bot:</b><br>{msg["content"]}
            </div>
            """,
            unsafe_allow_html=True
        )
