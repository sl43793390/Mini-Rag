import streamlit as st
from db.database import Database


def render_user_manage_page():
    st.title("用户管理")

    if "db" not in st.session_state:
        st.session_state.db = Database()

    db: Database = st.session_state.db
    user = st.session_state.user

    if user["role"] != "admin":
        st.warning("仅管理员可访问此页面")
        return

    if "user_active_tab" not in st.session_state:
        st.session_state.user_active_tab = "用户列表"

    if "user_created_msg" in st.session_state and st.session_state.user_created_msg:
        st.toast(st.session_state.user_created_msg, icon="✅")
        del st.session_state.user_created_msg

    active_tab = st.radio(
        "选择操作",
        options=["用户列表", "创建用户"],
        index=["用户列表", "创建用户"].index(st.session_state.user_active_tab),
        horizontal=True,
        label_visibility="collapsed",
    )

    if active_tab != st.session_state.user_active_tab:
        st.session_state.user_active_tab = active_tab
        st.rerun()

    if active_tab == "用户列表":
        _render_user_list_tab(db)
    elif active_tab == "创建用户":
        _render_create_user_tab(db)


def _render_user_list_tab(db: Database):
    users = db.get_all_users()
    if not users:
        st.info("暂无用户")
        return

    search_keyword = st.text_input("🔍 搜索用户", placeholder="输入用户名搜索...", key="user_search")

    if search_keyword.strip():
        filtered = [u for u in users if search_keyword.strip().lower() in u["username"].lower()]
    else:
        filtered = users

    if not filtered:
        st.warning("未找到匹配的用户")
        return

    st.write(f"共 {len(filtered)} 个用户")

    for u in filtered:
        col_name, col_role, col_time, col_actions = st.columns([3, 2, 3, 2])
        with col_name:
            st.write(f"**{u['username']}**")
        with col_role:
            role_label = "👑 管理员" if u["role"] == "admin" else "👤 普通用户"
            st.write(role_label)
        with col_time:
            st.write(u["created_at"][:19])
        with col_actions:
            btn_cols = st.columns(2)
            with btn_cols[0]:
                if st.button("🔑", key=f"pwd_user_{u['id']}", help="修改密码"):
                    st.session_state.user_pwd_change_id = u["id"]
                    st.session_state.user_pwd_change_name = u["username"]
                    st.rerun()
            with btn_cols[1]:
                if u["role"] != "admin":
                    if st.button("🗑️", key=f"del_user_{u['id']}", help="删除用户"):
                        st.session_state.user_delete_confirm_id = u["id"]
                        st.session_state.user_delete_confirm_name = u["username"]
                        st.rerun()

    if "user_delete_confirm_id" in st.session_state:
        user_id_to_del = st.session_state.user_delete_confirm_id
        user_name_to_del = st.session_state.user_delete_confirm_name
        st.markdown("---")
        st.warning(f"⚠️ 确定要删除用户 **「{user_name_to_del}」** 吗？此操作不可恢复！")
        col_confirm, col_cancel = st.columns(2)
        with col_confirm:
            if st.button("确认删除", type="primary", key="confirm_del_user"):
                db.delete_user(user_id_to_del)
                del st.session_state.user_delete_confirm_id
                del st.session_state.user_delete_confirm_name
                st.toast(f"用户 '{user_name_to_del}' 已删除", icon="🗑️")
                st.rerun()
        with col_cancel:
            if st.button("取消", key="cancel_del_user"):
                del st.session_state.user_delete_confirm_id
                del st.session_state.user_delete_confirm_name
                st.rerun()

    if "user_pwd_change_id" in st.session_state:
        pwd_user_id = st.session_state.user_pwd_change_id
        pwd_user_name = st.session_state.user_pwd_change_name
        st.markdown("---")
        st.subheader(f"修改密码 - {pwd_user_name}")
        with st.form("change_password_form"):
            new_pwd = st.text_input("新密码", type="password", key="change_new_pwd")
            new_pwd_confirm = st.text_input("确认新密码", type="password", key="change_new_pwd_confirm")
            pwd_submitted = st.form_submit_button("确认修改")
            if pwd_submitted:
                if not new_pwd:
                    st.error("请输入新密码")
                elif len(new_pwd) < 6:
                    st.error("密码长度至少6位")
                elif new_pwd != new_pwd_confirm:
                    st.error("两次密码输入不一致")
                else:
                    db.update_user_password(pwd_user_id, new_pwd)
                    del st.session_state.user_pwd_change_id
                    del st.session_state.user_pwd_change_name
                    st.toast(f"用户 '{pwd_user_name}' 密码修改成功", icon="🔑")
                    st.rerun()

        if st.button("取消修改密码", key="cancel_change_pwd"):
            del st.session_state.user_pwd_change_id
            del st.session_state.user_pwd_change_name
            st.rerun()


def _render_create_user_tab(db: Database):
    with st.form("create_user_form"):
        new_username = st.text_input("用户名")
        new_password = st.text_input("密码", type="password")
        new_password_confirm = st.text_input("确认密码", type="password")
        new_role = st.selectbox("角色", options=["user", "admin"], format_func=lambda x: "管理员" if x == "admin" else "普通用户")

        submitted = st.form_submit_button("创建用户")
        if submitted:
            if not new_username or not new_password:
                st.error("请输入用户名和密码")
            elif new_password != new_password_confirm:
                st.error("两次密码输入不一致")
            elif len(new_password) < 6:
                st.error("密码长度至少6位")
            else:
                existing = db.get_user(new_username)
                if existing:
                    st.error("用户名已存在")
                else:
                    success = db.create_user(new_username, new_password, role=new_role)
                    if success:
                        st.session_state.user_active_tab = "用户列表"
                        st.session_state.user_created_msg = f"用户 '{new_username}' 创建成功"
                        st.rerun()
                    else:
                        st.error("创建失败")
