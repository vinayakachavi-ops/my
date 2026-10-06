# SecureShare - Secure Encrypted File-Sharing Vault

**SecureShare** is an enterprise-grade full-stack web application designed for encrypted document sharing with polymorphic Role-Based Access Control (RBAC). Files are encrypted with Fernet (AES-128-CBC + HMAC-SHA256 authenticated encryption) before being committed to persistent disk storage, with encryption keys strictly isolated from the database and decryption executed exclusively in volatile memory.

---

## 🏛️ Object-Oriented Architecture & Polymorphism

SecureShare enforces access control through **polymorphic inheritance** rather than procedural conditionals (i.e. avoiding `if user.role == 'Admin'` checks across routes).

### 1. Abstract Permissions Interface (`app/core/permissions.py`)
Defines the strict capability contract adhering to the Interface Segregation Principle:
```python
class Permissions(ABC):
    @abstractmethod
    def can_upload(self) -> bool: pass

    @abstractmethod
    def can_view(self) -> bool: pass

    @abstractmethod
    def can_download(self) -> bool: pass

    @abstractmethod
    def can_manage_users(self) -> bool: pass

    @abstractmethod
    def can_assign_roles(self) -> bool: pass
```

### 2. User Abstract Base Class & Role Inheritance Hierarchy (`app/core/models.py`)
```
                     +-------------------+
                     |  Permissions(ABC) |
                     +---------+---------+
                               |
                               v
                     +---------+---------+
                     |     User (ABC)    |
                     +---------+---------+
                               |
                               v
                     +---------+---------+
                     |    Viewer(User)   |   can_view() -> True
                     |                   |   can_download() -> True
                     +---------+---------+
                               |
                               v
                     +---------+---------+
                     |   Editor(Viewer)  |   can_upload() -> True
                     |                   |   (inherits view & download)
                     +---------+---------+
                               |
                               v
                     +---------+---------+
                     |   Admin(Editor)   |   can_manage_users() -> True
                     |                   |   can_assign_roles() -> True
                     +-------------------+   (inherits view, download & upload)
```

- **`Viewer(User)`**: The base authenticated role. Permitted only to view catalog metadata and decrypt files for download. `can_upload()` is `False`.
- **`Editor(Viewer)`**: Inherits `can_view()` and `can_download()` from `Viewer` and overrides `can_upload() -> True`.
- **`Admin(Editor)`**: Inherits all viewing, downloading, and uploading capabilities from `Editor`, and overrides `can_manage_users() -> True` and `can_assign_roles() -> True`.

### 3. Polymorphic RBAC Enforcement
Every route protection decorator calls the capability method directly on the concrete `User` subclass:
```python
# app/routes/decorators.py
@require_permission("upload")       # Evaluates current_user.can_upload()
@require_permission("manage_users") # Evaluates current_user.can_manage_users()
```
If a user with the `Viewer` role attempts to invoke a route guarded by `@require_permission("upload")`, Python executes `Viewer.can_upload()` which returns `False`, automatically triggering an HTTP 403 Access Denied exception.

### 4. Domain & Service Separation
- **`EncryptionService` (`app/services/encryption_service.py`)**: Responsible for authenticated AES encryption/decryption using cryptography's Fernet engine. Keys are read from environment variables or a restricted key file, never stored in the relational database.
- **`FileManager` (`app/services/file_manager.py`)**: Sanitizes filenames, enforces extension allowlists, computes SHA-256 integrity checksums, coordinates encryption, and handles in-memory decryption.
- **`AuthService` (`app/services/auth_service.py`)**: Validates password complexity, computes salted bcrypt hashes, and authenticates credentials.
- **`UserManager` (`app/services/user_manager.py`)**: Handles CRUD operations and instantiates domain models via `UserFactory`.
- **`AuditService` (`app/services/audit_service.py`)**: Writes immutable audit log entries for all security events.

---

## 🔒 Security Architecture Highlights

1. **Zero-Knowledge Decryption in Volatile Memory**:
   Files on disk (`uploads/<uuid>.enc`) are always authenticated ciphertext. When a user downloads or previews a document, bytes are decrypted strictly in memory and streamed directly via `BytesIO`. Raw encrypted files or master keys are never exposed.
2. **Path Traversal Immunization**:
   Filenames are sanitized via `werkzeug.utils.secure_filename`, and disk storage filenames are randomized UUIDs (`uuid.uuid4().hex + ".enc"`), preventing directory traversal attacks (`../../`).
3. **Bcrypt Password Security**:
   Passwords require $\ge 8$ characters, uppercase, lowercase, numbers, and special symbols, hashed with 12 salt rounds.
4. **CSRF Protection**:
   State-changing requests (`POST`, `PUT`, `DELETE`) require a valid session CSRF token.
5. **Deactivation Policy**:
   Users can be deactivated (not deleted) by Admins. Deactivated accounts are blocked from logging in.
6. **Immutable Audit Trail**:
   All logins, logouts, failures, uploads, downloads, role modifications, and status changes are recorded with client IP and user agent.

---

## 📁 Project Directory Structure

```
secureshare/
├── app/
│   ├── __init__.py                # App factory, context processors & error handlers
│   ├── config.py                  # Environment & security configuration
│   ├── core/
│   │   ├── __init__.py
│   │   ├── permissions.py         # Permissions interface (ABC)
│   │   ├── models.py              # User, Viewer, Editor, Admin polymorphic models
│   │   └── exceptions.py          # Domain-specific exception hierarchy
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py          # SQLAlchemy engine and scoped session
│   │   └── schema.py              # UserRecord, FileRecord, AuditLogRecord
│   ├── services/
│   │   ├── __init__.py
│   │   ├── encryption_service.py  # Fernet / AES-128-CBC + HMAC-SHA256
│   │   ├── file_manager.py        # Safe storage, encryption & in-memory decryption
│   │   ├── auth_service.py        # Bcrypt hashing & credential validation
│   │   ├── user_manager.py        # User CRUD & active status management
│   │   └── audit_service.py       # Security event logging
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── decorators.py          # @login_required, @require_permission (polymorphic)
│   │   ├── auth_routes.py         # Login, Register, Logout
│   │   ├── dashboard_routes.py    # Main dashboard & capability matrix
│   │   ├── file_routes.py         # Upload, list, preview, download, delete
│   │   └── admin_routes.py        # RBAC role management, status toggles, audit logs
│   ├── templates/
│   │   ├── base.html              # Responsive layout with Lucide icons & toasts
│   │   ├── auth/
│   │   │   ├── login.html         # Sign-in page with seed hints
│   │   │   └── register.html      # Registration with dynamic password meter
│   │   ├── dashboard.html         # User dashboard with role badge & quick actions
│   │   ├── files/
│   │   │   └── index.html         # Files vault, upload modal, in-memory preview modal
│   │   ├── admin/
│   │   │   └── index.html         # Admin panel: user table, role changer, audit trail
│   │   └── errors/
│   │       ├── 403.html           # Access Denied page with missing capability details
│   │       ├── 404.html           # Resource Not Found
│   │       └── 500.html           # Internal Server Error
│   └── static/
│       ├── css/
│       │   └── style.css          # Sleek enterprise dark-slate styling
│       └── js/
│           ├── main.js            # Global utilities & toast auto-dismiss
│           ├── auth.js            # Real-time password strength meter
│           ├── files.js           # Drag-and-drop uploads & preview modal
│           └── admin.js           # Admin tabs & audit search filter
├── instance/
│   └── secureshare.db             # SQLite database
├── uploads/                       # Encrypted ciphertext storage (.gitkeep)
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Pytest fixtures & in-memory test database
│   ├── test_permissions.py        # Role hierarchy & polymorphism unit tests
│   ├── test_encryption.py         # Fernet cipher roundtrip & tampering tests
│   ├── test_auth.py               # Bcrypt hashing & password validation tests
│   ├── test_file_manager.py       # Encrypted storage & integrity tests
│   └── test_routes.py             # End-to-end RBAC HTTP integration tests
├── seed.py                        # Database initialization & default account seeder
├── run.py                         # Application runner
├── requirements.txt               # Dependencies
├── .env.example                   # Environment variable template
├── .env                           # Configured environment keys
└── README.md
```

---

## 🚀 Setup & Execution Guide

### Prerequisites
- Python 3.10+ (tested on Python 3.12)
- Windows PowerShell, macOS Terminal, or Linux Bash

### Step 1: Create and Activate Virtual Environment
```bash
# In the secureshare project directory
python -m venv .venv

# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# On Linux / macOS:
source .venv/bin/activate
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
*(The repository already includes a pre-configured `.env` with a secure 32-byte Fernet key).*

### Step 4: Seed Database with Default Accounts
```bash
python seed.py
```

### Default Accounts Created:
| Role | Username | Password | Email | Permissions |
| :--- | :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `Admin@12345` | `admin@secureshare.local` | Upload, View, Download, Manage Users, Assign Roles |
| **Editor** | `editor` | `Editor@12345` | `editor@secureshare.local` | Upload, View, Download |
| **Viewer** | `viewer` | `Viewer@12345` | `viewer@secureshare.local` | View, Download |

### Step 5: Run the Web Application
```bash
python run.py
```
Open your browser and navigate to:
**http://127.0.0.1:5000**

---

## ⚡ Start the Server

You can start the SecureShare server using any of the following methods:

### Method A: One-Click Quick Start (Windows Batch File)
Double-click `start.bat` or run it from Command Prompt / PowerShell:
```cmd
start.bat
```
This batch file automatically activates `.venv` and runs `run.py`, keeping the terminal window open to display logs and server output.

### Method B: PowerShell Manual Start
```powershell
# Navigate to the project root
cd C:\Users\madda\.gemini\antigravity\scratch\secureshare

# Run with virtual environment Python
.\.venv\Scripts\python.exe run.py
```

### Method C: Background Process (PowerShell)
To run the server in the background:
```powershell
Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "run.py" -NoNewWindow
```

### Verifying the Server is Running
Test server reachability:
```powershell
Invoke-WebRequest http://127.0.0.1:5000/auth/login -UseBasicParsing
```
A status code of `200` confirms the server is actively serving requests.

### Accessing the Web Vault
- **URL**: [http://127.0.0.1:5000](http://127.0.0.1:5000)
- **Default Admin Login**:
  - Username: `admin`
  - Password: `Admin@12345`

---


## 🧪 Running the Automated Test Suite

Run all 25 unit and integration tests with pytest:
```bash
pytest -v
```

Output:
```
tests/test_auth.py::TestAuthService::test_password_strength_validation PASSED
tests/test_auth.py::TestAuthService::test_bcrypt_hashing_and_verification PASSED
tests/test_auth.py::TestAuthService::test_user_registration_defaults_to_viewer PASSED
tests/test_auth.py::TestAuthService::test_authentication_with_username_and_email PASSED
tests/test_auth.py::TestAuthService::test_authentication_invalid_credentials PASSED
tests/test_auth.py::TestAuthService::test_deactivated_user_cannot_login PASSED
tests/test_encryption.py::TestEncryptionService::test_encrypt_and_decrypt_roundtrip PASSED
tests/test_encryption.py::TestEncryptionService::test_binary_data_encryption PASSED
tests/test_encryption.py::TestEncryptionService::test_tampered_ciphertext_fails PASSED
tests/test_encryption.py::TestEncryptionService::test_invalid_key_fails_decryption PASSED
tests/test_file_manager.py::TestFileManager::test_save_and_decrypt_file PASSED
tests/test_file_manager.py::TestFileManager::test_disallowed_extension_rejected PASSED
tests/test_file_manager.py::TestFileManager::test_empty_file_rejected PASSED
tests/test_file_manager.py::TestFileManager::test_file_size_exceeded_rejected PASSED
tests/test_file_manager.py::TestFileManager::test_delete_file PASSED
tests/test_permissions.py::TestPermissionsHierarchy::test_viewer_permissions PASSED
tests/test_permissions.py::TestPermissionsHierarchy::test_editor_inherits_and_extends_viewer PASSED
tests/test_permissions.py::TestPermissionsHierarchy::test_admin_inherits_and_extends_editor PASSED
tests/test_permissions.py::TestPermissionsHierarchy::test_polymorphic_permission_checks PASSED
tests/test_permissions.py::TestPermissionsHierarchy::test_user_factory_instantiation PASSED
tests/test_permissions.py::TestPermissionsHierarchy::test_to_dict_serialization PASSED
tests/test_routes.py::TestRouteRBAC::test_unauthenticated_redirect PASSED
tests/test_routes.py::TestRouteRBAC::test_viewer_access_and_restrictions PASSED
tests/test_routes.py::TestRouteRBAC::test_editor_can_upload_but_no_admin PASSED
tests/test_routes.py::TestRouteRBAC::test_admin_has_full_access PASSED
============================== 25 passed in 8.21s ==============================
```
