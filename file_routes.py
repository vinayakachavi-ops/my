import io
import mimetypes
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, send_file, current_app, jsonify
from app.routes.decorators import login_required, require_permission
from app.database.connection import db_session
from app.services.file_manager import FileManager
from app.services.encryption_service import EncryptionService
from app.services.audit_service import AuditService
from app.core.exceptions import ValidationError, FileManagementError

file_bp = Blueprint("files", __name__, url_prefix="/files")


def get_file_manager():
    encryption_srv = EncryptionService(key_file_path=current_app.config["ENCRYPTION_KEY_PATH"])
    file_mgr = FileManager(
        session=db_session,
        upload_folder=current_app.config["UPLOAD_FOLDER"],
        encryption_service=encryption_srv,
        allowed_extensions=current_app.config["ALLOWED_EXTENSIONS"],
        max_file_size=current_app.config["MAX_CONTENT_LENGTH"]
    )
    audit_srv = AuditService(db_session)
    return file_mgr, audit_srv


@file_bp.route("/", methods=["GET"])
@login_required
@require_permission("view")
def index():
    """List all encrypted files with metadata."""
    file_mgr, _ = get_file_manager()
    files = file_mgr.list_all_files()
    allowed_exts = sorted(list(current_app.config["ALLOWED_EXTENSIONS"]))
    max_mb = current_app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)

    return render_template(
        "files/index.html",
        files=files,
        user=g.current_user,
        allowed_extensions=allowed_exts,
        max_file_size_mb=max_mb
    )


@file_bp.route("/upload", methods=["POST"])
@login_required
@require_permission("upload")
def upload():
    """Upload a new file, encrypt before saving to disk."""
    if "file" not in request.files:
        flash("No file part provided in upload form.", "danger")
        return redirect(url_for("files.index"))

    file_obj = request.files["file"]
    if not file_obj or file_obj.filename == "":
        flash("Please select a file to upload.", "danger")
        return redirect(url_for("files.index"))

    file_mgr, audit_srv = get_file_manager()

    try:
        content = file_obj.read()
        mime_type = file_obj.content_type or mimetypes.guess_type(file_obj.filename)[0] or "application/octet-stream"
        
        record = file_mgr.save_file(
            filename=file_obj.filename,
            content=content,
            uploader_id=g.current_user.id,
            mime_type=mime_type
        )

        audit_srv.log(
            action="FILE_UPLOAD",
            user_id=g.current_user.id,
            username=g.current_user.username,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string,
            details=f"Uploaded and encrypted '{record.original_filename}' ({record.file_size} bytes, SHA256: {record.checksum[:12]}...)"
        )

        flash(f"File '{record.original_filename}' uploaded and encrypted successfully!", "success")

    except (ValidationError, FileManagementError) as e:
        flash(str(e), "danger")
    except Exception as e:
        flash(f"Unexpected upload error: {str(e)}", "danger")

    return redirect(url_for("files.index"))


@file_bp.route("/<int:file_id>/download", methods=["GET"])
@login_required
@require_permission("download")
def download(file_id: int):
    """Decrypt file strictly in memory and stream to authorized client."""
    file_mgr, audit_srv = get_file_manager()

    try:
        decrypted_bytes, record = file_mgr.get_decrypted_content(file_id)

        audit_srv.log(
            action="FILE_DOWNLOAD",
            user_id=g.current_user.id,
            username=g.current_user.username,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string,
            details=f"Decrypted in-memory and downloaded '{record.original_filename}' (ID {record.id})"
        )

        return send_file(
            io.BytesIO(decrypted_bytes),
            as_attachment=True,
            download_name=record.original_filename,
            mimetype=record.mime_type
        )

    except FileManagementError as e:
        flash(str(e), "danger")
        return redirect(url_for("files.index"))
    except Exception as e:
        flash(f"Decryption failed: {str(e)}", "danger")
        return redirect(url_for("files.index"))


@file_bp.route("/<int:file_id>/preview", methods=["GET"])
@login_required
@require_permission("view")
def preview(file_id: int):
    """
    Decrypted in-memory preview for supported files (text, images, markdown, pdf, json).
    Never writes unencrypted files to disk.
    """
    file_mgr, audit_srv = get_file_manager()

    try:
        decrypted_bytes, record = file_mgr.get_decrypted_content(file_id)

        audit_srv.log(
            action="FILE_VIEW",
            user_id=g.current_user.id,
            username=g.current_user.username,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string,
            details=f"Viewed preview of '{record.original_filename}' (ID {record.id})"
        )

        # For text/code/json files, attempt utf-8 decode
        is_text = False
        text_content = ""
        ext = record.original_filename.rsplit(".", 1)[-1].lower() if "." in record.original_filename else ""

        if ext in ("txt", "md", "csv", "json", "py", "js", "html", "css", "xml"):
            try:
                text_content = decrypted_bytes.decode("utf-8")
                is_text = True
            except UnicodeDecodeError:
                pass

        if request.args.get("raw") == "1":
            # Stream directly inline in browser for PDF or Image
            return send_file(
                io.BytesIO(decrypted_bytes),
                as_attachment=False,
                download_name=record.original_filename,
                mimetype=record.mime_type
            )

        if is_text:
            return jsonify({
                "status": "success",
                "filename": record.original_filename,
                "is_text": True,
                "content": text_content,
                "mime_type": record.mime_type,
                "size": record.file_size
            })
        else:
            return jsonify({
                "status": "success",
                "filename": record.original_filename,
                "is_text": False,
                "raw_url": url_for("files.preview", file_id=file_id, raw=1),
                "mime_type": record.mime_type,
                "size": record.file_size
            })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@file_bp.route("/<int:file_id>/delete", methods=["POST"])
@login_required
def delete(file_id: int):
    """Delete a file. Permitted if Admin OR original uploader."""
    file_mgr, audit_srv = get_file_manager()
    record = file_mgr.get_by_id(file_id)

    if not record:
        flash("File not found.", "danger")
        return redirect(url_for("files.index"))

    # Permission check: Admin or uploader
    if not (g.current_user.can_manage_users() or record.uploader_id == g.current_user.id):
        flash("You are not authorized to delete this file.", "danger")
        return redirect(url_for("files.index"))

    filename = record.original_filename
    file_mgr.delete_file(file_id)

    audit_srv.log(
        action="FILE_DELETE",
        user_id=g.current_user.id,
        username=g.current_user.username,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string,
        details=f"Deleted file '{filename}' (ID {file_id})"
    )

    flash(f"File '{filename}' was permanently deleted.", "info")
    return redirect(url_for("files.index"))
