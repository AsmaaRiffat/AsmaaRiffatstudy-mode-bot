import streamlit as st
import google.generativeai as genai
import os
from PIL import Image

# Configure Gemini API key
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

st.title("📚 ChatGPT Study Mode Clone (Gemini)")

# --- Session State ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "file_content" not in st.session_state:
    st.session_state.file_content = ""

# --- File Upload (Text Notes) ---
uploaded_file = st.file_uploader("📂 Upload your study notes (.txt, .pdf, .docx)", type=["txt", "pdf", "docx"])
if uploaded_file is not None:
    if uploaded_file.type == "text/plain":
        st.session_state.file_content = uploaded_file.read().decode("utf-8")

    elif uploaded_file.type == "application/pdf":
        from PyPDF2 import PdfReader
        reader = PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        st.session_state.file_content = text

    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        from docx import Document
        doc = Document(uploaded_file)
        text = "\n".join([p.text for p in doc.paragraphs])
        st.session_state.file_content = text

    st.success("✅ File uploaded and processed successfully!")

# --- Image Upload (New Feature) ---
uploaded_image = st.file_uploader("🖼️ Upload an image (jpg, png)", type=["jpg", "jpeg", "png"])
image_obj = None
if uploaded_image is not None:
    image_obj = Image.open(uploaded_image)
    st.image(image_obj, caption="Uploaded Image", use_column_width=True)

# --- Clear Chat Button ---
if st.button("🗑️ Clear Chat"):
    st.session_state.chat_history = []

# --- Study Mode Selection ---
mode = st.radio(
    "Choose a study mode:",
    ["Explain", "Quiz", "Review"],
    horizontal=True
)

# --- Chat Input ---
user_input = st.chat_input("Type your question or topic...")

if user_input or image_obj:
    # Save user message
    if user_input:
        st.session_state.chat_history.append(("You", user_input))
    elif image_obj:
        st.session_state.chat_history.append(("You", "🖼️ Sent an image"))

    # Build prompt
    context_text = st.session_state.file_content if st.session_state.file_content else ""
    if mode == "Explain":
        prompt = f"Explain step by step in simple terms:\n{user_input}\n\nReference Notes:\n{context_text}"
    elif mode == "Quiz":
        prompt = f"Create 3-5 quiz questions with answers about:\n{user_input}\n\nReference Notes:\n{context_text}"
    elif mode == "Review":
        prompt = f"Summarize and review:\n{user_input}\n\nReference Notes:\n{context_text}"

    try:
        if image_obj:
            response = model.generate_content([prompt, image_obj])
        else:
            response = model.generate_content(prompt)
        bot_reply = response.text
    except Exception as e:
        bot_reply = f"⚠️ Error: {e}"

    st.session_state.chat_history.append(("Bot", bot_reply))

# --- Chat Display ---
for role, msg in st.session_state.chat_history:
    if role == "You":
        st.markdown(
            f"""
            <div style='text-align:right; background-color:#DCF8C6; padding:10px; 
                        border-radius:12px; margin:5px; max-width:80%; float:right; clear:both;'>
                <b>🧑 You:</b><br>{msg}
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""
            <div style='text-align:left; background-color:#F1F0F0; padding:10px; 
                        border-radius:12px; margin:5px; max-width:80%; float:left; clear:both;'>
                <b>🤖 Bot:</b><br>{msg}
            </div>
            """,
            unsafe_allow_html=True
        )
