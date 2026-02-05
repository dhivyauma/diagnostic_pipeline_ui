import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class Step4JSONStore:
    def __init__(self, output_dir: str = "outputs", filename: str = "diagnostic_draft.json") -> None:
        base_dir = Path(__file__).resolve().parent
        self.output_dir = base_dir / output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.filepath = self.output_dir / filename

    def load(self) -> Dict[str, Any]:
        if self.filepath.exists():
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        return {}

    def save(self, data: Dict[str, Any], completion_status: Optional[Dict[str, Any]] = None) -> None:
        meta: Dict[str, Any] = {
            "last_updated": datetime.now().isoformat(),
        }
        if completion_status is not None:
            mandatory_complete = bool(completion_status.get("all_mandatory_complete", False))
            meta["completion_status"] = {
                "mandatory_complete": mandatory_complete,
            }

        data["meta"] = meta

        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def upsert_field(
        self,
        header: Dict[str, Any],
        field: str,
        value: Any,
        completion_status: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        draft = self.load()

        draft.setdefault("header", {})
        if isinstance(draft["header"], dict):
            draft["header"].update(header)
        else:
            draft["header"] = dict(header)

        draft.setdefault("user_specs", {})
        if not isinstance(draft["user_specs"], dict):
            draft["user_specs"] = {}
        draft["user_specs"][field] = value

        self.save(draft, completion_status=completion_status)
        return draft
