import os
import shutil
import streamlit as st
from db.database import Database
from docAnalysis.loader import DocumentLoader
from docSplitter.splitter import DocumentSplitter
from docEmbedding.embedding import EmbeddingManager
from docEmbedding.job_manager import job_manager, JobStatus
from config import UPLOAD_DIR, SUPPORTED_EXTENSIONS


def render_knowledge_base_page():
    st.title("知识库管理")

    if "db" not in st.session_state:
        st.session_state.db = Database()
    if "embedding_manager" not in st.session_state:
        st.session_state.embedding_manager = EmbeddingManager()

    db: Database = st.session_state.db
    emb_manager: EmbeddingManager = st.session_state.embedding_manager
    user = st.session_state.user

    if "kb_active_tab" not in st.session_state:
        st.session_state.kb_active_tab = "知识库列表"

    if "kb_created_msg" in st.session_state and st.session_state.kb_created_msg:
        st.toast(st.session_state.kb_created_msg, icon="✅")
        del st.session_state.kb_created_msg

    active_tab = st.radio(
        "选择操作",
        options=["创建知识库", "知识库列表", "上传文件"],
        index=["创建知识库", "知识库列表", "上传文件"].index(st.session_state.kb_active_tab),
        horizontal=True,
        label_visibility="collapsed",
    )

    if active_tab != st.session_state.kb_active_tab:
        st.session_state.kb_active_tab = active_tab
        st.rerun()

    if active_tab == "创建知识库":
        _render_create_tab(db, user)
    elif active_tab == "知识库列表":
        _render_list_tab(db, emb_manager, user)
    elif active_tab == "上传文件":
        _render_upload_tab(db, emb_manager, user)


def _render_create_tab(db: Database, user: dict):
    with st.form("create_kb_form"):
        kb_name = st.text_input("知识库名称")
        kb_description = st.text_area("知识库描述", height=100)
        kb_splitter = st.selectbox(
            "分割方式",
            options=DocumentSplitter.SPLITTER_TYPES,
            index=0,
            format_func=lambda x: {
                "recursive": "递归字符分割（推荐）",
                "character": "字符分割",
                "markdown_header": "Markdown标题分割",
            }.get(x, x),
        )
        col1, col2 = st.columns(2)
        with col1:
            kb_chunk_size = st.number_input("块大小", min_value=100, max_value=2000, value=500, step=50)
        with col2:
            kb_chunk_overlap = st.number_input("块重叠", min_value=0, max_value=500, value=50, step=10)

        submitted = st.form_submit_button("创建知识库")
        if submitted:
            if not kb_name.strip():
                st.error("请输入知识库名称")
            else:
                existing = db.get_knowledge_base_by_name(kb_name.strip())
                if existing:
                    st.error("知识库名称已存在")
                else:
                    kb_id = db.create_knowledge_base(
                        name=kb_name.strip(),
                        user_id=user["id"],
                        description=kb_description,
                        splitter_type=kb_splitter,
                        chunk_size=kb_chunk_size,
                        chunk_overlap=kb_chunk_overlap,
                    )
                    if kb_id:
                        st.session_state.kb_active_tab = "知识库列表"
                        st.session_state.kb_created_msg = f"知识库 '{kb_name.strip()}' 创建成功！"
                        st.rerun()
                    else:
                        st.error("创建失败")


def _render_list_tab(db: Database, emb_manager: EmbeddingManager, user: dict):
    kbs = db.get_knowledge_bases(user_id=user["id"])
    if not kbs:
        st.info("暂无知识库，请先创建")
        return

    search_keyword = st.text_input("🔍 搜索知识库", placeholder="输入关键词搜索...", key="kb_search")

    if search_keyword.strip():
        filtered = [kb for kb in kbs if search_keyword.strip().lower() in kb["name"].lower() or search_keyword.strip().lower() in (kb["description"] or "").lower()]
    else:
        filtered = kbs

    if not filtered:
        st.warning("未找到匹配的知识库")
        return

    for kb in filtered:
        file_count = db.get_kb_file_count(kb["id"])
        vector_count = emb_manager.get_collection_count(kb["name"])

        col_info, col_del = st.columns([10, 1])
        with col_info:
            with st.expander(f"📁 {kb['name']} ({file_count} 个文件, {vector_count} 个向量块)"):
                st.write(f"**描述：** {kb['description'] or '无'}")
                st.write(f"**分割方式：** {kb['splitter_type']}")
                st.write(f"**块大小：** {kb['chunk_size']} | **块重叠：** {kb['chunk_overlap']}")
                st.write(f"**创建时间：** {kb['created_at']}")

                files = db.get_kb_files(kb["id"])
                if files:
                    st.write("**文件列表：**")
                    for f in files:
                        st.write(f"  - {f['file_name']} ({f['file_type']}, {f['chunk_count']} 块)")

        with col_del:
            st.markdown("<div style='height: 30px'></div>", unsafe_allow_html=True)
            if st.button("🗑️", key=f"del_kb_{kb['id']}", help="删除知识库"):
                st.session_state.kb_delete_confirm_id = kb["id"]
                st.session_state.kb_delete_confirm_name = kb["name"]
                st.rerun()

    if "kb_delete_confirm_id" in st.session_state:
        kb_id_to_del = st.session_state.kb_delete_confirm_id
        kb_name_to_del = st.session_state.kb_delete_confirm_name
        st.markdown("---")
        st.warning(f"⚠️ 确定要删除知识库 **「{kb_name_to_del}」** 吗？此操作不可恢复，该知识库下的所有文件和向量数据将被永久删除！")
        col_confirm, col_cancel = st.columns(2)
        with col_confirm:
            if st.button("确认删除", type="primary", key="confirm_del_kb"):
                emb_manager.delete_collection(kb_name_to_del)
                db.delete_knowledge_base(kb_id_to_del)
                del st.session_state.kb_delete_confirm_id
                del st.session_state.kb_delete_confirm_name
                st.toast(f"知识库 '{kb_name_to_del}' 已删除", icon="🗑️")
                st.rerun()
        with col_cancel:
            if st.button("取消", key="cancel_del_kb"):
                del st.session_state.kb_delete_confirm_id
                del st.session_state.kb_delete_confirm_name
                st.rerun()


def _render_upload_tab(db: Database, emb_manager: EmbeddingManager, user: dict):
    kbs = db.get_knowledge_bases(user_id=user["id"])
    if not kbs:
        st.info("请先创建知识库")
        return

    kb_options = {kb["name"]: kb for kb in kbs}
    selected_kb_name = st.selectbox("选择知识库", options=list(kb_options.keys()))

    if not selected_kb_name:
        return

    selected_kb = kb_options[selected_kb_name]

    upload_mode = st.radio("上传方式", options=["上传文件", "指定目录"], horizontal=True)

    if upload_mode == "上传文件":
        st.caption("通过浏览器选择本地文件上传到知识库，支持批量上传")
    else:
        st.caption(
            "💡 指定服务器上的一个目录路径，系统将自动扫描该目录下所有支持的文件并批量导入到知识库。"
            "适用于已有大量文档存放在服务器目录的场景。"
        )

    if upload_mode == "上传文件":
        uploaded_files = st.file_uploader(
            "选择文件",
            accept_multiple_files=True,
            type=list(SUPPORTED_EXTENSIONS.keys()),
        )

        if uploaded_files and st.button("开始处理上传文件"):
            kb_upload_dir = os.path.join(UPLOAD_DIR, selected_kb_name)
            os.makedirs(kb_upload_dir, exist_ok=True)

            with st.spinner("⏳ 正在处理文件，请稍候..."):
                progress = st.progress(0, text="准备处理...")

                total_files = len(uploaded_files)
                all_chunks = []

                for i, uploaded_file in enumerate(uploaded_files):
                    file_path = os.path.join(kb_upload_dir, uploaded_file.name)
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    progress.progress(
                        (i + 1) / total_files,
                        text=f"正在处理: {uploaded_file.name} ({i + 1}/{total_files})"
                    )

                    docs = DocumentLoader.load_file(file_path)
                    if docs:
                        chunks = DocumentSplitter.split(
                            docs,
                            splitter_type=selected_kb["splitter_type"],
                            chunk_size=selected_kb["chunk_size"],
                            chunk_overlap=selected_kb["chunk_overlap"],
                        )
                        all_chunks.extend(chunks)

                        ext = os.path.splitext(uploaded_file.name)[1].lower()
                        file_type = SUPPORTED_EXTENSIONS.get(ext, "unknown")
                        db.add_file_to_kb(
                            kb_id=selected_kb["id"],
                            file_name=uploaded_file.name,
                            file_path=file_path,
                            file_type=file_type,
                            chunk_count=len(chunks),
                        )

                if all_chunks:
                    progress.progress(1.0, text="正在向量化存入ChromaDB...")
                    try:
                        emb_manager.add_documents(all_chunks, selected_kb_name)
                        st.success(f"处理完成！共 {total_files} 个文件，{len(all_chunks)} 个文本块已入库")
                    except RuntimeError as e:
                        st.error(str(e))
                else:
                    st.warning("未提取到有效文档内容")

    else:
        active_job = job_manager.get_active_job(selected_kb["id"])
        latest_job = job_manager.get_latest_job(selected_kb["id"])

        dir_path = st.text_input(
            "输入目录路径",
            placeholder="例如：D:\\documents 或 /home/user/docs",
            help="输入服务器上包含文档的目录绝对路径，系统将递归扫描该目录下所有支持的文件类型（PDF、Word、Excel、TXT、Markdown等）并批量导入",
            key="dir_path_input",
        )

        if active_job:
            st.info(
                f"⏳ 后台正在处理中：{active_job.kb_name} "
                f"({active_job.processed_files}/{active_job.total_files}) "
                f"- {active_job.current_file or '准备中...'}"
            )
            st.progress(
                active_job.processed_files / max(active_job.total_files, 1),
                text=f"{int(active_job.processed_files / max(active_job.total_files, 1) * 100)}%",
            )
            st.caption("💡 您可以切换到其他功能继续操作，处理完成后会自动提示")

        elif latest_job and latest_job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
            if latest_job.status == JobStatus.COMPLETED:
                result = latest_job.result
                st.success(
                    f"✅ 上次处理完成：{result.get('file_count', 0)} 个文件，"
                    f"{result.get('chunk_count', 0)} 个文本块已入库 "
                    f"（{latest_job.finished_at}）"
                )
            else:
                st.error(f"❌ 上次处理失败：{latest_job.error}")
            if st.button("清除历史记录", key="clear_job_history"):
                job_manager.clear_completed_jobs(selected_kb["id"])
                st.rerun()

        elif dir_path:
            if not os.path.isdir(dir_path):
                st.warning("⚠️ 输入的路径不存在或不是有效目录")
            else:
                supported_files = []
                for root, _, files in os.walk(dir_path):
                    for fname in files:
                        ext = os.path.splitext(fname)[1].lower()
                        if ext in SUPPORTED_EXTENSIONS:
                            supported_files.append(os.path.join(root, fname))
                if supported_files:
                    st.info(f"📂 发现 {len(supported_files)} 个支持的文件待处理")
                    with st.expander("查看文件列表"):
                        for f in supported_files:
                            st.write(f"  - {os.path.basename(f)}")

                    col_btn, col_tip = st.columns([1, 4])
                    with col_btn:
                        start_clicked = st.button(
                            "🚀 开始嵌入",
                            type="primary",
                            key="start_dir_embed_btn",
                        )
                    with col_tip:
                        st.caption("点击启动后台线程处理，不影响其他操作")

                    if start_clicked:
                        def _dir_worker(job):
                            kb_upload_dir = os.path.join(UPLOAD_DIR, job.kb_name)
                            os.makedirs(kb_upload_dir, exist_ok=True)

                            file_list = []
                            for root_dir, _, files in os.walk(dir_path):
                                for fname in files:
                                    ext = os.path.splitext(fname)[1].lower()
                                    if ext in SUPPORTED_EXTENSIONS:
                                        file_list.append(os.path.join(root_dir, fname))

                            job.total_files = len(file_list)
                            job_manager.update_progress(job, 0, "扫描完成")

                            worker_db = Database()
                            worker_emb = EmbeddingManager()
                            all_chunks = []

                            for i, file_path in enumerate(file_list):
                                file_name = os.path.basename(file_path)
                                job_manager.update_progress(job, i, file_name)

                                dest_path = os.path.join(kb_upload_dir, file_name)
                                if dest_path != file_path:
                                    shutil.copy2(file_path, dest_path)

                                docs = DocumentLoader.load_file(file_path)
                                if docs:
                                    chunks = DocumentSplitter.split(
                                        docs,
                                        splitter_type=selected_kb["splitter_type"],
                                        chunk_size=selected_kb["chunk_size"],
                                        chunk_overlap=selected_kb["chunk_overlap"],
                                    )
                                    all_chunks.extend(chunks)

                                    ext = os.path.splitext(file_path)[1].lower()
                                    file_type = SUPPORTED_EXTENSIONS.get(ext, "unknown")
                                    worker_db.add_file_to_kb(
                                        kb_id=selected_kb["id"],
                                        file_name=file_name,
                                        file_path=dest_path,
                                        file_type=file_type,
                                        chunk_count=len(chunks),
                                    )

                            if all_chunks:
                                job_manager.update_progress(
                                    job, len(file_list), "正在向量化存入..."
                                )
                                worker_emb.add_documents(all_chunks, job.kb_name)

                            job_manager.update_progress(job, len(file_list), "")
                            job.result = {
                                "file_count": len(file_list),
                                "chunk_count": len(all_chunks),
                            }

                        file_count = len(supported_files)
                        job_manager.start_job(
                            kb_id=selected_kb["id"],
                            kb_name=selected_kb_name,
                            total_files=file_count,
                            worker=_dir_worker,
                        )
                        st.toast(f"🚀 已启动后台嵌入任务，共 {file_count} 个文件", icon="🚀")
                        st.rerun()
                else:
                    st.warning("该目录下没有发现支持的文件类型")
