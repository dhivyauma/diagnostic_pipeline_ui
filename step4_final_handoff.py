from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import streamlit as st
from step4_json_store import Step4JSONStore


@dataclass(frozen=True)
class FinalContract:
    header: Dict[str, Any]
    user_specs: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "header": self.header,
            "user_specs": self.user_specs,
        }


class FinalHandoffManager:
    def __init__(
        self,
        output_dir: Optional[Path] = None,
        db_path: Optional[Path] = None,
    ) -> None:
        base_dir = Path(__file__).resolve().parent
        self.output_dir = output_dir or (base_dir / "outputs")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = db_path or (self.output_dir / "diagnostic_results.db")
        self._init_db()

    def compile_final_json(self, header: Dict[str, Any], user_specs: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(header, dict):
            raise TypeError("header must be a dict")
        if not isinstance(user_specs, dict):
            raise TypeError("user_specs must be a dict")

        required_header_keys = ["model_type", "portfolio", "purpose"]
        missing = [k for k in required_header_keys if not header.get(k)]
        if missing:
            raise ValueError(f"Missing required header fields: {missing}")

        contract = FinalContract(header=header, user_specs=user_specs)
        return contract.to_dict()

    def save_final_json(self, final_json: Dict[str, Any], filename: Optional[str] = None) -> str:
        if not isinstance(final_json, dict):
            raise TypeError("final_json must be a dict")

        header = final_json.get("header") or {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if filename is None:
            model_type = str(header.get("model_type", "UNKNOWN")).replace(" ", "_")
            portfolio = str(header.get("portfolio", "UNKNOWN")).replace(" ", "_")
            purpose = str(header.get("purpose", "UNKNOWN")).replace(" ", "_")
            filename = f"final_contract_{model_type}_{portfolio}_{purpose}_{timestamp}.json"

        path = self.output_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(final_json, f, indent=2, ensure_ascii=False)

        return str(path)

    def generate_modeling_script(self, final_json: Dict[str, Any]) -> str:
        final_json_str = json.dumps(final_json, indent=2, ensure_ascii=False)
        base_dir = Path(__file__).resolve().parent
        return (
            "import json\n"
            "from pathlib import Path\n\n"
            "CONTRACT = "
            + repr(final_json_str)
            + "\n\n"
            "def load_contract() -> dict:\n"
            "    return json.loads(CONTRACT)\n\n"
            "def run_model(contract: dict) -> dict:\n"
            "    header = contract.get('header', {})\n"
            "    user_specs = contract.get('user_specs', {})\n"
            "    return {\n"
            "        'status': 'success',\n"
            "        'echo': {\n"
            "            'header': header,\n"
            "            'user_specs': user_specs,\n"
            "        }\n"
            "    }\n\n"
            "if __name__ == '__main__':\n"
            "    contract = load_contract()\n"
            "    results = run_model(contract)\n"
            f"    out_dir = Path({repr(str(base_dir / 'outputs'))})\n"
            "    out_dir.mkdir(parents=True, exist_ok=True)\n"
            "    out_file = out_dir / 'model_results.json'\n"
            "    out_file.write_text(json.dumps(results, indent=2), encoding='utf-8')\n"
            "    print(f'Wrote results to: {out_file}')\n"
        )

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    header_json TEXT NOT NULL,
                    user_specs_json TEXT NOT NULL,
                    execution_status TEXT NOT NULL,
                    execution_result_json TEXT
                )
                """
            )
            conn.commit()

    def save_execution_results(self, final_json: Dict[str, Any], execution_result: Dict[str, Any]) -> int:
        header_json = json.dumps(final_json.get("header", {}), ensure_ascii=False)
        user_specs_json = json.dumps(final_json.get("user_specs", {}), ensure_ascii=False)

        status = "unknown"
        if isinstance(execution_result, dict):
            status = str(execution_result.get("status", status))

        execution_result_json = json.dumps(execution_result, ensure_ascii=False)
        timestamp = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO executions (timestamp, header_json, user_specs_json, execution_status, execution_result_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (timestamp, header_json, user_specs_json, status, execution_result_json),
            )
            conn.commit()
            return int(cur.lastrowid)

    def get_execution_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id, timestamp, execution_status
                FROM executions
                ORDER BY id DESC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()

        return [dict(r) for r in rows]

    def download_results(self, record_id: int) -> Optional[str]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT id, timestamp, header_json, user_specs_json, execution_status, execution_result_json
                FROM executions
                WHERE id = ?
                """,
                (int(record_id),),
            ).fetchone()

        if row is None:
            return None

        payload = {
            "id": row["id"],
            "timestamp": row["timestamp"],
            "execution_status": row["execution_status"],
            "contract": {
                "header": json.loads(row["header_json"]),
                "user_specs": json.loads(row["user_specs_json"]),
            },
            "execution_result": json.loads(row["execution_result_json"]) if row["execution_result_json"] else None,
        }

        return json.dumps(payload, indent=2, ensure_ascii=False)


def create_step4_ui(manager: FinalHandoffManager) -> None:
    st.markdown("---")
    st.subheader("Step 4 - Final Handoff")

    json_store = Step4JSONStore()
    draft = json_store.load()
    if not draft:
        st.warning(f"No draft found yet at: {json_store.filepath}")
        return

    st.caption(f"Draft path: {json_store.filepath}")

    header = draft.get("header", {})
    user_specs = draft.get("user_specs", {})
    meta = draft.get("meta")

    final_json = manager.compile_final_json(header, user_specs)
    if meta is not None:
        final_json["meta"] = meta

    st.markdown("### Final Contract JSON")
    st.json(final_json)

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Save Final JSON", type="primary"):
            try:
                path = manager.save_final_json(final_json)
                st.success(f"Saved: {path}")
            except Exception as e:
                st.error(str(e))

    with col2:
        st.download_button(
            label="Download Final JSON",
            data=json.dumps(final_json, indent=2, ensure_ascii=False),
            file_name=f"final_contract_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
        )

    st.markdown("### Execution History")
    history = manager.get_execution_history(limit=10)
    if history:
        st.dataframe(history, use_container_width=True)
    else:
        st.info("No executions saved yet.")
