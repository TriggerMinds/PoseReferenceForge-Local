"""Pose library with SQLite persistence, thumbnails, and search."""
import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Any

from app.domain.models import Pose3D, JointState
from app.persistence.project_repository import ProjectRepository
from app.config.settings import Settings


class PoseLibrary:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = Settings.get().get_val("library_db", "")
        if not db_path:
            db_path = str(Path.home() / "PoseReferenceForge" / "library.db")
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._repo = ProjectRepository()

    def _init_db(self):
        conn = sqlite3.connect(self._db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS poses (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                tags TEXT DEFAULT '',
                category TEXT DEFAULT '',
                favorite INTEGER DEFAULT 0,
                created TEXT NOT NULL,
                modified TEXT NOT NULL,
                pose3d TEXT NOT NULL,
                thumbnail BLOB,
                notes TEXT DEFAULT '',
                hands_visible INTEGER DEFAULT 0,
                feet_visible INTEGER DEFAULT 0,
                manually_corrected INTEGER DEFAULT 0,
                camera_available INTEGER DEFAULT 0,
                orientation TEXT DEFAULT '',
                source_image_hash TEXT DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_poses_name ON poses(name)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_poses_tags ON poses(tags)
        """)
        conn.commit()
        conn.close()

    def _generate_id(self) -> str:
        return hashlib.sha256(
            f"{datetime.now().isoformat()}{id(self)}".encode()
        ).hexdigest()[:16]

    def save(self, name: str, pose3d: Pose3D, tags: str = "", category: str = "",
             notes: str = "", source_hash: str = "", orientation: str = "") -> str:
        pose_id = self._generate_id()
        now = datetime.now().isoformat()
        pose_data = self._repo.serialize_pose3d(pose3d)
        pose_json = json.dumps(pose_data)

        manually_corrected = any(
            j.state in (JointState.MANUALLY_CORRECTED, JointState.LOCKED)
            for j in pose3d.joints.values()
        )
        hands_visible = all(
            pose3d.joints.get(h) is not None
            for h in ("left_hand", "right_hand")
        )
        feet_visible = all(
            pose3d.joints.get(f) is not None
            for f in ("left_foot", "right_foot")
        )

        conn = sqlite3.connect(self._db_path)
        conn.execute(
            "INSERT OR REPLACE INTO poses VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                pose_id, name, tags, category, 0, now, now,
                pose_json, None, notes,
                int(hands_visible), int(feet_visible),
                int(manually_corrected), 0, orientation, source_hash,
            ),
        )
        conn.commit()
        conn.close()
        return pose_id

    def load(self, pose_id: str) -> Optional[Pose3D]:
        conn = sqlite3.connect(self._db_path)
        row = conn.execute(
            "SELECT pose3d FROM poses WHERE id = ?", (pose_id,)
        ).fetchone()
        conn.close()
        if row is None:
            return None
        return self._repo.deserialize_pose3d(json.loads(row[0]))

    def delete(self, pose_id: str) -> bool:
        conn = sqlite3.connect(self._db_path)
        c = conn.execute("DELETE FROM poses WHERE id = ?", (pose_id,))
        conn.commit()
        conn.close()
        return c.rowcount > 0

    def rename(self, pose_id: str, new_name: str) -> bool:
        conn = sqlite3.connect(self._db_path)
        now = datetime.now().isoformat()
        c = conn.execute(
            "UPDATE poses SET name = ?, modified = ? WHERE id = ?",
            (new_name, now, pose_id),
        )
        conn.commit()
        conn.close()
        return c.rowcount > 0

    def list_all(self) -> list[dict[str, Any]]:
        conn = sqlite3.connect(self._db_path)
        rows = conn.execute(
            "SELECT id, name, tags, category, favorite, created, modified, "
            "hands_visible, feet_visible, manually_corrected, camera_available, "
            "orientation, notes FROM poses ORDER BY modified DESC"
        ).fetchall()
        conn.close()
        return [
            {
                "id": r[0], "name": r[1], "tags": r[2],
                "category": r[3], "favorite": bool(r[4]),
                "created": r[5], "modified": r[6],
                "hands_visible": bool(r[7]), "feet_visible": bool(r[8]),
                "manually_corrected": bool(r[9]),
                "camera_available": bool(r[10]),
                "orientation": r[11] or "", "notes": r[12] or "",
            }
            for r in rows
        ]

    def search(self, query: str = "") -> list[dict[str, Any]]:
        conn = sqlite3.connect(self._db_path)
        if query:
            like = f"%{query}%"
            rows = conn.execute(
                "SELECT id, name, tags, category, favorite, created, modified, "
                "hands_visible, feet_visible, manually_corrected, camera_available, "
                "orientation, notes FROM poses "
                "WHERE name LIKE ? OR tags LIKE ? OR notes LIKE ? "
                "ORDER BY modified DESC",
                (like, like, like),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, name, tags, category, favorite, created, modified, "
                "hands_visible, feet_visible, manually_corrected, camera_available, "
                "orientation, notes FROM poses ORDER BY modified DESC"
            ).fetchall()
        conn.close()
        return [
            {
                "id": r[0], "name": r[1], "tags": r[2],
                "category": r[3], "favorite": bool(r[4]),
                "created": r[5], "modified": r[6],
                "hands_visible": bool(r[7]), "feet_visible": bool(r[8]),
                "manually_corrected": bool(r[9]),
                "camera_available": bool(r[10]),
                "orientation": r[11] or "", "notes": r[12] or "",
            }
            for r in rows
        ]

    def toggle_favorite(self, pose_id: str) -> bool:
        conn = sqlite3.connect(self._db_path)
        current = conn.execute(
            "SELECT favorite FROM poses WHERE id = ?", (pose_id,)
        ).fetchone()
        if current is None:
            conn.close()
            return False
        new_val = 0 if current[0] else 1
        conn.execute("UPDATE poses SET favorite = ? WHERE id = ?", (new_val, pose_id))
        conn.commit()
        conn.close()
        return True

    def export_pose(self, pose_id: str, path: str):
        pose = self.load(pose_id)
        if pose is None:
            raise FileNotFoundError(f"Pose not found: {pose_id}")
        data = self._repo.serialize_pose3d(pose)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def import_pose(self, path: str, name: str = "", tags: str = "") -> str:
        with open(path) as f:
            data = json.load(f)
        pose3d = self._repo.deserialize_pose3d(data)
        if not name:
            name = Path(path).stem
        return self.save(name=name, pose3d=pose3d, tags=tags)

    def duplicate(self, pose_id: str, new_name: str = "") -> Optional[str]:
        conn = sqlite3.connect(self._db_path)
        row = conn.execute(
            "SELECT name, tags, category, pose3d, notes, orientation, source_image_hash "
            "FROM poses WHERE id = ?", (pose_id,)
        ).fetchone()
        conn.close()
        if row is None:
            return None
        name = new_name or f"{row[0]} (copy)"
        now = datetime.now().isoformat()
        new_id = self._generate_id()
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            "INSERT INTO poses VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (new_id, name, row[1], row[2], 0, now, now, row[3], None, row[4],
             0, 0, 0, 0, row[5], row[6]),
        )
        conn.commit()
        conn.close()
        return new_id
