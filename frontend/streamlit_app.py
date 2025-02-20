import streamlit as st
import requests
import json

# Base URL for the FastAPI backend
BASE_URL = "http://localhost:8000"

# Initialize session state variables if not already set
if "token" not in st.session_state:
    st.session_state.token = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- Sign Up, Login, and Profile functions ---

def signup():
    st.subheader("Sign Up")
    email = st.text_input("Email", key="signup_email")
    password = st.text_input("Password", type="password", key="signup_password")
    full_name = st.text_input("Full Name", key="signup_fullname")
    if st.button("Sign Up"):
        data = {
            "email": email,
            "password": password,
            "full_name": full_name
        }
        response = requests.post(f"{BASE_URL}/signup", json=data)
        try:
            resp_json = response.json()
        except Exception:
            resp_json = {}
        if response.status_code == 200 and resp_json:
            st.success("Sign up successful. Please log in.")
        else:
            error_detail = resp_json.get("detail", response.text or "Sign up failed.")
            st.error(error_detail)

def login():
    st.subheader("Login")
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_password")
    if st.button("Login"):
        data = {"username": email, "password": password}
        response = requests.post(f"{BASE_URL}/login", data=data)
        try:
            resp_json = response.json()
        except Exception:
            resp_json = {}
        if response.status_code == 200 and "access_token" in resp_json:
            token = resp_json["access_token"]
            st.session_state.token = token
            st.success("Login successful!")
        else:
            error_detail = resp_json.get("detail", response.text or "Login failed.")
            st.error(error_detail)

def profile():
    st.subheader("Profile")
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    response = requests.get(f"{BASE_URL}/profile", headers=headers)
    try:
        user = response.json()
    except Exception:
        user = {}
    if response.status_code == 200 and user:
        st.write("**Email:**", user["email"])
        st.write("**Full Name:**", user.get("full_name", ""))
        travel_preferences = user.get("travel_preferences", {})
        st.write("**Travel Preferences:**", travel_preferences)
        st.write("### Update Profile")
        new_full_name = st.text_input("Full Name", value=user.get("full_name", ""), key="profile_full_name")
        new_preferences = st.text_area("Travel Preferences (JSON)", value=json.dumps(travel_preferences, indent=2), key="profile_preferences")
        if st.button("Update Profile"):
            try:
                preferences_dict = json.loads(new_preferences)
            except Exception as e:
                st.error("Invalid JSON for travel preferences.")
                return
            data = {
                "email": user["email"],
                "full_name": new_full_name,
                "travel_preferences": preferences_dict
            }
            update_response = requests.put(f"{BASE_URL}/profile", json=data, headers=headers)
            try:
                update_resp_json = update_response.json()
            except Exception:
                update_resp_json = {}
            if update_response.status_code == 200:
                st.success("Profile updated successfully!")
            else:
                error_detail = update_resp_json.get("detail", update_response.text or "Profile update failed.")
                st.error(error_detail)
    else:
        st.error("Unable to fetch profile. Please ensure you are logged in.")

# --- Chat Interface Function ---

def chat():
    st.subheader("Travel Chat")
    query = st.text_input("Enter your travel query:", key="chat_query")
    if st.button("Send Query"):
        if not st.session_state.token:
            st.error("Please login to use the chat feature.")
        elif not query:
            st.error("Query cannot be empty.")
        else:
            headers = {"Authorization": f"Bearer {st.session_state.token}"}
            payload = {"query": query}
            response = requests.post(f"{BASE_URL}/chat", json=payload, headers=headers)
            try:
                resp_json = response.json()
            except Exception:
                resp_json = {}
            if response.status_code == 200 and "response" in resp_json:
                answer = resp_json.get("response", "")
                # Append the current query and its response to chat history
                st.session_state.chat_history.append({"query": query, "response": answer})
            else:
                error_detail = resp_json.get("detail", response.text or "Error processing query")
                st.error("Error processing query: " + error_detail)
    # Display conversation history
    st.write("### Conversation History")
    for chat_entry in st.session_state.chat_history:
        st.markdown(f"**You:** {chat_entry['query']}")
        st.markdown(f"**Assistant:** {chat_entry['response']}")
        st.write("---")

# --- Main Navigation ---

def main():
    st.title("Travel Assistant")
    menu = st.sidebar.selectbox("Navigation", ["Login", "Sign Up", "Profile", "Chat"])
    if menu == "Sign Up":
        signup()
    elif menu == "Login":
        login()
    elif menu == "Profile":
        if st.session_state.token:
            profile()
        else:
            st.warning("Please login first.")
    elif menu == "Chat":
        if st.session_state.token:
            chat()
        else:
            st.warning("Please login first to use the chat feature.")

if __name__ == "__main__":
    main()
