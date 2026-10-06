import pytest
from app.services.encryption_service import EncryptionService
from app.core.exceptions import EncryptionError


class TestEncryptionService:
    """Test suite verifying Fernet / AES symmetric encryption functionality and error resilience."""

    def test_encrypt_and_decrypt_roundtrip(self, encryption_service):
        """Plaintext bytes should be encrypted and decrypted accurately."""
        secret_data = b"CONFIDENTIAL: Internal SecureShare Financial Report 2026"
        ciphertext = encryption_service.encrypt(secret_data)

        # Ciphertext must differ from plaintext
        assert ciphertext != secret_data
        assert secret_data not in ciphertext

        # Decryption must return exact original bytes
        decrypted = encryption_service.decrypt(ciphertext)
        assert decrypted == secret_data

    def test_binary_data_encryption(self, encryption_service):
        """Raw binary data (e.g. simulated image bytes) must roundtrip cleanly."""
        binary_data = bytes(range(256)) * 16  # 4096 bytes of binary spectrum
        ciphertext = encryption_service.encrypt(binary_data)
        decrypted = encryption_service.decrypt(ciphertext)
        assert decrypted == binary_data

    def test_tampered_ciphertext_fails(self, encryption_service):
        """Modifying ciphertext bytes must be detected by HMAC-SHA256 authenticated verification."""
        data = b"Patient Medical Record: Blood type O+"
        ciphertext = bytearray(encryption_service.encrypt(data))

        # Tamper with arbitrary byte inside payload
        ciphertext[25] = (ciphertext[25] + 1) % 256

        with pytest.raises(EncryptionError):
            encryption_service.decrypt(bytes(ciphertext))

    def test_invalid_key_fails_decryption(self, tmp_path):
        """Data encrypted with key A cannot be decrypted with key B."""
        key_a_file = tmp_path / "key_a.key"
        key_b_file = tmp_path / "key_b.key"

        service_a = EncryptionService(key_file_path=key_a_file)
        service_b = EncryptionService(key_file_path=key_b_file)

        data = b"Classified Intelligence Memorandum"
        ciphertext = service_a.encrypt(data)

        with pytest.raises(EncryptionError):
            service_b.decrypt(ciphertext)
