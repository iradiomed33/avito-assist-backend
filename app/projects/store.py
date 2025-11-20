import json
import os
import threading
from typing import Dict, List, Optional

from .models import Project


class ProjectStore:
    """
    Простое файловое хранилище проектов.
    В MVP храним всё в data/projects.json.
    """

    def __init__(self, path: str = "data/projects.json") -> None:
        self.path = path
        self._lock = threading.Lock()

    def _load_all(self) -> Dict[str, dict]:
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_all(self, data: Dict[str, dict]) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp_path = f"{self.path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.path)

    def list_projects(self) -> List[Project]:
        with self._lock:
            raw = self._load_all()
            return [Project(**p) for p in raw.values()]

    def get_project(self, project_id: str) -> Optional[Project]:
        with self._lock:
            raw = self._load_all()
            data = raw.get(project_id)
            if not data:
                return None
            return Project(**data)

    def upsert_project(self, project: Project) -> None:
        with self._lock:
            raw = self._load_all()
            raw[project.id] = project.model_dump()
            self._save_all(raw)
