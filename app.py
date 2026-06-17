import streamlit as st
from supabase import create_client, Client
from anthropic import Anthropic

# --- CONFIGURATION & INITIALIZATION ---
st.set_page_config(page_title="Company Chatbot", layout="centered")

# Securely fetch secrets (Set these in Streamlit Cloud Secrets or local .env)
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "YOUR_SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "YOUR_SUPABASE_ANON_KEY")
CLAUDE_API_KEY = st.secrets.get("CLAUDE_API_KEY", "YOUR_CLAUDE_API_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
anthropic_client = Anthropic(api_key=CLAUDE_API_KEY)

# Initialize Session States
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- HELPER FUNCTIONS ---
def get_master_prompt():
    try:
        response = supabase.table("config").select("master_prompt").eq("id", 1).execute()
        return response.data[0]["master_prompt"] if response.data else "You are a helpful assistant."
    except Exception:
        return "You are a helpful assistant."

def update_master_prompt(new_prompt):
    supabase.table("config").update({"master_prompt": new_prompt}).eq("id", 1).execute()

# --- LOGIN PAGE ---
if not st.session_state.logged_in:
    st.title("🔒 Company AI Portal")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    
    if st.button("Login", use_container_width=True):
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            st.session_state.logged_in = True
            st.session_state.user_email = email
            st.rerun()
        except Exception as e:
            st.error("Invalid credentials. Please try again.")
    st.stop()

# --- DETERMINING ROLES ---
# Simple check: If email contains 'admin', grant admin rights. Customize as needed.
is_admin = "admin" in st.session_state.user_email.lower()

# --- APP INTERFACE ---
st.sidebar.title(f"👤 {st.session_state.user_email}")
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.messages = []
    st.rerun()

# Admin Panel Panel
if is_admin:
    st.sidebar.markdown("---")
    st.sidebar.subheader("🛠️ Admin Controls")
    current_prompt = get_master_prompt()
    new_prompt = st.sidebar.text_area("Modify Master System Prompt:", value=current_prompt, height=150)
    if st.sidebar.button("Save System Prompt"):
        update_master_prompt(new_prompt)
        st.sidebar.success("Prompt updated successfully!")

# Chat Interface
st.title("🤖 Company Assistant")
master_system_prompt = get_master_prompt()

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# User Input
if user_query := st.chat_input("Ask me anything..."):
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.write(user_query)

    # Generate response from Claude
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # Format history for Claude SDK API format
                api_messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                
                response = anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022", # Or your preferred Claude model
                    max_tokens=1024,
                    system=master_system_prompt,
                    messages=api_messages
                )
                answer = response.content[0].text
                st.write(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
            except Exception as e:
                st.error(f"Error calling Claude API: {e}")