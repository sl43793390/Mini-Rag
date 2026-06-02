import streamlit as st
from db.database import Database


def render_login_page():
    if "db" not in st.session_state:
        st.session_state.db = Database()

    _, center_col, _ = st.columns([1, 1.2, 1])

    with center_col:
        st.markdown(
            """
            <div style="text-align:center;padding:16px 0 8px 0;">
                <div style="font-size:48px;line-height:1;">🤖</div>
                <div style="font-size:24px;font-weight:600;margin-top:8px;">Mini-Rag</div>
                <div style="color:#888;font-size:13px;margin-top:4px;">RAG 智能问答系统</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tab_login, tab_register = st.tabs(["登录", "注册"])

        with tab_login:
            with st.form("login_form"):
                username = st.text_input("用户名", key="login_username")
                password = st.text_input("密码", type="password", key="login_password")
                submitted = st.form_submit_button("登录", use_container_width=True)

                if submitted:
                    if not username or not password:
                        st.error("请输入用户名和密码")
                    else:
                        user = st.session_state.db.verify_user(username, password)
                        if user:
                            st.session_state.authenticated = True
                            st.session_state.user = user
                            st.success(f"欢迎回来，{username}！")
                            st.rerun()
                        else:
                            st.error("用户名或密码错误")

        with tab_register:
            with st.form("register_form"):
                reg_username = st.text_input("用户名", key="reg_username")
                reg_password = st.text_input("密码", type="password", key="reg_password")
                reg_password_confirm = st.text_input("确认密码", type="password", key="reg_password_confirm")
                reg_submitted = st.form_submit_button("注册", use_container_width=True)

                if reg_submitted:
                    if not reg_username or not reg_password:
                        st.error("请输入用户名和密码")
                    elif reg_password != reg_password_confirm:
                        st.error("两次密码输入不一致")
                    elif len(reg_password) < 6:
                        st.error("密码长度至少6位")
                    else:
                        existing = st.session_state.db.get_user(reg_username)
                        if existing:
                            st.error("用户名已存在")
                        else:
                            success = st.session_state.db.create_user(reg_username, reg_password)
                            if success:
                                st.success("注册成功，请登录")
                            else:
                                st.error("注册失败")
