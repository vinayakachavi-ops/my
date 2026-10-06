import pytest
from app.core.exceptions import ValidationError, FileManagementError
from app.database.schema import UserRecord


class TestFileManager:
    """Test suite verifying encrypted file storage, extension filtering, and in-memory decryption."""

    @pytest.fixture
    def test_user_id(self, session):
        user = UserRecord(
            username="file_tester",
            email="file_tester@test.com",
            password_hash="fakehash",
            role="Editor",
            is_active=True
        )
        session.add(user)
        session.commit()
        return user.id

    def test_save_and_decrypt_file(self, file_manager, test_user_id):
        """Uploaded file must be stored encrypted and decrypted with checksum verification."""
        content = b"Confidential Strategy: Project Apollo Launch Q3 2026."
        filename = "apollo_strategy.txt"

        record = file_manager.save_file(
            filename=filename,
            content=content,
            uploader_id=test_user_id,
            mime_type="text/plain"
        )

        assert record.id is not None
        assert record.original_filename == filename
        assert record.file_size == len(content)

        # Inspect disk file: must exist and be encrypted (NOT plaintext)
        stored_path = file_manager.upload_folder / record.stored_filename
        assert stored_path.exists()
        with open(stored_path, "rb") as f:
            disk_bytes = f.read()
        assert disk_bytes != content
        assert content not in disk_bytes

        # Retrieve and decrypt in-memory
        decrypted_bytes, fetched_record = file_manager.get_decrypted_content(record.id)
        assert decrypted_bytes == content
        assert fetched_record.id == record.id

    def test_disallowed_extension_rejected(self, file_manager, test_user_id):
        """Dangerous or unsupported extensions (e.g. .exe) must be rejected."""
        content = b"MZ\x90\x00\x03\x00\x00\x00"  # PE binary header
        with pytest.raises(ValidationError) as exc:
            file_manager.save_file("malware.exe", content, test_user_id)
        assert "extension is not allowed" in str(exc.value)

    def test_empty_file_rejected(self, file_manager, test_user_id):
        """Empty files must be rejected."""
        with pytest.raises(ValidationError) as exc:
            file_manager.save_file("empty.txt", b"", test_user_id)
        assert "empty file" in str(exc.value)

    def test_file_size_exceeded_rejected(self, file_manager, test_user_id):
        """Files exceeding size limit must be rejected."""
        oversized = b"A" * (6 * 1024 * 1024)  # 6 MB (limit is 5 MB)
        with pytest.raises(ValidationError) as exc:
            file_manager.save_file("large.txt", oversized, test_user_id)
        assert "exceeds the maximum limit" in str(exc.value)

    def test_delete_file(self, file_manager, test_user_id):
        """Deleting a file must remove both disk ciphertext and database record."""
        record = file_manager.save_file("temp.txt", b"Temporary file", test_user_id)
        file_path = file_manager.upload_folder / record.stored_filename
        assert file_path.exists()

        success = file_manager.delete_file(record.id)
        assert success is True
        assert not file_path.exists()
        assert file_manager.get_by_id(record.id) is None
