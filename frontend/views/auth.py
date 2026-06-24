import streamlit as st
import api_client

def render_auth_portal():
    """Renders the centralized signup and login form portal."""
    st.markdown("<h1 class='gradient-text'>Domain Knowledge Co-Pilot</h1>", unsafe_allow_html=True)
    st.markdown("<p class='sub-text'>Intelligent RAG Document Assistant</p>", unsafe_allow_html=True)
    
    auth_tab1, auth_tab2 = st.tabs(["🔒 Log In", "📝 Sign Up"])
    
    with auth_tab1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)
            if submitted:
                if not username.strip() or not password:
                    st.error("Please enter both username and password.")
                else:
                    success, msg = api_client.login(username.strip(), password)
                    if success:
                        st.success("Log in successful!")
                        st.rerun()
                    else:
                        st.error(msg)
                        
    with auth_tab2:
        with st.form("signup_form"):
            reg_username = st.text_input("Choose Username")
            reg_password = st.text_input("Choose Password", type="password")
            submitted = st.form_submit_button("Create Account", use_container_width=True)
            if submitted:
                if not reg_username.strip() or not reg_password:
                    st.error("Please enter both username and password.")
                elif len(reg_password) < 6:
                    st.error("Password must be at least 6 characters long.")
                else:
                    success, msg = api_client.signup(reg_username.strip(), reg_password)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
