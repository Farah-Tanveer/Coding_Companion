
import streamlit as st
import starter

from langchain_core.messages import HumanMessage
from llm import agent


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="DevMate | Coding Companion",
    page_icon="💻",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# THEME
# ============================================================

st.markdown(
    """
    <style>
    :root {
        --accent: #8B5CF6;
        --accent-light: #A78BFA;
        --bg-card: rgba(139, 92, 246, 0.08);
        --border: rgba(167, 139, 250, 0.22);
    }

    .stApp {
        background:
            radial-gradient(
                ellipse at top left,
                rgba(91, 60, 170, 0.13),
                transparent 42%
            ),
            var(--background-color);
    }

    [data-testid="stSidebar"] {
        border-right: 1px solid var(--border);
    }

    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1.5rem;
    }

    .brand {
        font-size: 3.2rem !important;
        font-weight: 850 !important;
        letter-spacing: -1.8px !important;
        line-height: 1.2 !important;
        margin-bottom: 0.5rem !important;
        white-space: nowrap;
    }

    .brand span {
        color: #A78BFA !important;
        text-shadow: 0 0 18px rgba(167, 139, 250, 0.25);
    }

    .subtitle {
        color: var(--text-color);
        opacity: 0.68;
        font-size: 0.9rem;
        margin-top: 0.2rem;
    }

    .hero {
        padding: 1.4rem 1.5rem;
        border: 1px solid var(--border);
        border-radius: 20px;
        background: var(--bg-card);
        margin-bottom: 1.2rem;
    }

    .hero h1 {
        font-size: 1.8rem;
        margin: 0 0 0.35rem 0;
        letter-spacing: -0.8px;
    }

    .hero p {
        margin: 0;
        opacity: 0.75;
        font-size: 0.95rem;
    }

    .section-label {
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.3px;
        opacity: 0.65;
        margin: 1.2rem 0 0.6rem 0;
    }

    .workspace-card {
        padding: 0.85rem;
        border: 1px solid var(--border);
        border-radius: 12px;
        background: var(--bg-card);
        overflow-wrap: anywhere;
    }

    .workspace-card code {
        font-size: 0.78rem;
    }

    .feature-card {
        padding: 0.9rem;
        border: 1px solid var(--border);
        border-radius: 14px;
    }

    .feature-title {
        font-weight: 650;
        margin-bottom: 0.3rem;
    }

    .feature-description {
        font-size: 0.85rem;
        opacity: 0.7;
    }

    .stChatMessage {
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.7rem;
    }

    .stChatInput textarea {
        border-radius: 14px;
    }

    div.stButton > button {
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.15s ease-in-out;
    }

    div.stButton > button[kind="primary"] {
        border: 0;
    }

    [data-testid="stMetric"] {
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 0.8rem;
        background: var(--bg-card);
    }

    footer {
        visibility: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SESSION STATE
# ============================================================

DEFAULTS = {
    "chat_history": [],
    "agent_messages": [],
    "pending_prompt": None,
    "notice": None,
    "last_action": "Ready",
    "next_prompt": None,
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# HELPERS
# ============================================================

def message_text(message):
    """Convert a LangChain message into displayable text."""
    content = getattr(message, "content", str(message))

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
            else:
                parts.append(str(item))
        return "\n".join(parts)

    return str(content)


def display_assistant_response(result):
    """Add the final agent response to chat history."""
    messages = result.get("messages", [])

    if not messages:
        return

    response = message_text(messages[-1])

    if response.strip():
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": response,
        })


def finish_approved_action(outcome):
    """Show the confirmed result without invoking the agent again."""
    st.session_state.chat_history.append({
        "role": "assistant",
        "content": outcome,
    })
    st.session_state.pending_prompt = None
    st.session_state.last_action = "Task completed"
    st.session_state.notice = outcome


def process_prompt(prompt):
    """Send a prompt to the agent and handle any pending approval."""
    st.session_state.chat_history.append({
        "role": "user",
        "content": prompt,
    })

    st.session_state.pending_prompt = prompt
    st.session_state.last_action = "Working"
    st.session_state.notice = None

    try:
        with st.spinner("DevMate is working on your request..."):
            result = agent.invoke({
                "messages": (
                    st.session_state.agent_messages
                    + [HumanMessage(content=prompt)]
                )
            })

        st.session_state.agent_messages = result.get("messages", [])

        if starter.PENDING_ACTION is not None:
            st.session_state.last_action = "Waiting for permission"
            # The approval drawer will display on the next rerun.
        else:
            display_assistant_response(result)
            st.session_state.pending_prompt = None
            st.session_state.last_action = "Task completed"

    except Exception as error:
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": (
                "The request failed before completion.\n\n"
                f"**Error:** `{error}`\n\n"
                "No successful change is being reported."
            ),
        })
        st.session_state.last_action = "Error"

        # If a tool staged an action before an error, preserve it
        # for review instead of silently clearing it.


# ============================================================
# PERMISSION DRAWER
# ============================================================

@st.dialog(
    "Review this action",
    position="right",
    dismissible=False,
    width="small",
)
def permission_drawer():
    action = starter.PENDING_ACTION

    if action is None:
        st.info("There is no action awaiting approval.")
        if st.button("Close", use_container_width=True):
            st.rerun()
        return

    action_type = action.get("type", "unknown")
    relative_path = action.get("relative_path", "Unknown file")

    if action_type == "overwrite":
        st.warning("This file already exists.")
        st.markdown("### Overwrite file?")
        st.write("The existing contents will be replaced.")
        button_label = "Allow overwrite"

    elif action_type == "delete":
        st.error("This action deletes a file.")
        st.markdown("### Delete file?")
        st.write("A backup will be saved before deletion.")
        button_label = "Allow deletion"

    else:
        st.error(f"Unsupported pending action: {action_type}")
        if st.button("Cancel action", use_container_width=True):
            outcome = starter.cancel_pending_action()
            st.session_state.notice = outcome
            st.session_state.pending_prompt = None
            st.rerun()
        return

    st.markdown("**Target file**")
    st.code(f"work_dir/{relative_path}", language=None)

    if action_type == "overwrite":
        with st.expander("Preview proposed content"):
            st.code(action.get("content", ""), language="python")

    st.caption("Nothing is changed until you approve this action.")
    st.divider()

    allow_col, cancel_col = st.columns(2)

    with allow_col:
        if st.button(
            button_label,
            type="primary",
            use_container_width=True,
            key="approve_pending_action",
        ):
            if action_type == "overwrite":
                outcome = starter.approve_pending_action()
                success = outcome.startswith(
                    "Overwrite completed successfully:"
                )
            else:
                outcome = starter.approve_delete_action()
                success = outcome.startswith(
                    "File deleted successfully:"
                )

            if success:
                finish_approved_action(outcome)
            else:
                st.session_state.notice = outcome
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": outcome,
                })

            st.rerun()

    with cancel_col:
        if st.button(
            "Cancel",
            use_container_width=True,
            key="cancel_pending_action",
        ):
            outcome = starter.cancel_pending_action()
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": outcome,
            })
            st.session_state.pending_prompt = None
            st.session_state.last_action = "Cancelled"
            st.session_state.notice = outcome
            st.rerun()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown(
        '<p class="brand">Dev<span>Mate</span> ✦</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="subtitle">Your personal coding companion</p>',
        unsafe_allow_html=True,
    )

    st.divider()

    st.markdown(
        '<p class="section-label">Workspace</p>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="workspace-card">
            <strong>📁 work_dir</strong><br><br>
            <code>{starter.WORK_DIR}</code>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<p class="section-label">Session status</p>',
        unsafe_allow_html=True,
    )

    if starter.PENDING_ACTION:
        st.warning("Waiting for your permission")
    else:
        st.success("Ready to help")

    st.caption(f"Last action: {st.session_state.last_action}")
    st.divider()

    st.markdown(
        '<p class="section-label">Quick prompts</p>',
        unsafe_allow_html=True,
    )

    quick_prompts = [
        "List the files in my workspace.",
        "Explain the files in my project.",
        "Create a Python file that prints Hello World.",
        "Run my Python file and show the output.",
    ]

    for index, quick_prompt in enumerate(quick_prompts):
        if st.button(
            quick_prompt,
            key=f"quick_prompt_{index}",
            use_container_width=True,
            disabled=starter.PENDING_ACTION is not None,
        ):
            st.session_state.next_prompt = quick_prompt
            st.rerun()

    st.divider()

    if st.button(
        "＋ New conversation",
        use_container_width=True,
        disabled=starter.PENDING_ACTION is not None,
    ):
        st.session_state.chat_history = []
        st.session_state.agent_messages = []
        st.session_state.pending_prompt = None
        st.session_state.notice = None
        st.session_state.last_action = "Ready"
        st.rerun()

    st.caption("DevMate · AI-powered development workspace")


# ============================================================
# MAIN HEADER
# ============================================================

st.markdown(
    """
    <div class="hero">
        <h1>Build something great. ✨</h1>
        <p>
            Create files, improve your code, explore your workspace,
            and run programs — all from one place.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

metric1, metric2, metric3 = st.columns(3)

with metric1:
    st.metric("Workspace", "Connected")

with metric2:
    st.metric(
        "Permission",
        "Required" if starter.PENDING_ACTION else "On demand",
    )

with metric3:
    st.metric(
        "Assistant",
        "Waiting" if starter.PENDING_ACTION else "Ready",
    )

if st.session_state.notice:
    st.info(st.session_state.notice)


# ============================================================
# CHAT HISTORY
# ============================================================

st.markdown("### Conversation")

if not st.session_state.chat_history:
    st.markdown(
        """
        <div class="feature-card">
            <div class="feature-title">👋 Welcome to DevMate</div>
            <div class="feature-description">
                Ask a question or choose a quick prompt from the sidebar.
                DevMate can inspect files, create code, and execute programs.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

for message in st.session_state.chat_history:
    avatar = "👩‍💻" if message["role"] == "user" else "✨"

    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])


# ============================================================
# CHAT INPUT
# ============================================================

quick_prompt = st.session_state.pop("next_prompt", None)
prompt = None

if starter.PENDING_ACTION is None:
    if quick_prompt:
        prompt = quick_prompt
    else:
        prompt = st.chat_input(
            "Message DevMate... e.g. create and run primes.py"
        )

if prompt:
    process_prompt(prompt)
    st.rerun()


# ============================================================
# APPROVAL DRAWER
# ============================================================

if starter.PENDING_ACTION is not None:
    permission_drawer()
