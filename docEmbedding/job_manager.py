import json
import os
import threading
import time
import traceback
from datetime import datetime
from typing import Callable, Dict, Optional


JOB_STATE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "embedding_jobs.json",
)


class JobStatus:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class EmbeddingJob:
    def __init__(
        self,
        job_id: str,
        kb_name: str,
        kb_id: int,
        total_files: int,
    ):
        self.job_id = job_id
        self.kb_name = kb_name
        self.kb_id = kb_id
        self.total_files = total_files
        self.processed_files = 0
        self.current_file = ""
        self.status = JobStatus.PENDING
        self.error = ""
        self.created_at = datetime.now().isoformat()
        self.finished_at = ""
        self.result = {}

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "kb_name": self.kb_name,
            "kb_id": self.kb_id,
            "total_files": self.total_files,
            "processed_files": self.processed_files,
            "current_file": self.current_file,
            "status": self.status,
            "error": self.error,
            "created_at": self.created_at,
            "finished_at": self.finished_at,
            "result": self.result,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EmbeddingJob":
        job = cls(
            job_id=d["job_id"],
            kb_name=d["kb_name"],
            kb_id=d["kb_id"],
            total_files=d["total_files"],
        )
        job.processed_files = d.get("processed_files", 0)
        job.current_file = d.get("current_file", "")
        job.status = d.get("status", JobStatus.PENDING)
        job.error = d.get("error", "")
        job.created_at = d.get("created_at", "")
        job.finished_at = d.get("finished_at", "")
        job.result = d.get("result", {})
        return job


class JobManager:
    _instance: Optional["JobManager"] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._jobs: Dict[str, EmbeddingJob] = {}
                    cls._instance._threads: Dict[str, threading.Thread] = {}
                    cls._instance._file_lock = threading.Lock()
                    cls._instance._load_from_disk()
        return cls._instance

    def _load_from_disk(self):
        if not os.path.exists(JOB_STATE_FILE):
            return
        try:
            with open(JOB_STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for job_dict in data.get("jobs", []):
                job = EmbeddingJob.from_dict(job_dict)
                if job.status in (JobStatus.RUNNING, JobStatus.PENDING):
                    job.status = JobStatus.FAILED
                    job.error = "服务重启导致任务中断"
                    job.finished_at = datetime.now().isoformat()
                self._jobs[job.job_id] = job
            self._save_to_disk()
        except Exception as e:
            print(f"[JobManager] 加载任务状态失败: {e}")

    def _save_to_disk(self):
        try:
            os.makedirs(os.path.dirname(JOB_STATE_FILE), exist_ok=True)
            with self._file_lock:
                with open(JOB_STATE_FILE, "w", encoding="utf-8") as f:
                    json.dump(
                        {"jobs": [job.to_dict() for job in self._jobs.values()]},
                        f,
                        ensure_ascii=False,
                        indent=2,
                    )
        except Exception as e:
            print(f"[JobManager] 保存任务状态失败: {e}")

    def get_job(self, job_id: str) -> Optional[EmbeddingJob]:
        return self._jobs.get(job_id)

    def get_jobs_by_kb(self, kb_id: int) -> list:
        return [job for job in self._jobs.values() if job.kb_id == kb_id]

    def get_active_job(self, kb_id: int) -> Optional[EmbeddingJob]:
        for job in self._jobs.values():
            if job.kb_id == kb_id and job.status in (JobStatus.RUNNING, JobStatus.PENDING):
                return job
        return None

    def get_latest_job(self, kb_id: int) -> Optional[EmbeddingJob]:
        jobs = self.get_jobs_by_kb(kb_id)
        if not jobs:
            return None
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)[0]

    def start_job(
        self,
        kb_id: int,
        kb_name: str,
        total_files: int,
        worker: Callable[[EmbeddingJob], None],
    ) -> EmbeddingJob:
        job_id = f"job_{int(time.time() * 1000)}_{kb_id}"
        job = EmbeddingJob(
            job_id=job_id,
            kb_name=kb_name,
            kb_id=kb_id,
            total_files=total_files,
        )
        job.status = JobStatus.RUNNING
        self._jobs[job_id] = job
        self._save_to_disk()

        def run():
            try:
                worker(job)
                if job.status == JobStatus.RUNNING:
                    job.status = JobStatus.COMPLETED
                    job.finished_at = datetime.now().isoformat()
            except Exception as e:
                job.status = JobStatus.FAILED
                job.error = f"{type(e).__name__}: {str(e)}"
                job.finished_at = datetime.now().isoformat()
                print(f"[JobManager] 任务 {job_id} 失败: {e}")
                traceback.print_exc()
            finally:
                self._save_to_disk()
                if job_id in self._threads:
                    del self._threads[job_id]

        thread = threading.Thread(target=run, daemon=True, name=f"EmbeddingJob-{job_id}")
        self._threads[job_id] = thread
        thread.start()
        return job

    def update_progress(
        self,
        job: EmbeddingJob,
        processed: int,
        current_file: str = "",
    ):
        job.processed_files = processed
        if current_file:
            job.current_file = current_file
        self._save_to_disk()

    def clear_completed_jobs(self, kb_id: Optional[int] = None):
        for job_id, job in list(self._jobs.items()):
            if job.status not in (JobStatus.RUNNING, JobStatus.PENDING):
                if kb_id is None or job.kb_id == kb_id:
                    del self._jobs[job_id]
        self._save_to_disk()


job_manager = JobManager()
