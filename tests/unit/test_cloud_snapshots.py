import pytest
from pathlib import Path
from camoufox_pm.core.database import StorageManager
from camoufox_pm.core.cloud_sync import generate_r2_presigned_url, pack_profile_snapshot, unpack_profile_snapshot

@pytest.mark.asyncio
async def test_snapshot_db_rolling_retention(tmp_path: Path):
    db_file = tmp_path / "test_snapshots.db"
    storage = StorageManager(str(db_file))
    await storage.initialize()

    profile_id = "test_profile_001"

    # Insert 7 snapshots; rolling retention should keep only the latest 5
    for i in range(1, 8):
        await storage.record_profile_snapshot(
            profile_id=profile_id,
            snapshot_name=f"Snapshot #{i}",
            size_kb=100.0 + i,
            r2_key=f"camoufox/cloud_profiles/{profile_id}/snapshots/snap_{i}.tar.gz",
        )

    snaps = await storage.list_profile_snapshots(profile_id)
    assert len(snaps) == 5
    # The newest should be Snapshot #7
    assert snaps[0]["snapshot_name"] == "Snapshot #7"
    assert snaps[-1]["snapshot_name"] == "Snapshot #3"

    # Test get snapshot
    target_id = snaps[0]["id"]
    single = await storage.get_profile_snapshot(target_id)
    assert single is not None
    assert single["id"] == target_id

    # Test delete snapshot
    deleted = await storage.delete_profile_snapshot(target_id)
    assert deleted is True
    remaining = await storage.list_profile_snapshots(profile_id)
    assert len(remaining) == 4

    await storage.close()

def test_presigned_url_generation():
    upload_url = generate_r2_presigned_url("PUT", "/tikmatrix/camoufox/test/snapshot.tar.gz", expires_in=300)
    assert upload_url.startswith("https://")
    assert "X-Amz-Algorithm=AWS4-HMAC-SHA256" in upload_url
    assert "X-Amz-Signature=" in upload_url
    assert "X-Amz-Expires=300" in upload_url

    download_url = generate_r2_presigned_url("GET", "/tikmatrix/camoufox/test/snapshot.tar.gz", expires_in=600)
    assert download_url.startswith("https://")
    assert "X-Amz-Expires=600" in download_url

def test_pack_unpack_snapshot(tmp_path: Path):
    source_dir = tmp_path / "source_profile"
    source_dir.mkdir()
    cookies_dir = source_dir / "Default" / "Network"
    cookies_dir.mkdir(parents=True)
    cookie_file = cookies_dir / "Cookies"
    cookie_file.write_bytes(b"dummy_cookie_sqlite_bytes")

    meta = {"id": "p1", "name": "Profile 1", "engine": "chromium"}
    packed = pack_profile_snapshot(source_dir, meta)
    assert len(packed) > 0

    dest_dir = tmp_path / "restored_profile"
    unpacked_meta = unpack_profile_snapshot(packed, dest_dir)
    assert unpacked_meta["id"] == "p1"
    restored_cookie = dest_dir / "Default" / "Network" / "Cookies"
    assert restored_cookie.is_file()
    assert restored_cookie.read_bytes() == b"dummy_cookie_sqlite_bytes"
