import json
from pathlib import Path


class Session:
    def __init__(self, creator_slug: str, base_dir: Path = None):
        self.creator_slug = creator_slug
        self.base_dir = Path(base_dir) if base_dir else Path(".")
        self._dir = self.base_dir / ".agent" / creator_slug
        self._session_file = self._dir / "session.json"
        self._learnings_file = self._dir / "learnings.json"
        self._state: dict = {}
        self.learnings: list = []
        self._load()

    def _load(self):
        if self._session_file.exists():
            self._state = json.loads(self._session_file.read_text(encoding="utf-8"))
        if self._learnings_file.exists():
            self.learnings = json.loads(self._learnings_file.read_text(encoding="utf-8"))

    def get(self, key: str, default=None):
        return self._state.get(key, default)

    def set(self, key: str, value):
        self._state[key] = value

    def append_learning(self, entry: dict):
        self.learnings.append(entry)

    def save(self):
        self._dir.mkdir(parents=True, exist_ok=True)
        self._session_file.write_text(
            json.dumps(self._state, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        self._learnings_file.write_text(
            json.dumps(self.learnings, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def save_brief_json(self, brief: dict):
        self._dir.mkdir(parents=True, exist_ok=True)
        path = self._dir / "positioning-brief.json"
        path.write_text(json.dumps(brief, indent=2, ensure_ascii=False), encoding="utf-8")
