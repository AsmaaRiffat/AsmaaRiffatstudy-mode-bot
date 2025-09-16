# streamlit_app.py
import streamlit as st
import os
import io
from PIL import Image

# new GenAI SDK
from google import genai
from google.genai import types

# text extraction helpers
import pdfplumber
from docx import Document

# ---- Setup client ----
API_KEY = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
if not API_KEY:
    st.error("No GEMINI_API_KEY found. Add it in Streamlit Secrets (GEMINI_API_KEY).")
    st.stop()

# create genai client (works for Gemini Developer API / Vertex as appropriate)
client = genai.Client(api_key=API_KEY)
MODEL_ID = "gemini-1.5-flash"  # change if you want another Gemini model

st.title("📚 Study Mode (Gemini) — PDF, DOCX, Image support")

# session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "file_content" not in st.session_state:
    st.session_state.file_content = ""

# --- Upload notes (txt / pdf / docx) ---
uploaded_file = st.file_uploader("Upload notes (.txt, .pdf, .docx)", type=["txt", "pdf", "docx"])
if uploaded_file is not None:
    try:
        file_bytes = uploaded_file.read()
        mime = uploaded_file.type or ""
        if "pdf" in mime or uploaded_file.name.lower().endswith(".pdf"):
            # robust PDF extraction with pdfplumber
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                pages = [p.extract_text() or "" for p in pdf.pages]
            text = "\n\n".join(pages).strip()
        elif "plain" in mime or uploaded_file.name.lower().endswith(".txt"):
            text = file_bytes.decode("utf-8", errors="ignore")
        else:  # docx
            doc = Document(io.BytesIO(file_bytes))
            text = "\n".join([p.text for p in doc.paragraphs]).strip()

        st.session_state.file_content = text
        st.success("✅ File processed. (Use it as reference for questions)")
    except Exception as e:
        st.error(f"Failed to process uploaded file: {e}")

# --- Upload image (jpg/png) ---
uploaded_image = st.file_uploader("Upload an image (jpg, png) — optional", type=["jpg", "jpeg", "png"])
image_bytes = None
if uploaded_image is not None:
    try:
        image_bytes = uploaded_image.read()
        pil_img = Image.open(io.BytesIO(image_bytes))
        st.image(pil_img, caption="Uploaded image", use_column_width=True)
    except Exception as e:
        st.error(f"Failed to read image: {e}")
        image_bytes = None

# Clear chat
if st.button("🗑️ Clear Chat"):
    st.session_state.chat_history = []

# mode selector
mode = st.radio("Choose study mode:", ["Explain", "Quiz", "Review"], horizontal=True)

# input
user_input = st.chat_input("Type your question or topic...")

def call_gemini(prompt_text, image_bytes=None):
    """Call Gemini: if image_bytes provided, send inline image part + prompt."""
    try:
        if image_bytes:
            # create an image Part from raw bytes (use uploaded mime type if you know it)
            # determine mime type from uploaded file name or default to jpeg
            mime = uploaded_image.type if uploaded_image is not None else "image/jpeg"
            image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime)
            contents = [image_part, prompt_text]  # image first, then text prompt (recommended)
            response = client.models.generate_content(model=MODEL_ID, contents=contents)
        else:
            response = client.models.generate_content(model=MODEL_ID, contents=prompt_text)
        return response.text
    except Exception as e:
        # return a readable error so you can see Streamlit logs
        return f"⚠️ API/error: {type(e).__name__}: {e}"

if user_input or image_bytes:
    # save user message
    if user_input:
        st.session_state.chat_history.append(("You", user_input))
        query_text = user_input
    else:
        # if only image sent, set prompt to request explanation
        st.session_state.chat_history.append(("You", "📷 Sent an image"))
        query_text = "Please describe and explain this image, and give 2 short flashcards."

    # add uploaded notes as context if available
    context = st.session_state.file_content
    if mode == "Explain":
        prompt = f"You are a friendly teacher. Explain step by step with simple examples.\n\nQuestion/Topic: {query_text}\n\nReference notes:\n{context}"
    elif mode == "Quiz":
        prompt = f"You are a quiz master. Create 3-5 quiz questions (with answers hidden) on: {query_text}\n\nReference notes:\n{context}"
    else:  # Review
        prompt = f"You are a study coach. Summarize and list the key points for: {query_text}\n\nReference notes:\n{context}"

    with st.spinner("Asking Gemini..."):
        reply = call_gemini(prompt, image_bytes=image_bytes)
    st.session_state.chat_history.append(("Bot", reply))

# Display chat with clear distinction
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
