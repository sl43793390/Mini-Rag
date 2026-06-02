import streamlit as st
from db.database import Database
from ui.login import render_login_page
from ui.knowledge_base import render_knowledge_base_page
from ui.chat import render_chat_page
from ui.user_manage import render_user_manage_page


def init_session_state():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None
    if "db" not in st.session_state:
        st.session_state.db = Database()


def main():
    st.set_page_config(
        page_title="Mini-RAG",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_session_state()

    if not st.session_state.authenticated:
        render_login_page()
        return

    user = st.session_state.user

    with st.sidebar:
        st.markdown(
            """
            <div style="display:flex;align-items:center;gap:8px;">
                <span style="font-size:28px;font-weight:600;margin-top: -80px;line-height:1;">Mini-Rag</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.divider()
        st.write(f"👤 **{user['username']}**")
        role_label = "管理员" if user["role"] == "admin" else "普通用户"
        st.write(f"角色: {role_label}")

        page = st.radio(
            "导航",
            options=["RAG 问答", "知识库管理", "用户管理"] if user["role"] == "admin" else ["RAG 问答", "知识库管理"],
            key="page_nav",
        )

        st.divider()
        if st.button("退出登录"):
            keys_to_remove = [k for k in st.session_state if k.startswith("chat_history_")]
            for k in keys_to_remove:
                del st.session_state[k]
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()

    if page == "RAG 问答":
        render_chat_page()
    elif page == "知识库管理":
        render_knowledge_base_page()
    elif page == "用户管理":
        render_user_manage_page()


if __name__ == "__main__":
    main()
