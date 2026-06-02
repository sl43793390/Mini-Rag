import json
import streamlit as st
from db.database import Database
from docEmbedding.embedding import EmbeddingManager

_CHAT_CSS = """
<style>
[data-testid="stChatMessage"] {
    padding: 4px 8px !important;
    gap: 2px !important;
    align-items: flex-start !important;
}
[data-testid="stChatMessageAvatar"] {
    width: 36px !important;
    height: 36px !important;
    border-radius: 6px !important;
    font-size: 22px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
.msg-role-marker {
    display: none !important;
}
[data-testid="stChatMessage"]:has(.assistant-marker) [data-testid="stChatMessageAvatar"] {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    border-radius: 6px !important;
}
[data-testid="stChatMessage"]:has(.user-marker) [data-testid="stChatMessageAvatar"] {
    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%) !important;
    border-radius: 6px !important;
}
[data-testid="stChatMessage"]:has(.assistant-marker) [data-testid="stChatMessageContent"] {
    background-color: #ffffff !important;
    border: 1px solid #e0e0e0 !important;
    border-radius: 12px !important;
    border-top-left-radius: 2px !important;
    padding: 10px 14px !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
    max-width: 75% !important;
    margin-left: 20px !important;
}
[data-testid="stChatMessage"]:has(.user-marker) {
    flex-direction: row-reverse !important;
}
[data-testid="stChatMessage"]:has(.user-marker) [data-testid="stChatMessageContent"] {
    background: linear-gradient(135deg, #95ec69 0%, #7ed957 100%) !important;
    border-radius: 12px !important;
    border-top-right-radius: 2px !important;
    padding: 10px 14px !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
    max-width: 75% !important;
    margin-right: 20px !important;
}
[data-testid="stChatMessage"]:has(.user-marker) [data-testid="stChatMessageContent"] p,
[data-testid="stChatMessage"]:has(.user-marker) [data-testid="stChatMessageContent"] li {
    color: #000 !important;
}
</style>
"""


def _render_message(role: str, content: str, sources: list = None):
    marker_class = "user-marker" if role == "user" else "assistant-marker"
    avatar = "👤" if role == "user" else "🤖"

    with st.chat_message(role, avatar=avatar):
        st.markdown(f'<span class="msg-role-marker {marker_class}"></span>', unsafe_allow_html=True)
        st.markdown(content)
        if role == "assistant" and sources:
            with st.expander("📎 查看引用来源"):
                for j, source in enumerate(sources):
                    st.write(f"**来源 {j + 1}:** {source}")


def render_chat_page():
    st.title("RAG 智能问答")

    if "db" not in st.session_state:
        st.session_state.db = Database()
    if "embedding_manager" not in st.session_state:
        st.session_state.embedding_manager = EmbeddingManager()

    db: Database = st.session_state.db
    emb_manager: EmbeddingManager = st.session_state.embedding_manager
    user = st.session_state.user

    kbs = db.get_knowledge_bases(user_id=user["id"])
    if not kbs:
        st.info("暂无知识库，请先在知识库管理页面创建并上传文件")
        return

    kb_options = {kb["name"]: kb for kb in kbs}
    kb_names = list(kb_options.keys())

    last_kb = db.get_last_kb_name(user["id"])
    if last_kb and last_kb in kb_names:
        default_index = kb_names.index(last_kb)
    else:
        default_index = 0

    with st.sidebar:
        st.subheader("会话设置")
        selected_kb_name = st.selectbox("选择知识库", options=kb_names, index=default_index)

        if selected_kb_name:
            selected_kb = kb_options[selected_kb_name]
            vector_count = emb_manager.get_collection_count(selected_kb_name)
            file_count = db.get_kb_file_count(selected_kb["id"])
            st.info(f"知识库: {selected_kb_name}\n\n文件数: {file_count}\n向量块数: {vector_count}")

        top_k = st.slider("检索文档数", min_value=1, max_value=10, value=4)

        if st.button("清空对话历史"):
            if selected_kb_name:
                db.clear_chat_history(user["id"], selected_kb_name)
            st.session_state.pop(f"chat_history_{selected_kb_name}", None)
            st.rerun()

    if not selected_kb_name:
        st.warning("请选择一个知识库")
        return

    chat_key = f"chat_history_{selected_kb_name}"
    if chat_key not in st.session_state:
        db_messages = db.get_chat_history(user["id"], selected_kb_name)
        if db_messages:
            st.session_state[chat_key] = []
            for msg in db_messages:
                entry = {"role": msg["role"], "content": msg["content"]}
                if msg["role"] == "assistant" and msg["sources"]:
                    try:
                        entry["sources"] = json.loads(msg["sources"])
                    except (json.JSONDecodeError, TypeError):
                        entry["sources"] = [msg["sources"]] if msg["sources"] else []
                st.session_state[chat_key].append(entry)
        else:
            st.session_state[chat_key] = []

    chat_history = st.session_state[chat_key]

    st.markdown(_CHAT_CSS, unsafe_allow_html=True)

    for msg in chat_history:
        sources = msg.get("sources", [])
        _render_message(msg["role"], msg["content"], sources if sources else None)

    if prompt := st.chat_input("请输入您的问题..."):
        chat_history.append({"role": "user", "content": prompt})
        db.add_chat_message(
            user_id=user["id"],
            kb_name=selected_kb_name,
            role="user",
            content=prompt,
        )

        _render_message("user", prompt)

        try:
            answer_parts = []
            with st.spinner("🔍 正在检索相关文档..."):
                docs = emb_manager.query(
                    question=prompt,
                    collection_name=selected_kb_name,
                    top_k=top_k,
                )

                sources = []
                for doc in docs:
                    source_info = f"{doc.metadata.get('file_name', '未知文件')}"
                    page = doc.metadata.get("page")
                    if page is not None:
                        source_info += f" (第{page}页)"
                    sources.append(source_info)

            with st.chat_message("assistant", avatar="🤖"):
                st.markdown('<span class="msg-role-marker assistant-marker"></span>', unsafe_allow_html=True)
                response_placeholder = st.empty()

                for chunk in emb_manager.stream_generate_answer(
                    question=prompt,
                    documents=docs,
                ):
                    answer_parts.append(chunk)
                    response_placeholder.markdown("".join(answer_parts))

                if sources:
                    st.markdown("---")
                    st.caption("📎 引用来源")
                    for j, source in enumerate(sources):
                        st.write(f"**来源 {j + 1}:** {source}")

            answer = "".join(answer_parts)

            assistant_entry = {
                "role": "assistant",
                "content": answer,
                "sources": sources,
            }
            chat_history.append(assistant_entry)

            db.add_chat_message(
                user_id=user["id"],
                kb_name=selected_kb_name,
                role="assistant",
                content=answer,
                sources=json.dumps(sources, ensure_ascii=False),
            )

        except Exception as e:
            error_msg = f"生成回答时出错: {str(e)}"
            st.error(error_msg)
            chat_history.append({
                "role": "assistant",
                "content": error_msg,
            })
            db.add_chat_message(
                user_id=user["id"],
                kb_name=selected_kb_name,
                role="assistant",
                content=error_msg,
            )
