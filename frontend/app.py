import os
import time
import json
from typing import Optional

import streamlit as st
import requests
from dotenv import load_dotenv

load_dotenv()

# Config
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
ADMIN_BYPASS = os.getenv("ADMIN_BYPASS", "False").lower() in ("1", "true", "yes")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")
REQUEST_TIMEOUT = 10


# Helpers: backend wrappers

def backend_available() -> bool:
    try:
        r = requests.get(f"{BACKEND_URL}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def backend_signup(email: str, password: str) -> (bool, str):
    """Call backend signup; return (ok, message)."""
    try:
        r = requests.post(
            f"{BACKEND_URL}/signup",
            json={"email": email, "password": password},
            timeout=REQUEST_TIMEOUT,
        )
        if r.status_code in (200, 201):
            return True, "Account created successfully."
        else:
            data = r.json() if r.headers.get("content-type", "").startswith("application/") else {}
            msg = data.get("detail", r.text[:200])
            return False, f"Signup failed: {msg}"
    except Exception as e:
        return False, f"Signup error: {e}"


def backend_login(email: str, password: str) -> (bool, Optional[str], str):
    """Call backend login; return (ok, token_or_none, message)."""
    try:
        r = requests.post(
            f"{BACKEND_URL}/login",
            json={"email": email, "password": password},
            timeout=REQUEST_TIMEOUT,
        )
        if r.status_code == 200:
            data = r.json()
            token = data.get("token") or data.get("access_token") or data.get("detail")
            # If backend returns token in some other shape, attempt to pick it
            if not token and "token" in data:
                token = data["token"]
            return True, token, "Logged in"
        else:
            data = r.json() if r.headers.get("content-type", "").startswith("application/") else {}
            msg = data.get("detail", r.text[:200])
            return False, None, f"Login failed: {msg}"
    except Exception as e:
        return False, None, f"Login error: {e}"


def backend_generate(token: Optional[str], brief: str, depth: int):
    """Call backend /generate (POST). Return dict or raise."""
    payload = {"brief": brief, "depth": depth}
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.post(f"{BACKEND_URL}/generate", json=payload, headers=headers, timeout=REQUEST_TIMEOUT * 4)
    r.raise_for_status()
    return r.json()


def backend_history(token: Optional[str]):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.get(f"{BACKEND_URL}/history", headers=headers, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()


# Demo fallbacks

def demo_generate(brief: str, depth: int):
    """Safe offline fallback - gives canned content when backend/LLM not available."""
    brief_short = brief.strip()[:120]
    output = {
        "PRD": f"Demo PRD for: {brief_short}\n\n(Expand this with the real backend.)",
        "Landing Page": f"{brief_short} — catchy one-liner, subtitle, features, CTA.",
        "FAQ": "\n".join([f"Q{i+1}: Example question?\nA: Example answer." for i in range(5 if depth < 3 else 10)]),
        # Removed "Video Script" — our model does not provide video scripts
        # Keep demo outputs aligned with actual supported features
    }

    time.sleep(0.8)
    return output


def demo_history():
    return []


# Authentication & session

def init_session_state():
    if "token" not in st.session_state:
        st.session_state["token"] = None
    if "user_email" not in st.session_state:
        st.session_state["user_email"] = None
    if "last_generation" not in st.session_state:
        st.session_state["last_generation"] = None
    if "history" not in st.session_state:
        st.session_state["history"] = None


def developer_auto_login_if_enabled():
    """If ADMIN_BYPASS is enabled, auto-set session token/email for the dev."""
    if ADMIN_BYPASS and ADMIN_EMAIL:
        st.session_state["token"] = "DEV-BYPASS-TOKEN"
        st.session_state["user_email"] = ADMIN_EMAIL
        st.sidebar.success(f"Developer mode: logged in as {ADMIN_EMAIL}")


# UI pieces

def login_signup_sidebar():
    st.sidebar.header("Account")
    if ADMIN_BYPASS and ADMIN_EMAIL:
        st.sidebar.info("Developer bypass is enabled (see .env).")

        if st.sidebar.button("Logout (dev)"):
            st.session_state["token"] = None
            st.session_state["user_email"] = None
        return st.session_state["token"] is not None

    if st.session_state["token"]:
        st.sidebar.success(f"Logged in as {st.session_state.get('user_email')}")
        if st.sidebar.button("Logout"):
            st.session_state["token"] = None
            st.session_state["user_email"] = None
        return True

    # Tabs: Login / Signup
    tab_login, tab_signup = st.sidebar.tabs(["Login", "Sign up"])

    with tab_login:
        st.write("Log in to access generation & history.")
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            if not email or not password:
                st.warning("Please enter email and password.")
            else:
                if backend_available():
                    ok, token, msg = backend_login(email, password)
                    if ok and token:
                        st.session_state["token"] = token
                        st.session_state["user_email"] = email
                        st.success("Logged in successfully.")
                    else:
                        st.error(msg)
                else:
                    st.error("Backend unavailable — cannot log in right now.")

    with tab_signup:
        st.write("Create a new account (backend required).")
        new_email = st.text_input("New email", key="signup_email")
        new_password = st.text_input("New password", type="password", key="signup_password")
        if st.button("Sign up"):
            if not new_email or not new_password:
                st.warning("Please enter email and password.")
            else:
                if backend_available():
                    ok, msg = backend_signup(new_email, new_password)
                    if ok:
                        st.success("Account created — please switch to Login tab and sign in.")
                    else:
                        st.error(msg)
                else:
                    st.error("Backend unavailable — cannot create account right now.")

    return st.session_state.get("token") is not None


# Main app

def main():
    st.set_page_config(page_title="ProductDoc AutoSuite", layout="wide")
    st.title("ProductDoc AutoSuite")
    # Updated caption to remove reference to video scripts
    st.caption("Generate PRD, landing page copy, FAQ and marketing copy from a short product brief.")

    init_session_state()
    developer_auto_login_if_enabled()

    # Sidebar login / signup
    logged_in = login_signup_sidebar()

    # Info bar about backend availability
    backend_ok = backend_available()
    if backend_ok:
        st.info(f"Backend available: {BACKEND_URL}")
    else:
        st.warning("Backend not reachable – the app will run in demo mode for generation/history.")

    # Main layout
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Write product brief (2-3 lines)")
        brief = st.text_area("Product brief", height=150, placeholder="AI tool that helps small businesses create marketing content automatically using templates.")
        depth = st.slider("Depth (detail level)", min_value=1, max_value=3, value=2)

        if st.button("Generate"):
            if not brief.strip():
                st.warning("Please provide a product brief.")
            else:
                with st.spinner("Generating..."):
                    try:
                        if backend_ok:
                            token = st.session_state.get("token")
                            try:
                                res = backend_generate(token, brief, depth)
                            except requests.HTTPError as he:
                                # If backend returns an HTTP error, fallback to demo
                                st.error(f"Backend generation failed: {he}. Using demo output.")
                                res = demo_generate(brief, depth)
                            except Exception as e:
                                st.error(f"Network error during generation: {e}. Using demo output.")
                                res = demo_generate(brief, depth)
                        else:
                            res = demo_generate(brief, depth)
                    except Exception as e:
                        st.error(f"Unexpected error: {e}")
                        res = demo_generate(brief, depth)

                    # store and show
                    st.session_state["last_generation"] = res
                    st.success("Generation complete (see below).")

        # Display last generation
        if st.session_state.get("last_generation"):
            gen = st.session_state["last_generation"]
            st.markdown("### Results")
            for section_name, content in gen.items():
                st.markdown(f"**{section_name}**")
                st.write(content)

    with col2:
        st.subheader("History (last 10)")
        # Fetch history from backend if possible
        history_displayed = False
        if backend_ok:
            try:
                token = st.session_state.get("token")
                history = backend_history(token)
                st.session_state["history"] = history
                if history:
                    for item in history:
                        brief_text = item.get("brief") or item.get("title") or "—"
                        created = item.get("created_at", "")
                        st.markdown(f"- **{brief_text}** — {created}")
                    history_displayed = True
                else:
                    st.info("No history yet. Generate something first.")
                    history_displayed = True
            except Exception as e:
                st.warning(f"Could not load history from backend: {e}")
        if not history_displayed:
            demo_hist = demo_history()
            if demo_hist:
                for item in demo_hist:
                    st.markdown(f"- {item}")
            else:
                st.info("History unavailable (backend offline).")

        st.markdown("---")
        st.subheader("Quick tips")
        st.write(
            """
            • Try a short 1–2 line brief.  
            • Use depth=3 for more detailed output.  
            • If the backend is offline the app uses demo outputs so you can still show the UI.
            """
        )

    st.markdown("---")
    st.caption("Developer: add BACKEND_URL and optional ADMIN_BYPASS/ADMIN_EMAIL in .env to enable developer auto-login.")

    # Debug: small panel for developer to see session info (only show if dev bypass)
    if ADMIN_BYPASS and ADMIN_EMAIL:
        with st.expander("Dev info (session)"):
            st.json({
                "token": st.session_state.get("token"),
                "user_email": st.session_state.get("user_email"),
                "backend_ok": backend_ok,
                "backend_url": BACKEND_URL,
            })


if __name__ == "__main__":
    main()
