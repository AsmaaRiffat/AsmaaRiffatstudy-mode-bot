import streamlit as st
import google.generativeai as genai
import os

# Configure Gemini API key from Streamlit Secrets
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Choose Gemini model
model = genai.GenerativeModel("gemini-1.5-flash")

# Streamlit UI
st.title("📚 ChatGPT Study Mode Clone (Gemini)")

# Conversation history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Clear chat button
if st.button("🗑️ Clear Chat"):
    st.session_state.chat_history = []

# Study mode selector
mode = st.radio(
    "Choose a study mode:",
    ["Explain", "Quiz", "Review"],
    horizontal=True
)

# Chat input
user_input = st.chat_input("Type your question or topic...")

if user_input:
    # Add user input
    st.session_state.chat_history.append(("You", user_input))

    # Build the prompt depending on mode
    if mode == "Explain":
        prompt = f"You are a teacher. Explain step by step in simple terms with examples:\n{user_input}"
    elif mode == "Quiz":
        prompt = f"You are a quiz master. Ask me 3-5 quiz questions of increasing difficulty about:\n{user_input}"
    elif mode == "Review":
        prompt = f"You are a study coach. Summarize the key points and give a short review about:\n{user_input}"
    
    try:
        # Get response from Gemini
        response = model.generate_content(prompt)
        bot_reply = response.text
    except Exception as e:
        bot_reply = f"⚠️ Error: {e}"

    # Add bot reply
    st.session_state.chat_history.append(("Bot", bot_reply))

# Display chat with bubbles
for role, msg in st.session_state.chat_history:
    if role == "You":
        st.markdown(
            f"<div style='text-align:right; background-color:#DCF8C6; padding:8px; border-radius:10px; margin:5px;'>"
            f"<b>{role}:</b> {msg}</div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"<div style='text-align:left; background-color:#F1F0F0; padding:8px; border-radius:10px; margin:5px;'>"
            f"<b>{role}:</b> {msg}</div>",
            unsafe_allow_html=True
        )
