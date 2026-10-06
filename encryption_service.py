import os
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from app.core.exceptions import EncryptionError


class EncryptionService:
    """
    EncryptionService handles symmetric encryption and decryption of binary data
    using the Python cryptography library (Fernet / AES-128-CBC + HMAC-SHA256 authenticated encryption).
    
    Security Guarantee:
    - Master encryption key is loaded from SECURESHARE_ENCRYPTION_KEY env variable or an isolated key file.
    - Keys are NEVER stored in the database.
    - Files are decrypted strictly in memory upon authorized user request.
    """

    def __init__(self, key: Optional[bytes] = None, key_file_path: Optional[Path] = None):
        self._key = self._resolve_key(key, key_file_path)
        try:
            self._cipher = Fernet(self._key)
        except Exception as e:
            raise EncryptionError(f"Failed to initialize Fernet cipher: {str(e)}")

    def _resolve_key(self, explicit_key: Optional[bytes], key_file_path: Optional[Path]) -> bytes:
        """Resolve the encryption key from argument, environment variable, or key file."""
        if explicit_key:
            return explicit_key if isinstance(explicit_key, bytes) else explicit_key.encode("utf-8")

        # Check environment variable
        env_key = os.environ.get("SECURESHARE_ENCRYPTION_KEY")
        if env_key:
            return env_key.strip().encode("utf-8")

        # Check key file
        if key_file_path is None:
            key_file_path = Path(__file__).resolve().parent.parent.parent / ".encryption_key"

        if key_file_path.exists():
            with open(key_file_path, "rb") as f:
                return f.read().strip()

        # Generate a new key and persist to key file
        new_key = Fernet.generate_key()
        try:
            key_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(key_file_path, "wb") as f:
                f.write(new_key)
            # On Unix, enforce restrictive file permissions (chmod 600)
            try:
                os.chmod(key_file_path, 0o600)
            except Exception:
                pass
        except Exception as e:
            raise EncryptionError(f"Unable to write generated encryption key to {key_file_path}: {e}")

        return new_key

    def encrypt(self, data: bytes) -> bytes:
        """
        Encrypt raw bytes into authenticated ciphertext.
        
        :param data: Raw plaintext bytes
        :return: Encrypted ciphertext bytes
        """
        if not isinstance(data, bytes):
            raise EncryptionError("Data to encrypt must be bytes.")
        try:
            return self._cipher.encrypt(data)
        except Exception as e:
            raise EncryptionError(f"Encryption failed: {str(e)}")

    def decrypt(self, token: bytes) -> bytes:
        """
        Decrypt authenticated ciphertext back into original plaintext bytes.
        
        :param token: Ciphertext bytes
        :return: Plaintext bytes
        """
        if not isinstance(token, bytes):
            raise EncryptionError("Token to decrypt must be bytes.")
        try:
            return self._cipher.decrypt(token)
        except InvalidToken:
            raise EncryptionError("Decryption failed: Invalid encryption token or corrupted data.")
        except Exception as e:
            raise EncryptionError(f"Decryption failed: {str(e)}")

    @staticmethod
    def generate_key() -> str:
        """Helper to generate a new base64-encoded 32-byte encryption key string."""
        return Fernet.generate_key().decode("utf-8")
