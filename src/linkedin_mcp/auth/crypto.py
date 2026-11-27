"""Encryption helpers for protecting session state at rest."""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet, InvalidToken

from linkedin_mcp.config import config

logger = logging.getLogger("linkedin_mcp.crypto")

_ENCRYPTED_PREFIX = b"ENC:V1:"


def _restrict_permissions(path: Path) -> None:
    """Best-effort restriction of file permissions to owner-only."""
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def get_or_create_fernet() -> Fernet:
    """Return a Fernet cipher backed by env var or local key file."""
    env_key = os.getenv("LINKEDIN_MCP_ENCRYPTION_KEY", "").strip()
    if env_key:
        return Fernet(env_key.encode("utf-8"))

    key_file = config.session_key_file
    if key_file.exists():
        key_bytes = key_file.read_bytes().strip()
        return Fernet(key_bytes)

    key_file.parent.mkdir(parents=True, exist_ok=True)
    key_bytes = Fernet.generate_key()
    key_file.write_bytes(key_bytes)
    _restrict_permissions(key_file)
    return Fernet(key_bytes)


def save_encrypted_json(path: Path, data: Dict[str, Any]) -> None:
    """Serialize data as JSON and write it encrypted with Fernet."""
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
    token = get_or_create_fernet().encrypt(raw)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_bytes(_ENCRYPTED_PREFIX + token)
    _restrict_permissions(tmp_path)
    tmp_path.replace(path)
    _restrict_permissions(path)


def load_encrypted_json(path: Path) -> Optional[Dict[str, Any]]:
    """Load and decrypt JSON from disk, migrating legacy plaintext if encountered."""
    if not path.exists():
        return None

    raw = path.read_bytes()
    if not raw:
        return None

    # Handle encrypted format
    if raw.startswith(_ENCRYPTED_PREFIX):
        token = raw[len(_ENCRYPTED_PREFIX):]
        try:
            decrypted = get_or_create_fernet().decrypt(token)
            return json.loads(decrypted.decode("utf-8"))
        except (InvalidToken, json.JSONDecodeError) as e:
            logger.warning(f"Failed to decrypt {path.name}: {e}")
            return None

    # Seamless migration for legacy plaintext storage_state.json
    try:
        data = json.loads(raw.decode("utf-8"))
        if isinstance(data, dict):
            save_encrypted_json(path, data)
            logger.info(f"Migrated plaintext {path.name} to encrypted storage.")
            return data
    except Exception as e:
        logger.warning(f"Could not parse legacy {path.name}: {e}")
    return None
