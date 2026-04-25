from __future__ import annotations

import hashlib
from pathlib import Path


def storage_root() -> Path:
    from app import config

    root = Path(config.INTAKE_STORAGE_DIR)
    root.mkdir(parents=True, exist_ok=True)
    return root


def job_dir(job_id: str) -> Path:
    d = storage_root() / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_bytes(rel_path: str, data: bytes) -> None:
    path = storage_root() / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def read_bytes(rel_path: str) -> bytes:
    return (storage_root() / rel_path).read_bytes()


def delete_job_files(job_id: str) -> None:
    d = storage_root() / job_id
    if d.is_dir():
        for p in sorted(d.rglob("*"), reverse=True):
            if p.is_file():
                p.unlink()
        try:
            d.rmdir()
        except OSError:
            for sub in sorted(d.rglob("*"), reverse=True):
                if sub.is_dir():
                    try:
                        sub.rmdir()
                    except OSError:
                        pass
            try:
                d.rmdir()
            except OSError:
                pass
