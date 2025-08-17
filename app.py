# =========================== Environment (OpenMP fix) ===========================
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"   # avoid OpenMP runtime clash on Windows
os.environ.setdefault("OMP_NUM_THREADS", "4")

# =============================== App imports ===================================
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=False)

import streamlit as st
from datetime import datetime
from pathlib import Path
import base64

from services.chat_logic import process_user_input



from urllib.parse import urlparse

def _normalize_link(u: str) -> str:
    if not u:
        return u
    if u.startswith("gdoc:"):
        return u  # non-clickable; we show as code
    if not u.startswith("http://") and not u.startswith("https://"):
        # Treat anything that looks like a domain as https
        if "." in u:
            return "https://" + u
    return u

def _short_label(u: str) -> str:
    if u.startswith("gdoc:"):
        return f"Google Doc {u.split(':',1)[1][:8]}…"
    try:
        p = urlparse(u)
        label = p.netloc or u
        if p.path not in ("", "/"):
            label += p.path[:24] + ("…" if len(p.path) > 24 else "")
        return label
    except Exception:
        return u

def _unique(seq):
    seen = set(); out = []
    for x in seq:
        if x not in seen:
            seen.add(x); out.append(x)
    return out

def render_sources_from_session():
    docs = st.session_state.get("last_docs") or []
    raw = []
    for d in docs:
        if isinstance(d, dict):
            s = d.get("source")
            if s:
                raw.append(s)

    if not raw:
        return

    # normalize + deduplicate
    norm = []
    for s in raw:
        link = _normalize_link(s)
        norm.append(link)
    norm = _unique(norm)

    st.markdown("**Sources**")
    for s in norm:
        if s.startswith("gdoc:"):
            st.markdown(f"- `{s}`")
        else:
            st.markdown(f"- [{_short_label(s)}]({s})")



# --- Voice deps (press-and-hold using audio-recorder-streamlit)
try:
    from audio_recorder_streamlit import audio_recorder
    from services.asr import transcribe_wav_bytes
    VOICE_UI = True
except Exception:
    VOICE_UI = False

# --------------------------- Brand Colors ---------------------------
BRAND_NAVY = "#0A2D52"  # logo color
BRAND_WHITE = "#FFFFFF"

# --------------------------- Page Setup ----------------------------
st.set_page_config(page_title="روبوت دردشة ابتكار", page_icon="", layout="wide")

# --------------------------- Theme / CSS ---------------------------
def render_theme_css(dark: bool):
    """
    Theme-aware CSS that covers:
    - Page, header, sidebar (one solid color), bottom/base wrappers
    - Chat bubbles
    - Chat input (modern pill) + send button
    - Buttons/tiles
    """
    NAVY = BRAND_NAVY
    WHITE = "#FFFFFF"

    # Light
    bg        = "#FFFFFF"   # page/base
    text      = "#0F172A"
    subtext   = "#334155"
    user_bg   = NAVY
    user_tx   = WHITE
    bot_bg    = "#F1F5F9"
    bot_tx    = "#111827"
    input_bg  = "#F8FAFC"
    border    = NAVY
    header_bg = "#FFFFFF"
    sidebar_bg= "#F3F6FA"   # unified solid color
    tile_bg   = "#FFFFFF"
    tile_bd   = "#E2E8F0"
    tile_tx   = text
    tile_tx_muted = subtext

    # Dark
    if dark:
        bg        = "#0A1324"
        text      = "#EAF0F7"
        subtext   = "#A7B4C8"
        user_bg   = "#0E2B4A"
        user_tx   = "#EAF0F7"
        bot_bg    = "#111B2D"
        bot_tx    = "#EAF0F7"
        input_bg  = "#0F1A2F"
        border    = "#2A3E60"
        header_bg = "#0A1324"
        sidebar_bg= "#0E172B"
        tile_bg   = "#0F1A2F"
        tile_bd   = "#2A3E60"
        tile_tx   = "#EAF0F7"
        tile_tx_muted = "#A7B4C8"

    st.markdown(f"""
    <style>
    /* FRAME / BASE SURFACES */
    html, body, #root, .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewContainer"] > .main,
    section.main, [data-testid="stMain"],
    [data-testid="stVerticalBlock"],
    [data-testid="stAppViewContainer"] > .main > div,
    [data-testid="stDecoration"],
    [data-testid="stToolbar"],
    footer, [data-testid="stFooter"] {{
      background: {bg} !important;
      color: {text} !important;
    }}

    /* Top header bar */
    [data-testid="stHeader"] {{
      background: {header_bg} !important;
      border-bottom: 1px solid {border}33 !important;
    }}

    /* Sidebar (unified color) */
    [data-testid="stSidebar"],
    [data-testid="stSidebar"] > div,
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"],
    [data-testid="stSidebar"] [data-testid="stHorizontalBlock"],
    [data-testid="stSidebarNav"] {{
      background: {sidebar_bg} !important;
      border: none !important;
    }}

    /* Global typography */
    h1, h2, h3, h4, h5, h6, p, span, div, li {{
      color: {text} !important;
    }}
    .subtle {{ color: {subtext} !important; }}

    /* Content width */
    .block-container {{
      max-width: 900px !important;
      margin-left: auto !important;
      margin-right: auto !important;
      padding-bottom: 8px !important;
    }}

    /* CHAT BUBBLES */
    .chat-bubble {{
      padding: 12px 16px;
      border-radius: 18px;
      margin: 8px 0;
      max-width: 70%;
      display: inline-block;
      word-wrap: break-word;
      line-height: 1.55;
    }}
    .user-bubble {{
      background-color: {user_bg} !important;
      color: {user_tx} !important;
      text-align: right;
      margin-left: auto;
    }}
    .bot-bubble {{
      background-color: {bot_bg} !important;
      color: {bot_tx} !important;
      text-align: left;
      margin-right: auto;
    }}
    .chat-row {{ display: flex; align-items: flex-start; margin-bottom: 10px; }}
    .chat-avatar {{ width: 32px; height: 32px; border-radius: 50%; margin: 0 10px; }}
    .chat-right {{ justify-content: flex-end; flex-direction: row-reverse; }}

    /* WELCOME BUTTONS */
    .stButton > button {{
      background: {tile_bg} !important;
      color: {tile_tx} !important;
      border: 1px solid {tile_bd} !important;
      border-radius: 10px !important;
      padding: 8px 14px !important;
      box-shadow: none !important;
      transition: border-color .2s ease, transform .05s ease;
    }}
    .stButton > button:hover {{
      border-color: {NAVY} !important;
      transform: translateY(-1px);
    }}

    /* CHAT INPUT (modern pill) */
    div[data-testid="stChatInput"] {{
      background: {bg} !important;
      border-top: 1px solid {border}22;
      padding: 12px 0;
    }}
    div[data-testid="stChatInput"] > div {{
      max-width: 900px; margin: 0 auto;
      background: {input_bg};
      border: 1.5px solid {border};
      border-radius: 28px;
      padding: 6px 10px;
    }}
    div[data-testid="stChatInput"] textarea,
    div[data-testid="stChatInput"] textarea:focus,
    div[data-testid="stChatInput"] textarea:active {{
      background: transparent !important;
      color: {text} !important;
      -webkit-text-fill-color: {text} !important;
      caret-color: {text} !important;
      border: none !important;
      box-shadow: none !important;
      outline: none !important;
      min-height: 36px !important;
      max-height: 140px !important;
      padding: 8px 12px !important;
      font-size: 15px !important;
    }}
    div[data-testid="stChatInput"] textarea::placeholder {{ color: {subtext} !important; }}

    [data-testid="stBottomBlockContainer"],
    [data-testid="stDecoration"],
    footer, [data-testid="stFooter"] {{
      background: {bg} !important;
      color: {text} !important;
      border: none !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# --------------------------- Session State Init ---------------------------
if "conversations" not in st.session_state:
    st.session_state.conversations = {}
if "chat_titles" not in st.session_state:
    st.session_state.chat_titles = {}
if "current_chat" not in st.session_state:
    chat_id = datetime.now().strftime("%Y%m%d%H%M%S")
    st.session_state.conversations[chat_id] = []
    st.session_state.chat_titles[chat_id] = "محادثة جديدة"
    st.session_state.current_chat = chat_id
    st.session_state.show_welcome_screen = True
if "show_welcome_screen" not in st.session_state:
    st.session_state.show_welcome_screen = True
if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

# ----------------------- Helper: start or reuse empty chat ----------------------
def start_new_chat():
    # Reuse any existing empty conversation
    for cid, msgs in st.session_state.conversations.items():
        if not msgs:  # empty thread
            st.session_state.current_chat = cid
            st.session_state.show_welcome_screen = True
            return
    # Otherwise create a fresh one
    chat_id = datetime.now().strftime("%Y%m%d%H%M%S")
    st.session_state.conversations[chat_id] = []
    st.session_state.chat_titles[chat_id] = "محادثة جديدة"
    st.session_state.current_chat = chat_id
    st.session_state.show_welcome_screen = True

# --------------------------- Assets / Logo ---------------------------
def load_logo_base64(logo_path: Path) -> str:
    with open(logo_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

logo_path = Path("assets/logo.png")
user_avatar_path = "assets/user.png"
bot_avatar_path = "assets/bot.png"
logo_base64 = load_logo_base64(logo_path)

# --------------------------- Sidebar ---------------------------
with st.sidebar:
    st.image(str(logo_path), use_container_width=True)
    st.header("إدارة المحادثات")

    if st.button("➕ بدء محادثة جديدة", use_container_width=True):
        start_new_chat()
        st.rerun()

    st.subheader("المحادثات السابقة")
    for cid in sorted(st.session_state.conversations.keys(), reverse=True):
        title = st.session_state.chat_titles.get(cid, f"محادثة {cid}")
        if st.button(f"{title}", key=f"load_{cid}", use_container_width=True):
            st.session_state.current_chat = cid
            st.rerun()

    if st.button("🗑 حذف جميع المحادثات", use_container_width=True):
        st.session_state.conversations.clear()
        st.session_state.chat_titles.clear()
        st.session_state.current_chat = None
        st.rerun()

    st.divider()
    st.write("")
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = False
    st.session_state.dark_mode = st.toggle("🌙 Dark mode", value=st.session_state.dark_mode)

# Apply theme after toggle state
render_theme_css(st.session_state.dark_mode)

# ---- Mic-in-Chat CSS (floats mic next to send button)
st.markdown("""
<style>
#mic-fab {
  position: fixed;
  right: 110px;    /* adjust to align with your send button */
  bottom: 18px;    /* sits on the chat input bar */
  z-index: 1000;
}
#mic-fab .stButton > button,
#mic-fab button {
  width: 40px; height: 40px;
  border-radius: 9999px; padding: 0;
}
@media (max-width: 700px){
  #mic-fab { right: 84px; bottom: 14px; }
  #mic-fab button { width: 36px; height: 36px; }
}
</style>
""", unsafe_allow_html=True)

# --------------------------- Chat State ---------------------------
current_id = st.session_state.current_chat
messages = st.session_state.conversations.get(current_id, []) if current_id else []

# --------------------------- Welcome Screen ---------------------------
if st.session_state.show_welcome_screen and not messages:
    st.markdown(
        f'<img src="data:image/png;base64,{logo_base64}" style="display:block;margin:auto;width:220px;"/>',
        unsafe_allow_html=True
    )
    st.markdown(
        f'<h1 style="text-align:center;color:{BRAND_WHITE};">روبوت دردشة ابتكار</h1>',
        unsafe_allow_html=True
    )
    st.markdown("""
    <h3 class="subtle" style="text-align:center; margin-top: 40px;">
        تعرّف على ابتكار
    </h3>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("ما هو تجمع ابتكار وكيف كانت بدايته؟"):
            st.session_state.pending_prompt = "ما هو تجمع ابتكار وكيف كانت بدايته؟"
            st.session_state.show_welcome_screen = False
            st.rerun()
    with col2:
        if st.button("ما هي رؤية ورسالة تجمع ابتكار؟"):
            st.session_state.pending_prompt = "ما هي رؤية ورسالة تجمع ابتكار؟"
            st.session_state.show_welcome_screen = False
            st.rerun()
    with col3:
        if st.button("ما هي الأنشطة والمشاريع التي ينفذها تجمع ابتكار؟"):
            st.session_state.pending_prompt = "ما هي الأنشطة والمشاريع التي ينفذها تجمع ابتكار؟"
            st.session_state.show_welcome_screen = False
            st.rerun()
    with col4:
        if st.button("كيف يمكنني الانضمام إلى تجمع ابتكار؟"):
            st.session_state.pending_prompt = "كيف يمكنني الانضمام إلى تجمع ابتكار؟"
            st.session_state.show_welcome_screen = False
            st.rerun()

# --------------------------- Chat Messages Display ---------------------------
def avatar_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

for msg in messages:
    role = msg["role"]
    content = msg["content"]
    avatar_path = user_avatar_path if role == "user" else bot_avatar_path
    bubble_class = "user-bubble" if role == "user" else "bot-bubble"
    row_class = "chat-row chat-right" if role == "user" else "chat-row"

    st.markdown(f"""
    <div class="{row_class}">
        <img src="data:image/png;base64,{avatar_b64(avatar_path)}" class="chat-avatar">
        <div class="chat-bubble {bubble_class}">{content}</div>
    </div>
    """, unsafe_allow_html=True)

# --------------------------- Send + Stream Reply ---------------------------
def send_and_stream(prompt: str):
    current_id = st.session_state.current_chat
    messages = st.session_state.conversations.get(current_id, [])

    # title from first user turn
    if st.session_state.chat_titles.get(current_id) == "محادثة جديدة":
        st.session_state.chat_titles[current_id] = prompt[:30] + ("..." if len(prompt) > 30 else "")

    # store + render user bubble
    messages.append({"role": "user", "content": prompt})
    st.session_state.conversations[current_id] = messages
    st.markdown(f"""
    <div class="chat-row chat-right">
        <img src="data:image/png;base64,{avatar_b64(user_avatar_path)}" class="chat-avatar">
        <div class="chat-bubble user-bubble">{prompt}</div>
    </div>
    """, unsafe_allow_html=True)

    # typing bubble, then stream
    typing_placeholder = st.empty()
    typing_placeholder.markdown(f"""
    <div class="chat-row">
        <img src="data:image/png;base64,{avatar_b64(bot_avatar_path)}" class="chat-avatar">
        <div class="chat-bubble bot-bubble">...</div>
    </div>
    """, unsafe_allow_html=True)

    response = ""
    stream_placeholder = st.empty()
    typing_placeholder.empty()

    for chunk in process_user_input(prompt, stream=True):
        response += chunk
        stream_placeholder.markdown(f"""
        <div class="chat-row">
            <img src="data:image/png;base64,{avatar_b64(bot_avatar_path)}" class="chat-avatar">
            <div class="chat-bubble bot-bubble">{response}</div>
        </div>
        """, unsafe_allow_html=True)

    messages.append({"role": "assistant", "content": response})
    st.session_state.conversations[current_id] = messages

# --------------------------- Pending prompt from tiles ---------------------------
if st.session_state.pending_prompt:
    st.session_state.show_welcome_screen = False
    queued = st.session_state.pending_prompt
    st.session_state.pending_prompt = None
    send_and_stream(queued)

# --------------------------- Mic in chat bar (press & hold) ---------------------
if VOICE_UI:
    # Floating mic near the chat send button. Press and hold to record; release to stop.
    st.markdown('<div id="mic-fab">', unsafe_allow_html=True)
    audio_bytes = audio_recorder(
        text="",                        # icon-only
        recording_color=BRAND_NAVY,     # matches your theme
        neutral_color="#e2e8f0",
        icon_name="microphone",
        icon_size="2x",
        key="voice_recorder_btn"
    )
    st.markdown('</div>', unsafe_allow_html=True)

    if audio_bytes:
        with st.spinner("جارٍ تحويل الصوت إلى نص..."):
            text, detected, prob = transcribe_wav_bytes(audio_bytes, language=None)  # auto AR/EN
        if text:
            st.session_state.show_welcome_screen = False
            send_and_stream(text)

# --------------------------- Chat Input (text) ----------------------------------
if prompt := st.chat_input("اكتب رسالتك هنا..."):
    st.session_state.show_welcome_screen = False
    send_and_stream(prompt)
