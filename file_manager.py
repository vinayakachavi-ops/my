import os
import uuid
import hashlib
from pathlib import Path
from typing import Optional, List, Tuple
from werkzeug.utils import secure_filename
from sqlalchemy.orm import Session
from app.database.schema import FileRecord, UserRecord
from app.services.encryption_service import EncryptionService
from app.core.exceptions import FileManagementError, ValidationError


class FileManager:
    """
    FileManager coordinates secure file validation, disk storage,
    AES encryption/decryption, and retrieval.
    
    Security Guarantee:
    - Files on disk are ALWAYS encrypted with Fernet / AES.
    - Stored filenames are random UUIDs with no user-controlled directory components.
    - Original file checksums are recorded and verified upon in-memory decryption.
    """

    def __init__(
        self,
        session: Session,
        upload_folder: Path,
        encryption_service: EncryptionService,
        allowed_extensions: Optional[set] = None,
        max_file_size: int = 16 * 1024 * 1024
    ):
        self.session = session
        self.upload_folder = Path(upload_folder)
        self.upload_folder.mkdir(parents=True, exist_ok=True)
        self.encryption_service = encryption_service
        self.allowed_extensions = {ext.lower().lstrip(".") for ext in (allowed_extensions or set())}
        self.max_file_size = max_file_size

    def is_allowed_extension(self, filename: str) -> bool:
        """Check if file extension matches the allowlist."""
        if "." not in filename:
            return False
        ext = filename.rsplit(".", 1)[1].lower()
        return ext in self.allowed_extensions

    def validate_file(self, filename: str, content: bytes) -> None:
        """
        Validate filename safety, extension allowlist, and size limit.
        """
        if not filename or not filename.strip():
            raise ValidationError("File name cannot be empty.")

        # Prevent null byte injection and directory traversal
        if "\x00" in filename or ".." in filename or "/" in filename or "\\" in filename:
            sanitized = secure_filename(filename)
            if not sanitized:
                raise ValidationError("Invalid filename detected.")

        if not self.is_allowed_extension(filename):
            ext_list = ", ".join(sorted(list(self.allowed_extensions)))
            raise ValidationError(f"File extension is not allowed. Permitted extensions: {ext_list}")

        if len(content) == 0:
            raise ValidationError("Cannot upload an empty file.")

        if len(content) > self.max_file_size:
            max_mb = self.max_file_size / (1024 * 1024)
            raise ValidationError(f"File size exceeds the maximum limit of {max_mb:.1f} MB.")

    def save_file(
        self,
        filename: str,
        content: bytes,
        uploader_id: int,
        mime_type: Optional[str] = None
    ) -> FileRecord:
        """
        Validate, encrypt, and store a file.
        
        1. Validates filename and raw bytes.
        2. Computes SHA-256 checksum of original content.
        3. Encrypts content via EncryptionService.
        4. Writes encrypted ciphertext to storage disk with a unique UUID name.
        5. Saves metadata to database.
        """
        self.validate_file(filename, content)

        clean_filename = secure_filename(filename)
        if not clean_filename:
            clean_filename = f"file_{uuid.uuid4().hex[:8]}"

        # Calculate original plaintext checksum for integrity validation
        checksum = hashlib.sha256(content).hexdigest()

        # Encrypt plaintext bytes before disk persistence
        encrypted_data = self.encryption_service.encrypt(content)

        # Generate non-colliding UUID storage filename
        stored_filename = f"{uuid.uuid4().hex}.enc"
        file_path = self.upload_folder / stored_filename

        try:
            with open(file_path, "wb") as f:
                f.write(encrypted_data)
        except Exception as e:
            raise FileManagementError(f"Failed to persist encrypted file to disk: {str(e)}")

        record = FileRecord(
            original_filename=clean_filename,
            stored_filename=stored_filename,
            file_size=len(content),  # Original unencrypted size in bytes
            mime_type=mime_type or "application/octet-stream",
            uploader_id=uploader_id,
            checksum=checksum
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def get_by_id(self, file_id: int) -> Optional[FileRecord]:
        """Retrieve FileRecord metadata by ID."""
        return self.session.query(FileRecord).filter_by(id=file_id).first()

    def list_all_files(self) -> List[FileRecord]:
        """List all files ordered by upload timestamp descending."""
        return (
            self.session.query(FileRecord)
            .join(UserRecord, FileRecord.uploader_id == UserRecord.id)
            .order_by(FileRecord.uploaded_at.desc())
            .all()
        )

    def get_decrypted_content(self, file_id: int) -> Tuple[bytes, FileRecord]:
        """
        Retrieve and decrypt a file in memory.
        
        :return: Tuple of (decrypted_plaintext_bytes, FileRecord)
        :raises FileManagementError: If file not found or corrupted
        """
        record = self.get_by_id(file_id)
        if not record:
            raise FileManagementError(f"File with ID {file_id} does not exist.")

        file_path = self.upload_folder / record.stored_filename
        if not file_path.exists():
            raise FileManagementError(f"Physical encrypted file is missing from storage.")

        try:
            with open(file_path, "rb") as f:
                encrypted_bytes = f.read()
        except Exception as e:
            raise FileManagementError(f"Failed to read encrypted file: {str(e)}")

        decrypted_bytes = self.encryption_service.decrypt(encrypted_bytes)

        # Verify integrity against stored checksum
        actual_checksum = hashlib.sha256(decrypted_bytes).hexdigest()
        if actual_checksum != record.checksum:
            raise FileManagementError("File integrity check failed! Checksum mismatch detected.")

        return decrypted_bytes, record

    def delete_file(self, file_id: int) -> bool:
        """Delete file from disk and database."""
        record = self.get_by_id(file_id)
        if not record:
            return False

        file_path = self.upload_folder / record.stored_filename
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception:
                pass

        self.session.delete(record)
        self.session.commit()
        return True
