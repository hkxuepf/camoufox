"""Enterprise PostgreSQL storage backend for CamouHub fleet.

Enables true multi-operator concurrency, row-level locking, and high-throughput
state management for team studios without "database is locked" errors.
Switched automatically via DATABASE_URL=postgresql://...
"""

import json
from datetime import datetime, timezone
from typing import Any

from loguru import logger

try:
    import asyncpg
except ImportError:
    asyncpg = None  # type: ignore[assignment]

from .models import (
    Profile,
    ProfileGroup,
    ProfileStatus,
    ProxyConfig,
    Schedule,
    ScheduleRun,
)


class PostgresDatabaseManager:
    """High-concurrency PostgreSQL database manager using asyncpg."""

    def __init__(self, dsn: str):
        # Normalize postgres:// to postgresql://
        if dsn.startswith("postgres://"):
            dsn = "postgresql://" + dsn[11:]
        self.dsn = dsn
        self._pool: Any = None
        logger.info("PostgresDatabaseManager configured with PostgreSQL backend")

    async def initialize(self) -> None:
        """Create connection pool and initialize schema."""
        if asyncpg is None:
            raise RuntimeError("asyncpg is required for PostgreSQL mode. Install with `uv add asyncpg`.")

        self._pool = await asyncpg.create_pool(
            self.dsn,
            min_size=2,
            max_size=20,
            command_timeout=30.0,
        )
        logger.info("Connected to PostgreSQL connection pool")
        await self._create_tables()

    async def close(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def _create_tables(self) -> None:
        """Initialize PostgreSQL schema with IF NOT EXISTS."""
        async with self._pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS recovery_lock (
                    id INT PRIMARY KEY,
                    holder TEXT,
                    expires TIMESTAMPTZ
                );
                INSERT INTO recovery_lock (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

                CREATE TABLE IF NOT EXISTS profile_groups (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    color TEXT,
                    description TEXT,
                    user_id TEXT,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS profiles (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    group_id TEXT,
                    status TEXT NOT NULL,
                    browser_settings TEXT NOT NULL,
                    proxy_config TEXT,
                    extensions TEXT,
                    storage_path TEXT NOT NULL,
                    notes TEXT,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMPTZ,
                    fingerprint TEXT,
                    proxy_check TEXT,
                    locked_by TEXT,
                    lock_expires TIMESTAMPTZ,
                    row_version BIGINT NOT NULL DEFAULT 0,
                    deleted_at TIMESTAMPTZ,
                    user_id TEXT,
                    cookies TEXT,
                    account TEXT,
                    is_favorite BOOLEAN DEFAULT FALSE,
                    tags TEXT,
                    sync_status TEXT DEFAULT 'synced',
                    last_synced_at TIMESTAMPTZ,
                    sync_size_kb REAL,
                    cloud_sync_enabled BOOLEAN DEFAULT TRUE
                );

                CREATE TABLE IF NOT EXISTS profile_snapshots (
                    id TEXT PRIMARY KEY,
                    profile_id TEXT NOT NULL,
                    snapshot_name TEXT,
                    size_kb REAL,
                    r2_key TEXT,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_pg_snapshots_profile ON profile_snapshots(profile_id);

                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    role TEXT DEFAULT 'user',
                    plan_id TEXT DEFAULT 'free',
                    max_profiles INT DEFAULT 10,
                    max_concurrent INT DEFAULT 2,
                    expires_at TIMESTAMPTZ,
                    status TEXT DEFAULT 'active',
                    api_status TEXT DEFAULT 'disabled',
                    api_app_id TEXT,
                    api_app_secret TEXT,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMPTZ
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMPTZ NOT NULL
                );

                CREATE TABLE IF NOT EXISTS admin_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );

                CREATE TABLE IF NOT EXISTS plans (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    max_profiles INT NOT NULL,
                    max_concurrent INT NOT NULL,
                    duration_days INT DEFAULT 30,
                    price_usdt REAL NOT NULL,
                    description TEXT,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS orders (
                    id TEXT PRIMARY KEY,
                    order_no TEXT UNIQUE NOT NULL,
                    user_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    plan_id TEXT NOT NULL,
                    plan_name TEXT NOT NULL,
                    amount_usdt REAL NOT NULL,
                    status TEXT NOT NULL,
                    pay_network TEXT,
                    pay_address TEXT,
                    tx_hash TEXT,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS client_releases (
                    id TEXT PRIMARY KEY,
                    version TEXT NOT NULL,
                    release_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    is_critical BOOLEAN DEFAULT FALSE,
                    min_version TEXT,
                    download_url_win TEXT,
                    download_url_mac TEXT,
                    download_url_linux TEXT,
                    sha256_win TEXT,
                    sha256_mac TEXT,
                    sha256_linux TEXT,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS kernel_releases (
                    id TEXT PRIMARY KEY,
                    version TEXT NOT NULL,
                    engine TEXT NOT NULL,
                    flavor TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    is_recommended BOOLEAN DEFAULT FALSE,
                    download_url_mac_arm64 TEXT,
                    download_url_win_x64 TEXT,
                    sha256_mac_arm64 TEXT,
                    sha256_win_x64 TEXT,
                    size_bytes BIGINT DEFAULT 0,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS schedules (
                    id TEXT PRIMARY KEY,
                    profile_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    interval_minutes INT,
                    at_time TEXT,
                    days TEXT,
                    run_minutes INT,
                    enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    next_run_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL
                );

                CREATE TABLE IF NOT EXISTS schedule_runs (
                    id SERIAL PRIMARY KEY,
                    schedule_id TEXT NOT NULL,
                    started_at TIMESTAMPTZ NOT NULL,
                    finished_at TIMESTAMPTZ,
                    outcome TEXT NOT NULL,
                    message TEXT
                );
            """)

    # --- Profile Methods ---

    async def get_profile(self, profile_id: str, include_deleted: bool = False) -> Profile | None:
        async with self._pool.acquire() as conn:
            query = "SELECT * FROM profiles WHERE id = $1"
            if not include_deleted:
                query += " AND deleted_at IS NULL"
            row = await conn.fetchrow(query, profile_id)
            if not row:
                return None
            return self._row_to_profile(dict(row))

    async def save_profile(self, profile: Profile, expected_row_version: int | None = None) -> None:
        from .database import StaleWriteError

        async with self._pool.acquire() as conn:
            # Check row version if updating
            existing = await conn.fetchrow("SELECT row_version FROM profiles WHERE id = $1", profile.id)
            if existing:
                if expected_row_version is not None and existing["row_version"] != expected_row_version:
                    raise StaleWriteError(profile.id, expected_row_version)

            proxy_json = json.dumps(profile.proxy.model_dump()) if profile.proxy else None
            settings_json = json.dumps(profile.browser_settings.model_dump())
            extensions_json = json.dumps(profile.extensions) if profile.extensions else None
            tags_json = json.dumps(profile.tags) if profile.tags else None

            await conn.execute("""
                INSERT INTO profiles (
                    id, name, group_id, status, browser_settings, proxy_config, extensions,
                    storage_path, notes, created_at, updated_at, last_used, deleted_at,
                    user_id, cookies, account, is_favorite, tags, sync_status, last_synced_at,
                    sync_size_kb, cloud_sync_enabled, row_version
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23
                )
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    group_id = EXCLUDED.group_id,
                    status = EXCLUDED.status,
                    browser_settings = EXCLUDED.browser_settings,
                    proxy_config = EXCLUDED.proxy_config,
                    extensions = EXCLUDED.extensions,
                    storage_path = EXCLUDED.storage_path,
                    notes = EXCLUDED.notes,
                    updated_at = CURRENT_TIMESTAMP,
                    last_used = EXCLUDED.last_used,
                    deleted_at = EXCLUDED.deleted_at,
                    user_id = EXCLUDED.user_id,
                    cookies = EXCLUDED.cookies,
                    account = EXCLUDED.account,
                    is_favorite = EXCLUDED.is_favorite,
                    tags = EXCLUDED.tags,
                    sync_status = EXCLUDED.sync_status,
                    last_synced_at = EXCLUDED.last_synced_at,
                    sync_size_kb = EXCLUDED.sync_size_kb,
                    cloud_sync_enabled = EXCLUDED.cloud_sync_enabled,
                    row_version = profiles.row_version + 1
            """,
                profile.id, profile.name, profile.group, profile.status.value,
                settings_json, proxy_json, extensions_json, profile.storage_path,
                profile.notes, profile.created_at, datetime.now(timezone.utc),
                profile.last_used, profile.deleted_at, profile.user_id,
                profile.cookies, profile.account, profile.is_favorite, tags_json,
                profile.sync_status, profile.last_synced_at, profile.sync_size_kb,
                profile.cloud_sync_enabled, (expected_row_version or 0) + 1,
            )

    async def update_profile(self, profile: Profile, expected_row_version: int | None = None) -> None:
        await self.save_profile(profile, expected_row_version)

    async def list_profiles(
        self,
        filters: dict | None = None,
        limit: int | None = None,
        offset: int = 0,
        **kwargs,
    ) -> list[Profile]:
        f = dict(filters) if isinstance(filters, dict) else {}
        for k, v in kwargs.items():
            if v is not None:
                f[k] = v

        conditions = []
        params = []
        idx = 1

        include_deleted = f.get("include_deleted", False)
        trashed = f.get("trashed", False)

        if trashed:
            conditions.append("deleted_at IS NOT NULL")
        elif not include_deleted:
            conditions.append("deleted_at IS NULL")

        user_id = f.get("user_id")
        if user_id:
            conditions.append(f"user_id = ${idx}")
            params.append(user_id)
            idx += 1

        group_id = f.get("group") or f.get("group_id")
        if group_id:
            conditions.append(f"group_id = ${idx}")
            params.append(group_id)
            idx += 1

        status = f.get("status")
        if status:
            status_val = status.value if hasattr(status, "value") else str(status)
            conditions.append(f"status = ${idx}")
            params.append(status_val)
            idx += 1

        name_like = f.get("name_like")
        if name_like:
            conditions.append(f"name ILIKE ${idx}")
            params.append(f"%{name_like}%")
            idx += 1

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        query = f"SELECT * FROM profiles {where} ORDER BY created_at DESC"

        eff_limit = limit if (limit is not None and limit > 0) else (f.get("limit") or 100)
        eff_offset = offset if offset else (f.get("offset") or f.get("skip") or 0)

        query += f" OFFSET ${idx} LIMIT ${idx + 1}"
        params.extend([eff_offset, eff_limit])

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [self._row_to_profile(dict(r)) for r in rows]

    async def count_profiles(self, filters: dict | None = None) -> int:
        conditions = []
        params = []
        idx = 1

        include_deleted = False
        trashed = False
        if filters:
            include_deleted = filters.get("include_deleted", False)
            trashed = filters.get("trashed", False)

        if trashed:
            conditions.append("deleted_at IS NOT NULL")
        elif not include_deleted:
            conditions.append("deleted_at IS NULL")

        if filters:
            if filters.get("user_id"):
                conditions.append(f"user_id = ${idx}")
                params.append(filters["user_id"])
                idx += 1
            group_id = filters.get("group") or filters.get("group_id")
            if group_id:
                conditions.append(f"group_id = ${idx}")
                params.append(group_id)
                idx += 1
            if filters.get("status"):
                status_val = filters["status"].value if hasattr(filters["status"], "value") else str(filters["status"])
                conditions.append(f"status = ${idx}")
                params.append(status_val)
                idx += 1
            if filters.get("name_like"):
                conditions.append(f"name ILIKE ${idx}")
                params.append(f"%{filters['name_like']}%")
                idx += 1

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        query = f"SELECT COUNT(*) FROM profiles {where}"
        async with self._pool.acquire() as conn:
            val = await conn.fetchval(query, *params)
            return val or 0

    async def set_profile_trashed(self, profile_id: str, trashed: bool) -> bool:
        async with self._pool.acquire() as conn:
            if trashed:
                res = await conn.execute(
                    "UPDATE profiles SET deleted_at = CURRENT_TIMESTAMP WHERE id = $1 AND deleted_at IS NULL",
                    profile_id,
                )
            else:
                res = await conn.execute(
                    "UPDATE profiles SET deleted_at = NULL WHERE id = $1 AND deleted_at IS NOT NULL",
                    profile_id,
                )
            return "UPDATE 1" in res

    # --- Profile Groups ---

    async def save_profile_group(self, group: ProfileGroup) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO profile_groups (id, name, color, description, user_id, updated_at)
                VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    color = EXCLUDED.color,
                    description = EXCLUDED.description,
                    user_id = EXCLUDED.user_id,
                    updated_at = CURRENT_TIMESTAMP
                """,
                group.id,
                group.name,
                group.color,
                group.description,
                group.user_id,
            )

    async def list_profile_groups(self) -> list[ProfileGroup]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM profile_groups ORDER BY created_at ASC")
            return [
                ProfileGroup(
                    id=r["id"],
                    name=r["name"],
                    color=r["color"],
                    description=r["description"],
                    user_id=r["user_id"],
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                )
                for r in rows
            ]

    async def delete_profile_group(self, group_id: str) -> bool:
        async with self._pool.acquire() as conn:
            res = await conn.execute("DELETE FROM profile_groups WHERE id = $1", group_id)
            return "DELETE 1" in res

    async def delete_profile(self, profile_id: str, permanent: bool = False) -> bool:
        async with self._pool.acquire() as conn:
            if permanent:
                res = await conn.execute("DELETE FROM profiles WHERE id = $1", profile_id)
            else:
                res = await conn.execute(
                    "UPDATE profiles SET deleted_at = CURRENT_TIMESTAMP WHERE id = $1", profile_id
                )
            return " 0" not in res

    # --- Lease Management (Row-Level PostgreSQL Locking) ---

    async def acquire_lease(
        self, profile_id: str, holder: str, ttl_seconds: int, include_deleted: bool = False
    ) -> bool:
        async with self._pool.acquire() as conn:
            res = await conn.execute("""
                UPDATE profiles
                   SET locked_by = $1,
                       lock_expires = CURRENT_TIMESTAMP + ($2 || ' seconds')::INTERVAL
                 WHERE id = $3 AND (deleted_at IS NULL OR $4)
                   AND (locked_by IS NULL OR locked_by = $1 OR lock_expires < CURRENT_TIMESTAMP)
            """, holder, str(ttl_seconds), profile_id, include_deleted)
            return "UPDATE 1" in res

    async def renew_lease(self, profile_ids: list[str], holder: str, ttl_seconds: int) -> int:
        if not profile_ids:
            return 0
        async with self._pool.acquire() as conn:
            res = await conn.execute("""
                UPDATE profiles
                   SET lock_expires = CURRENT_TIMESTAMP + ($1 || ' seconds')::INTERVAL
                 WHERE id = ANY($2) AND locked_by = $3
            """, str(ttl_seconds), profile_ids, holder)
            # res format: "UPDATE <count>"
            parts = res.split()
            return int(parts[1]) if len(parts) > 1 else 0

    async def release_lease(self, profile_id: str, holder: str) -> bool:
        async with self._pool.acquire() as conn:
            res = await conn.execute("""
                UPDATE profiles
                   SET locked_by = NULL, lock_expires = NULL
                 WHERE id = $1 AND locked_by = $2
            """, profile_id, holder)
            return "UPDATE 1" in res

    # --- Snapshots (时光机) ---

    async def record_profile_snapshot(
        self, profile_id: str, snapshot_name: str, size_kb: float, r2_key: str
    ) -> dict:
        import uuid
        snapshot_id = f"snap_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO profile_snapshots (id, profile_id, snapshot_name, size_kb, r2_key, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, snapshot_id, profile_id, snapshot_name, size_kb, r2_key, now)

            # Rolling retention: keep newest 5
            all_snaps = await conn.fetch(
                "SELECT id FROM profile_snapshots WHERE profile_id = $1 ORDER BY created_at DESC",
                profile_id,
            )
            if len(all_snaps) > 5:
                old_ids = [r["id"] for r in all_snaps[5:]]
                await conn.execute("DELETE FROM profile_snapshots WHERE id = ANY($1)", old_ids)

        return {
            "id": snapshot_id,
            "profile_id": profile_id,
            "snapshot_name": snapshot_name,
            "size_kb": size_kb,
            "r2_key": r2_key,
            "created_at": now.isoformat(),
        }

    async def list_profile_snapshots(self, profile_id: str) -> list[dict]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM profile_snapshots WHERE profile_id = $1 ORDER BY created_at DESC",
                profile_id,
            )
            return [dict(r) for r in rows]

    async def get_profile_snapshot(self, snapshot_id: str) -> dict | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM profile_snapshots WHERE id = $1", snapshot_id)
            return dict(row) if row else None

    async def delete_profile_snapshot(self, snapshot_id: str) -> bool:
        async with self._pool.acquire() as conn:
            res = await conn.execute("DELETE FROM profile_snapshots WHERE id = $1", snapshot_id)
            return "DELETE 1" in res

    async def set_cloud_sync_status(
        self, profile_id: str, status: str, size_kb: float | None = None
    ) -> None:
        async with self._pool.acquire() as conn:
            if size_kb is not None:
                await conn.execute("""
                    UPDATE profiles
                       SET sync_status = $1, last_synced_at = CURRENT_TIMESTAMP, sync_size_kb = $2
                     WHERE id = $3
                """, status, size_kb, profile_id)
            else:
                await conn.execute("""
                    UPDATE profiles
                       SET sync_status = $1, last_synced_at = CURRENT_TIMESTAMP
                     WHERE id = $2
                """, status, profile_id)

    async def acquire_recovery_lock(self, holder: str, ttl_seconds: int) -> bool:
        async with self._pool.acquire() as conn:
            res = await conn.execute(
                """
                UPDATE recovery_lock
                   SET holder = $1, expires = CURRENT_TIMESTAMP + ($2 || ' seconds')::interval
                 WHERE id = 1 AND (holder IS NULL OR holder = $1 OR expires < CURRENT_TIMESTAMP)
                """,
                holder,
                str(ttl_seconds),
            )
            return "UPDATE 1" in res

    async def release_recovery_lock(self, holder: str) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute("UPDATE recovery_lock SET holder = NULL, expires = NULL WHERE id = 1 AND holder = $1", holder)

    async def get_lease_holders(self) -> list[dict]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, name, locked_by, lock_expires
                  FROM profiles
                 WHERE locked_by IS NOT NULL AND lock_expires > CURRENT_TIMESTAMP
                """
            )
            return [dict(r) for r in rows]

    # --- Schedule Methods ---

    async def save_schedule(self, schedule: Schedule) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO schedules (
                    id, profile_id, action, kind, interval_minutes, at_time, days,
                    run_minutes, enabled, next_run_at, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (id) DO UPDATE SET
                    profile_id = EXCLUDED.profile_id,
                    action = EXCLUDED.action,
                    kind = EXCLUDED.kind,
                    interval_minutes = EXCLUDED.interval_minutes,
                    at_time = EXCLUDED.at_time,
                    days = EXCLUDED.days,
                    run_minutes = EXCLUDED.run_minutes,
                    enabled = EXCLUDED.enabled,
                    next_run_at = EXCLUDED.next_run_at,
                    updated_at = EXCLUDED.updated_at
                """,
                schedule.id,
                schedule.profile_id,
                schedule.action,
                schedule.kind,
                schedule.interval_minutes,
                schedule.at_time,
                json.dumps(schedule.days) if schedule.days else None,
                schedule.run_minutes,
                schedule.enabled,
                schedule.next_run_at,
                schedule.created_at,
                schedule.updated_at,
            )

    async def get_schedule(self, schedule_id: str) -> Schedule | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM schedules WHERE id = $1", schedule_id)
            return self._row_to_schedule(row) if row else None

    async def list_schedules(self, profile_id: str | None = None) -> list[Schedule]:
        async with self._pool.acquire() as conn:
            if profile_id:
                rows = await conn.fetch("SELECT * FROM schedules WHERE profile_id = $1 ORDER BY created_at", profile_id)
            else:
                rows = await conn.fetch("SELECT * FROM schedules ORDER BY created_at")
            return [self._row_to_schedule(row) for row in rows]

    async def delete_schedule(self, schedule_id: str) -> bool:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("DELETE FROM schedule_runs WHERE schedule_id = $1", schedule_id)
                res = await conn.execute("DELETE FROM schedules WHERE id = $1", schedule_id)
                return "DELETE 1" in res

    async def log_schedule_run(self, run: ScheduleRun, keep: int = 20) -> ScheduleRun:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    """
                    INSERT INTO schedule_runs (schedule_id, started_at, finished_at, outcome, message)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING id
                    """,
                    run.schedule_id,
                    run.started_at,
                    run.finished_at,
                    run.outcome,
                    run.message,
                )
                if row:
                    run.id = row["id"]
                await conn.execute(
                    """
                    DELETE FROM schedule_runs WHERE schedule_id = $1 AND id NOT IN (
                        SELECT id FROM schedule_runs WHERE schedule_id = $1 ORDER BY id DESC LIMIT $2
                    )
                    """,
                    run.schedule_id,
                    keep,
                )
                return run

    async def list_schedule_runs(self, schedule_id: str, limit: int = 20) -> list[ScheduleRun]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM schedule_runs WHERE schedule_id = $1 ORDER BY id DESC LIMIT $2",
                schedule_id,
                limit,
            )
            return [self._row_to_schedule_run(row) for row in rows]

    def _row_to_schedule(self, row) -> Schedule:
        days = row["days"]
        if isinstance(days, str):
            try:
                days = json.loads(days)
            except Exception:
                days = None
        next_run = row["next_run_at"]
        if isinstance(next_run, str):
            next_run = datetime.fromisoformat(next_run)
        created = row["created_at"]
        if isinstance(created, str):
            created = datetime.fromisoformat(created)
        updated = row["updated_at"]
        if isinstance(updated, str):
            updated = datetime.fromisoformat(updated)

        return Schedule(
            id=row["id"],
            profile_id=row["profile_id"],
            action=row["action"],
            kind=row["kind"],
            interval_minutes=row["interval_minutes"],
            at_time=row["at_time"],
            days=days,
            run_minutes=row["run_minutes"],
            enabled=bool(row["enabled"]),
            next_run_at=next_run,
            created_at=created,
            updated_at=updated,
        )

    def _row_to_schedule_run(self, row) -> ScheduleRun:
        started = row["started_at"]
        if isinstance(started, str):
            started = datetime.fromisoformat(started)
        finished = row["finished_at"]
        if isinstance(finished, str):
            finished = datetime.fromisoformat(finished)

        return ScheduleRun(
            id=row["id"],
            schedule_id=row["schedule_id"],
            started_at=started,
            finished_at=finished,
            outcome=row["outcome"],
            message=row["message"],
        )

    # --- Helper Serializers ---

    def _row_to_profile(self, row: dict[str, Any]) -> Profile:
        from .models import BrowserSettings

        settings = BrowserSettings(**json.loads(row["browser_settings"]))
        proxy = ProxyConfig(**json.loads(row["proxy_config"])) if row.get("proxy_config") else None
        extensions = json.loads(row["extensions"]) if row.get("extensions") else []
        tags = json.loads(row["tags"]) if row.get("tags") else []
        fingerprint = json.loads(row["fingerprint"]) if row.get("fingerprint") else None

        created = row["created_at"]
        if isinstance(created, str):
            created = datetime.fromisoformat(created)
        updated = row["updated_at"]
        if isinstance(updated, str):
            updated = datetime.fromisoformat(updated)
        last_used = row["last_used"]
        if isinstance(last_used, str):
            last_used = datetime.fromisoformat(last_used)
        deleted_at = row["deleted_at"]
        if isinstance(deleted_at, str):
            deleted_at = datetime.fromisoformat(deleted_at)
        last_synced = row["last_synced_at"]
        if isinstance(last_synced, str):
            last_synced = datetime.fromisoformat(last_synced)

        return Profile(
            id=row["id"],
            name=row["name"],
            user_id=row.get("user_id"),
            group=row.get("group_id"),
            status=ProfileStatus(row["status"]),
            browser_settings=settings,
            proxy=proxy,
            extensions=extensions,
            storage_path=row["storage_path"],
            notes=row.get("notes"),
            created_at=created,
            updated_at=updated,
            last_used=last_used,
            fingerprint=fingerprint,
            row_version=row.get("row_version", 0),
            deleted_at=deleted_at,
            cookies=row.get("cookies"),
            account=row.get("account"),
            is_favorite=bool(row.get("is_favorite")),
            tags=tags,
            sync_status=row.get("sync_status", "synced"),
            last_synced_at=last_synced,
            sync_size_kb=float(row["sync_size_kb"]) if row.get("sync_size_kb") is not None else None,
            cloud_sync_enabled=bool(row.get("cloud_sync_enabled", True)),
        )

    # --- Users & Sessions ---

    async def create_user(
        self,
        user_id: str,
        username: str,
        password_hash: str,
        role: str = "user",
        plan_id: str = "free",
        max_profiles: int = 10,
        max_concurrent: int = 2,
        expires_at: str | None = None,
    ) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO users (id, username, password_hash, role, plan_id, max_profiles, max_concurrent, expires_at, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, CURRENT_TIMESTAMP)
                """,
                user_id,
                username,
                password_hash,
                role,
                plan_id,
                max_profiles,
                max_concurrent,
                datetime.fromisoformat(expires_at) if expires_at else None,
            )

    async def get_user_by_username(self, username: str) -> dict | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, username, password_hash, role, plan_id, max_profiles, max_concurrent, expires_at, status, created_at,
                       api_status, api_app_id, api_app_secret
                FROM users WHERE username = $1
                """,
                username,
            )
            return dict(row) if row else None

    async def get_user_by_id(self, user_id: str) -> dict | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, username, password_hash, role, plan_id, max_profiles, max_concurrent, expires_at, status, created_at,
                       api_status, api_app_id, api_app_secret
                FROM users WHERE id = $1
                """,
                user_id,
            )
            return dict(row) if row else None

    async def update_user_password(self, username: str, password_hash: str) -> bool:
        async with self._pool.acquire() as conn:
            res = await conn.execute(
                "UPDATE users SET password_hash = $1 WHERE username = $2", password_hash, username
            )
            return "UPDATE 1" in res

    async def update_user_api_credentials(
        self, username: str, api_status: str, app_id: str, app_secret: str
    ) -> bool:
        async with self._pool.acquire() as conn:
            res = await conn.execute(
                "UPDATE users SET api_status = $1, api_app_id = $2, api_app_secret = $3 WHERE username = $4",
                api_status, app_id, app_secret, username,
            )
            return "UPDATE 1" in res

    async def update_user_admin(
        self,
        username: str,
        role: str | None = None,
        plan_id: str | None = None,
        max_profiles: int | None = None,
        max_concurrent: int | None = None,
        expires_at: str | None = None,
        status: str | None = None,
    ) -> bool:
        fields = []
        params = []
        idx = 1
        if role is not None:
            fields.append(f"role = ${idx}")
            params.append(role)
            idx += 1
        if plan_id is not None:
            fields.append(f"plan_id = ${idx}")
            params.append(plan_id)
            idx += 1
        if max_profiles is not None:
            fields.append(f"max_profiles = ${idx}")
            params.append(max_profiles)
            idx += 1
        if max_concurrent is not None:
            fields.append(f"max_concurrent = ${idx}")
            params.append(max_concurrent)
            idx += 1
        if expires_at is not None:
            fields.append(f"expires_at = ${idx}")
            params.append(datetime.fromisoformat(expires_at) if expires_at else None)
            idx += 1
        if status is not None:
            fields.append(f"status = ${idx}")
            params.append(status)
            idx += 1
        if not fields:
            return False
        params.append(username)
        query = f"UPDATE users SET {', '.join(fields)} WHERE username = ${idx}"
        async with self._pool.acquire() as conn:
            res = await conn.execute(query, *params)
            return "UPDATE 1" in res

    async def delete_user(self, username: str) -> bool:
        async with self._pool.acquire() as conn:
            res = await conn.execute("DELETE FROM users WHERE username = $1", username)
            return "DELETE 1" in res

    async def count_users(self) -> int:
        async with self._pool.acquire() as conn:
            val = await conn.fetchval("SELECT COUNT(*) FROM users")
            return val or 0

    async def list_users(self) -> list[dict]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, username, role, plan_id, max_profiles, max_concurrent, expires_at, status, created_at, last_login,
                       api_status, api_app_id
                FROM users ORDER BY created_at DESC
                """
            )
            return [dict(r) for r in rows]

    async def create_session(self, token_hash: str, user_id: str, expires_at: datetime) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO sessions (token_hash, user_id, created_at, expires_at)
                VALUES ($1, $2, CURRENT_TIMESTAMP, $3)
                ON CONFLICT (token_hash) DO UPDATE SET expires_at = EXCLUDED.expires_at
                """,
                token_hash, user_id, expires_at,
            )

    async def get_session(self, token_hash: str) -> dict | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT s.token_hash, s.user_id, s.expires_at, u.username
                FROM sessions s JOIN users u ON u.id = s.user_id
                WHERE s.token_hash = $1
                """,
                token_hash,
            )
            return dict(row) if row else None

    async def delete_session(self, token_hash: str) -> bool:
        async with self._pool.acquire() as conn:
            res = await conn.execute("DELETE FROM sessions WHERE token_hash = $1", token_hash)
            return "DELETE 1" in res

    async def delete_expired_sessions(self) -> int:
        async with self._pool.acquire() as conn:
            res = await conn.execute("DELETE FROM sessions WHERE expires_at <= CURRENT_TIMESTAMP")
            parts = res.split()
            return int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0

    # --- Plans ---

    async def list_plans(self) -> list[dict]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM plans ORDER BY price_usdt ASC")
            return [dict(r) for r in rows]

    async def get_plan(self, plan_id: str) -> dict | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM plans WHERE id = $1", plan_id)
            return dict(row) if row else None

    async def save_plan(self, plan: dict) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO plans (id, name, max_profiles, max_concurrent, duration_days, price_usdt, description)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    max_profiles = EXCLUDED.max_profiles,
                    max_concurrent = EXCLUDED.max_concurrent,
                    duration_days = EXCLUDED.duration_days,
                    price_usdt = EXCLUDED.price_usdt,
                    description = EXCLUDED.description
                """,
                plan["id"],
                plan["name"],
                plan["max_profiles"],
                plan["max_concurrent"],
                plan.get("duration_days", 30),
                plan["price_usdt"],
                plan.get("description", ""),
            )

    async def delete_plan(self, plan_id: str) -> bool:
        async with self._pool.acquire() as conn:
            res = await conn.execute("DELETE FROM plans WHERE id = $1", plan_id)
            return "DELETE 1" in res

    # --- Orders ---

    async def create_order(self, order: dict) -> dict:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO orders (id, order_no, user_id, username, plan_id, plan_name, amount_usdt, status, pay_network, pay_address, tx_hash, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, CURRENT_TIMESTAMP)
                """,
                order["id"],
                order["order_no"],
                order["user_id"],
                order["username"],
                order["plan_id"],
                order["plan_name"],
                order["amount_usdt"],
                order.get("status", "pending"),
                order.get("pay_network", "TRC20"),
                order.get("pay_address", ""),
                order.get("tx_hash"),
            )
            return order

    async def get_order(self, order_no: str) -> dict | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM orders WHERE order_no = $1", order_no)
            return dict(row) if row else None

    async def list_orders(self, user_id: str | None = None, limit: int = 100) -> list[dict]:
        async with self._pool.acquire() as conn:
            if user_id:
                rows = await conn.fetch("SELECT * FROM orders WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2", user_id, limit)
            else:
                rows = await conn.fetch("SELECT * FROM orders ORDER BY created_at DESC LIMIT $1", limit)
            return [dict(r) for r in rows]

    async def update_order_status(self, order_no: str, status: str, tx_hash: str | None = None) -> bool:
        async with self._pool.acquire() as conn:
            if tx_hash:
                res = await conn.execute(
                    "UPDATE orders SET status = $1, tx_hash = $2 WHERE order_no = $3",
                    status, tx_hash, order_no,
                )
            else:
                res = await conn.execute(
                    "UPDATE orders SET status = $1 WHERE order_no = $2",
                    status, order_no,
                )
            return "UPDATE 1" in res

    # --- Admin Settings & Dashboard Stats ---

    async def get_admin_settings(self) -> dict[str, str]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT key, value FROM admin_settings")
            return {r["key"]: r["value"] or "" for r in rows}

    async def update_admin_setting(self, key: str, value: str) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO admin_settings (key, value)
                VALUES ($1, $2)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
                """,
                key, value,
            )

    async def get_admin_dashboard_stats(self) -> dict:
        async with self._pool.acquire() as conn:
            user_count = await conn.fetchval("SELECT COUNT(*) FROM users") or 0
            profile_count = await conn.fetchval("SELECT COUNT(*) FROM profiles WHERE deleted_at IS NULL") or 0
            active_running = await conn.fetchval(
                "SELECT COUNT(*) FROM profiles WHERE locked_by IS NOT NULL AND lock_expires > CURRENT_TIMESTAMP"
            ) or 0
            total_orders = await conn.fetchval("SELECT COUNT(*) FROM orders") or 0
            paid_orders = await conn.fetchval("SELECT COUNT(*) FROM orders WHERE status = 'paid'") or 0
            total_revenue = await conn.fetchval("SELECT COALESCE(SUM(amount_usdt), 0) FROM orders WHERE status = 'paid'") or 0.0
            return {
                "user_count": user_count,
                "profile_count": profile_count,
                "active_running": active_running,
                "total_orders": total_orders,
                "paid_orders": paid_orders,
                "total_revenue_usdt": round(float(total_revenue), 2),
            }

