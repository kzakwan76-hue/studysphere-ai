from app.config import get_settings
from app.services.storage import delete_upload, save_upload


def test_save_and_delete_roundtrip():
    relative = save_upload(user_id=1, extension=".txt", data=b"hello")
    full_path = get_settings().uploads_dir / relative
    assert relative.startswith("1/") and relative.endswith(".txt")
    assert full_path.read_bytes() == b"hello"
    delete_upload(relative)
    assert not full_path.exists()


def test_delete_refuses_paths_outside_the_uploads_folder():
    outside = get_settings().uploads_dir.parent / "outside-test.txt"
    outside.parent.mkdir(parents=True, exist_ok=True)
    outside.write_text("keep me")
    delete_upload("../outside-test.txt")
    assert outside.exists()
    outside.unlink()