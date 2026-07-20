"""
Progress tracking service for long-running analysis pipeline.
Uses in-memory state to support SSE streaming of progress events.
"""
import logging
import threading
from collections import defaultdict
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class ProgressEvent:
    def __init__(self, run_id: int, stage: str, status: str, message: str = "",
                 progress: float = 0.0, data: Optional[Dict] = None):
        self.run_id = run_id
        self.stage = stage
        self.status = status  # "started" | "in_progress" | "completed" | "failed"
        self.message = message
        self.progress = progress  # 0.0 - 1.0
        self.data = data or {}
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "stage": self.stage,
            "status": self.status,
            "message": self.message,
            "progress": round(self.progress, 3),
            "data": self.data,
            "timestamp": self.timestamp,
        }


class ProgressService:
    def __init__(self):
        self._events: Dict[int, List[ProgressEvent]] = defaultdict(list)
        self._locks: Dict[int, threading.Lock] = defaultdict(threading.Lock)
        self._completed: Dict[int, bool] = {}
        self._cursors: Dict[int, int] = defaultdict(int)

    def emit(self, run_id: int, stage: str, status: str, message: str = "",
             progress: float = 0.0, data: Optional[Dict] = None):
        event = ProgressEvent(run_id, stage, status, message, progress, data)
        with self._locks[run_id]:
            self._events[run_id].append(event)
            if status in ("completed", "failed"):
                self._completed[run_id] = True
        logger.info(f"[Run {run_id}] [{stage}] {status} ({progress:.0%}): {message}")

    def get_events_since(self, run_id: int, cursor: int = 0) -> tuple:
        with self._locks[run_id]:
            events = self._events[run_id][cursor:]
            new_cursor = cursor + len(events)
            is_done = self._completed.get(run_id, False)
        return [e.to_dict() for e in events], new_cursor, is_done

    def get_all_events(self, run_id: int) -> List[Dict]:
        with self._locks[run_id]:
            return [e.to_dict() for e in self._events[run_id]]

    def is_completed(self, run_id: int) -> bool:
        return self._completed.get(run_id, False)

    def clear(self, run_id: int):
        with self._locks[run_id]:
            self._events.pop(run_id, None)
            self._completed.pop(run_id, None)
            self._cursors.pop(run_id, None)


progress_service = ProgressService()


# Analysis stage definitions (ordered)
ANALYSIS_STAGES = [
    ("collection", "数据采集", "Collecting reviews from App Store"),
    ("cleaning", "评论清洗", "Cleaning and deduplicating reviews"),
    ("vector_index", "向量索引", "Building vector index for evidence retrieval"),
    ("topic_extraction", "主题发现", "Extracting topics via LLM"),
    ("finding_generation", "问题发现", "Generating findings via LLM"),
    ("evidence_validation", "证据验证", "Validating findings with vector search"),
    ("prd_generation", "PRD 生成", "Generating product requirements"),
    ("version_planning", "版本规划", "Planning release versions"),
    ("testcase_generation", "测试用例", "Generating test cases"),
    ("traceability", "追溯链", "Building traceability chain"),
]
