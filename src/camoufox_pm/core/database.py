"""
SQLite storage layer for the Camoufox profile management system.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger
from pydantic import ValidationError

from .crypto import decrypt, encrypt
from .leases import lease_expired
from .models import (
    Profile,
    ProfileGroup,
    ProfileStatus,
    ProxyCheckRecord,
    ProxyConfig,
    Schedule,
    ScheduleRun,
    UsageStats,
    generate_short_id,
)


def _serialize_proxy(proxy: ProxyConfig) -> dict:
    """Serialize a proxy for storage, encrypting the password."""
    data = proxy.model_dump()
    if data.get("password"):
        data["password"] = encrypt(data["password"])
    return data


def _deserialize_proxy(data: dict) -> ProxyConfig:
    """Rebuild a proxy from storage, decrypting the password."""
    if data.get("password"):
        data["password"] = decrypt(data["password"])
    return ProxyConfig(**data)


class StaleWriteError(Exception):
    """A save built on an older version of the row than the one stored.

    The optimistic half of this project's concurrency story; core/leases.py is
    the pessimistic half. A lease answers "who may *run* this profile"; this
    answers "who may *save* this row", which is a different question because a
    profile can be edited while nobody is running it.

    Raised when a version-checked update matched no rows: somebody saved first.
    The later edit is lost loudly instead of silently overwriting theirs.
    """

    def __init__(self, profile_id: str, expected_row_version: int | None = None):
        self.profile_id = profile_id
        self.expected_row_version = expected_row_version
        super().__init__(
            f"Profile {profile_id} was changed by someone else since it was read; "
            "reload it and apply the edit again"
        )


class DatabaseManager:
    """Async-friendly SQLite database manager."""

    def __init__(self, db_path: str = "data/profiles.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection: sqlite3.Connection = None  # type: ignore[assignment]
        logger.info(f"DatabaseManager initialized with database: {self.db_path}")

    async def initialize(self):
        """Initialize the database and create tables (safe to call twice)."""
        if self._connection is not None:
            return
        self._connection = sqlite3.connect(str(self.db_path), timeout=30.0)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")

        await self._create_tables()
        await self._migrate()
        await self._create_indexes()
        logger.info("Database initialized")

    async def _migrate(self):
        """Bring an existing database up to the current schema.

        Tables are created with ``CREATE TABLE IF NOT EXISTS``, so a database made
        by an older version keeps its original columns forever. Each entry here
        adds one column when it is missing; adding a column is safe to re-run and
        never touches existing rows.
        """
        added_columns = {
            "profiles": [
                ("fingerprint", "TEXT"),
                ("proxy_check", "TEXT"),
                ("locked_by", "TEXT"),
                ("lock_expires", "TIMESTAMP"),
                ("row_version", "BIGINT NOT NULL DEFAULT 0"),
                ("deleted_at", "TIMESTAMP"),
                ("user_id", "TEXT"),
            ],
            "profile_groups": [
                ("user_id", "TEXT"),
            ],
            "schedules": [
                ("user_id", "TEXT"),
            ],
            "users": [
                ("role", "TEXT DEFAULT 'user'"),
                ("plan_id", "TEXT DEFAULT 'free'"),
                ("max_profiles", "INTEGER DEFAULT 10"),
                ("max_concurrent", "INTEGER DEFAULT 2"),
                ("expires_at", "TIMESTAMP"),
                ("status", "TEXT DEFAULT 'active'"),
                ("api_status", "TEXT DEFAULT 'disabled'"),
                ("api_app_id", "TEXT"),
                ("api_app_secret", "TEXT"),
            ],
        }
        for table, columns in added_columns.items():
            cursor = self._connection.execute(f"PRAGMA table_info({table})")
            existing = {row["name"] for row in cursor.fetchall()}
            for name, column_type in columns:
                if name in existing:
                    continue
                self._connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {column_type}")
                logger.info(f"Migrated {table}: added column {name}")

        # 确保现有管理员账号获得超管权限
        self._connection.execute("UPDATE users SET role = 'admin', max_profiles = 99999, max_concurrent = 999 WHERE username IN ('admin', 'fgwl')")
        self._connection.commit()

    async def _create_tables(self):
        """Create the database tables."""
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS recovery_lock (
                id INTEGER PRIMARY KEY CHECK(id = 1), holder TEXT, expires TIMESTAMP
            )
        """)
        self._connection.execute("INSERT OR IGNORE INTO recovery_lock (id) VALUES (1)")

        # Profiles table
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                group_id TEXT,
                status TEXT DEFAULT 'active',
                browser_settings TEXT NOT NULL,
                proxy_config TEXT,
                extensions TEXT,
                storage_path TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP,
                fingerprint TEXT,
                proxy_check TEXT,
                locked_by TEXT,
                lock_expires TIMESTAMP,
                row_version BIGINT NOT NULL DEFAULT 0,
                deleted_at TIMESTAMP
            )
        """)

        # Dynamic migrations for commercial anti-detect features
        for col, col_type in [
            ("cookies", "TEXT"),
            ("account", "TEXT"),
            ("is_favorite", "INTEGER DEFAULT 0"),
            ("tags", "TEXT DEFAULT '[]'"),
            ("kernel_version", "TEXT DEFAULT '155.0.8059'"),
            ("sync_status", "TEXT DEFAULT 'synced'"),
            ("last_synced_at", "TIMESTAMP"),
            ("sync_size_kb", "REAL"),
            ("cloud_sync_enabled", "INTEGER DEFAULT 1"),
        ]:
            try:
                self._connection.execute(f"ALTER TABLE profiles ADD COLUMN {col} {col_type};")
            except Exception:
                pass

        # Profile groups table
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS profile_groups (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                profile_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Usage statistics table
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS usage_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id TEXT NOT NULL,
                action TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                duration INTEGER,
                success BOOLEAN DEFAULT 1,
                details TEXT
            )
        """)

        # User accounts for the web UI. Their mere existence turns login on, so a
        # database without rows here behaves exactly as before the table existed.
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Login sessions, keyed by the SHA-256 of the cookie token — the token
        # itself is never stored, so this table cannot be replayed if leaked.
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL
            )
        """)

        # Scheduled tasks. New tables need no _migrate entry: IF NOT EXISTS adds
        # them to an existing database without touching what is already there.
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS schedules (
                id TEXT PRIMARY KEY,
                profile_id TEXT NOT NULL,
                action TEXT NOT NULL,
                kind TEXT NOT NULL,
                interval_minutes INTEGER,
                at_time TEXT,
                days TEXT,
                run_minutes INTEGER,
                enabled BOOLEAN DEFAULT 1,
                next_run_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS schedule_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                schedule_id TEXT NOT NULL,
                started_at TIMESTAMP NOT NULL,
                finished_at TIMESTAMP,
                outcome TEXT NOT NULL,
                message TEXT
            )
        """)

        # Plans table for tiered subscriptions
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS plans (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                max_profiles INTEGER NOT NULL,
                max_concurrent INTEGER NOT NULL,
                duration_days INTEGER NOT NULL,
                price_usdt REAL NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Seed initial default plans
        self._connection.execute("""
            INSERT OR IGNORE INTO plans (id, name, max_profiles, max_concurrent, duration_days, price_usdt, description)
            VALUES 
                ('free', '体验版', 5, 1, 3, 0.0, '初次体验指纹浏览器功能，赠送 3 天试用'),
                ('basic', '基础版', 20, 2, 30, 10.0, '适合个人卖家或多号轻度运营，支持 20 个独立环境'),
                ('pro', '专业版', 60, 5, 30, 28.0, '适合电商工作室，支持 60 个环境及 5 并发多开'),
                ('enterprise', '企业版', 200, 10, 30, 79.0, '适合规模化多账号矩阵，支持 200 个环境与 10 并发')
        """)

        # USDT Orders table
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                order_no TEXT NOT NULL UNIQUE,
                user_id TEXT NOT NULL,
                username TEXT NOT NULL,
                plan_id TEXT NOT NULL,
                plan_name TEXT NOT NULL,
                amount_usdt REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                pay_network TEXT DEFAULT 'TRC20',
                pay_address TEXT,
                tx_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                paid_at TIMESTAMP
            )
        """)

        # Admin / Payment settings
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS admin_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # Proxies table for proxy pool management
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS proxies (
                id TEXT PRIMARY KEY,
                name TEXT,
                type TEXT NOT NULL DEFAULT 'http',
                server TEXT NOT NULL,
                port INTEGER,
                username TEXT,
                password TEXT,
                status TEXT DEFAULT 'uncheck',
                latency_ms INTEGER,
                country TEXT,
                city TEXT,
                ip TEXT,
                user_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_checked_at TIMESTAMP
            )
        """)

        # Extensions table for plugin management
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS extensions (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                version TEXT,
                icon_url TEXT,
                description TEXT,
                category TEXT DEFAULT 'general',
                crx_id TEXT,
                download_url TEXT,
                local_path TEXT,
                is_preset BOOLEAN DEFAULT 0,
                enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Seed and update preset extensions with embedded vector icons
        from camoufox_pm.core.preset_icons import PRESET_CATALOG
        for item in PRESET_CATALOG:
            self._connection.execute("""
                INSERT INTO extensions (id, name, version, icon_url, description, category, crx_id, is_preset, enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    icon_url = excluded.icon_url,
                    description = excluded.description,
                    category = excluded.category,
                    crx_id = excluded.crx_id,
                    version = excluded.version
                WHERE is_preset = 1
            """, (
                item["id"],
                item["name"],
                item["version"],
                item["icon_url"],
                item["description"],
                item["category"],
                item["crx_id"],
            ))

        # Client releases for desktop application update management
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS client_releases (
                id TEXT PRIMARY KEY,
                version TEXT NOT NULL UNIQUE,
                title TEXT,
                changelog TEXT,
                changelog_en TEXT,
                min_version TEXT DEFAULT '1.0.0',
                is_force_update BOOLEAN DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                mac_arm64_url TEXT,
                mac_x64_url TEXT,
                win_x64_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Kernel releases for multi-engine anti-detect kernel cloud repository
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS kernel_releases (
                id TEXT PRIMARY KEY,
                engine TEXT NOT NULL,
                version TEXT NOT NULL UNIQUE,
                display_name TEXT,
                changelog TEXT,
                is_recommended BOOLEAN DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                mac_arm64_url TEXT,
                mac_arm64_sha256 TEXT,
                mac_x64_url TEXT,
                mac_x64_sha256 TEXT,
                win_x64_url TEXT,
                win_x64_sha256 TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Seed default kernel releases (Chrome 155 and Camoufox 135)
        self._connection.execute("""
            INSERT OR IGNORE INTO kernel_releases (
                id, engine, version, display_name, changelog, is_recommended, is_active,
                mac_arm64_url, win_x64_url
            ) VALUES 
            (
                'kr_chrom_155', 'chromium', '155.0.8059', 'Chrome 155 (首发基准原生防关联内核)',
                '原生集成 Canvas/WebGL 抗指纹与移动端视口沙盒锁，修复 CDP 内存泄漏', 1, 1,
                'https://github.com/hkxuepf/camoufox/releases/download/v155.0/chromium-155.0.8059-mac-arm64.tar.gz',
                'https://github.com/hkxuepf/camoufox/releases/download/v155.0/chromium-155.0.8059-win-x64.zip'
            ),
            (
                'kr_cloak_146', 'chromium', '146.0.7680', 'Chrome 146 (CloakBrowser 87项C++补丁纯净无锁内核)',
                '基于 Chromium 146 纯离线无锁免鉴权运行，深度剥离所有商业鉴权与并发限制', 0, 1,
                'https://github.com/hkxuepf/camoufox/releases/download/v146.0/cloak-chromium-146.0.7680-mac-arm64.tar.gz',
                'https://github.com/hkxuepf/camoufox/releases/download/v146.0/cloak-chromium-146.0.7680-win-x64.zip'
            ),
            (
                'kr_fox_135', 'camoufox', '135.0-beta.36', 'Camoufox 135 (Gecko 原生防关联内核)',
                '基于 Firefox 135 ESR 真实渲染引擎，完美支持桌面指纹仿真', 1, 1,
                'https://github.com/hkxuepf/camoufox/releases/download/v135.0/camoufox-135.0-mac-arm64.zip',
                'https://github.com/hkxuepf/camoufox/releases/download/v135.0/camoufox-135.0-win-x64.zip'
            )
        """)

        # Profile snapshots table (时光机与快照历史)
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS profile_snapshots (
                id TEXT PRIMARY KEY,
                profile_id TEXT NOT NULL,
                snapshot_name TEXT,
                size_kb REAL,
                r2_key TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._connection.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_profile ON profile_snapshots(profile_id)")

        self._connection.commit()

    async def _create_indexes(self):
        """Create indexes to optimize queries."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_profiles_group ON profiles(group_id)",
            "CREATE INDEX IF NOT EXISTS idx_profiles_status ON profiles(status)",
            "CREATE INDEX IF NOT EXISTS idx_profiles_created ON profiles(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_usage_stats_profile ON usage_stats(profile_id)",
            "CREATE INDEX IF NOT EXISTS idx_usage_stats_timestamp ON usage_stats(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_schedules_profile ON schedules(profile_id)",
            "CREATE INDEX IF NOT EXISTS idx_schedule_runs_schedule ON schedule_runs(schedule_id)",
        ]

        for index_sql in indexes:
            self._connection.execute(index_sql)

        self._connection.commit()

    # --- Profiles ---

    def _profile_columns(self, profile: Profile) -> tuple:
        """The column values a save owns, in the order both writers use.

        Shared so the upsert and the version-checked update cannot drift apart:
        a column added to one and forgotten in the other would be written on a
        create and silently ignored on an edit.
        """
        return (
            profile.id,
            profile.name,
            profile.group,
            profile.status.value if hasattr(profile.status, "value") else profile.status,
            json.dumps(profile.browser_settings.model_dump()),
            json.dumps(_serialize_proxy(profile.proxy)) if profile.proxy else None,
            json.dumps(profile.extensions),
            profile.storage_path,
            profile.notes,
            profile.created_at.isoformat(),
            profile.updated_at.isoformat(),
            profile.last_used.isoformat() if profile.last_used else None,
            json.dumps(profile.fingerprint) if profile.fingerprint else None,
            profile.proxy_check.model_dump_json() if profile.proxy_check else None,
            profile.user_id,
            profile.cookies,
            profile.account,
            1 if profile.is_favorite else 0,
            json.dumps(profile.tags or []),
        )

    def _upsert_profile(self, profile: Profile) -> None:
        """Insert the row, or overwrite the columns a save owns."""
        self._connection.execute(
            """
            INSERT INTO profiles (
                id, name, group_id, status, browser_settings, proxy_config,
                extensions, storage_path, notes, created_at, updated_at, last_used,
                fingerprint, proxy_check, user_id, cookies, account, is_favorite, tags
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                group_id = excluded.group_id,
                status = excluded.status,
                browser_settings = excluded.browser_settings,
                proxy_config = excluded.proxy_config,
                extensions = excluded.extensions,
                storage_path = excluded.storage_path,
                notes = excluded.notes,
                created_at = excluded.created_at,
                updated_at = excluded.updated_at,
                last_used = excluded.last_used,
                fingerprint = excluded.fingerprint,
                proxy_check = excluded.proxy_check,
                user_id = COALESCE(excluded.user_id, profiles.user_id),
                cookies = excluded.cookies,
                account = excluded.account,
                is_favorite = excluded.is_favorite,
                tags = excluded.tags
        """,
            self._profile_columns(profile),
        )

    async def save_profile(self, profile: Profile, expected_row_version: int | None = None):
        """Save a profile."""
        profile.updated_at = datetime.now()
        if expected_row_version is None:
            self._upsert_profile(profile)
        else:
            self._save_profile_if_unchanged(profile, expected_row_version)
        self._connection.commit()
        logger.debug(f"Profile {profile.name} saved")

    def _save_profile_if_unchanged(self, profile: Profile, expected_row_version: int) -> None:
        """One guarded statement: update only while the version still matches."""
        cursor = self._connection.execute(
            """
            UPDATE profiles SET
                name = ?, group_id = ?, status = ?, browser_settings = ?,
                proxy_config = ?, extensions = ?, storage_path = ?, notes = ?,
                created_at = ?, updated_at = ?, last_used = ?, fingerprint = ?,
                proxy_check = ?, user_id = COALESCE(?, user_id),
                cookies = ?, account = ?, is_favorite = ?, tags = ?,
                row_version = row_version + 1
            WHERE id = ? AND row_version = ? AND deleted_at IS NULL
            """,
            (*self._profile_columns(profile)[1:], profile.id, expected_row_version),
        )
        if cursor.rowcount == 0:
            raise StaleWriteError(profile.id, expected_row_version)
        # Keep the caller's copy in step with the row it just wrote: the next
        # edit reads its row_version, and it must be the one this write produced.
        profile.row_version = expected_row_version + 1

    async def get_profile(self, profile_id: str, include_deleted: bool = False) -> Profile | None:
        """Get an active profile, or explicitly include the trash."""
        query = "SELECT * FROM profiles WHERE id = ?"
        if not include_deleted:
            query += " AND deleted_at IS NULL"
        cursor = self._connection.execute(query, (profile_id,))
        row = cursor.fetchone()

        if row:
            return self._row_to_profile(row)
        return None

    async def update_profile(self, profile: Profile, expected_row_version: int | None = None):
        """Update a profile, optionally guarded against a concurrent save."""
        await self.save_profile(profile, expected_row_version)
        logger.debug(f"Profile {profile.name} updated")

    async def set_proxy_check(self, profile_id: str, record: ProxyCheckRecord | None) -> None:
        """Write only the proxy check, leaving every other column alone.

        A check takes seconds — up to thirty against a proxy that never answers —
        and `save_profile` replaces the whole row. Writing back a Profile read
        before that wait would revert anything edited during it, which is the
        hazard already noted in profile_manager.launch_browser. This also keeps a
        check from touching `updated_at`: asking a proxy a question is not an
        edit, and a bulk check should not make a selection look modified.
        """
        self._connection.execute(
            "UPDATE profiles SET proxy_check = ? WHERE id = ?",
            (record.model_dump_json() if record else None, profile_id),
        )
        self._connection.commit()

    async def set_launch_pin(
        self, profile_id: str, fingerprint: dict | None, last_used: datetime
    ) -> None:
        """Write only what a launch owns: the pinned machine and the timestamp.

        A targeted write for the same reason as ``set_proxy_check``. A launch
        resolves a fingerprint, which can fetch the uBlock addon over the
        network on a fresh install, and writing a whole Profile back after that
        would revert anything edited while it ran. Naming the two columns a
        launch actually owns removes the hazard rather than guarding against it,
        and leaves the row's version alone: starting a browser is not an edit of
        the profile, so it must not make a concurrent editor's save go stale.
        """
        self._connection.execute(
            "UPDATE profiles SET fingerprint = ?, last_used = ?, updated_at = ? WHERE id = ?",
            (
                json.dumps(fingerprint) if fingerprint else None,
                last_used.isoformat(),
                last_used.isoformat(),
                profile_id,
            ),
        )
        self._connection.commit()

    async def set_cloud_sync_status(
        self,
        profile_id: str,
        sync_status: str,
        size_kb: float | None = None,
        last_synced_at: datetime | None = None,
    ) -> None:
        """Update cloud sync status, size and timestamp without bumping row_version."""
        now = (last_synced_at or datetime.now()).isoformat() if sync_status == "synced" else None
        if size_kb is not None and now is not None:
            self._connection.execute(
                "UPDATE profiles SET sync_status = ?, sync_size_kb = ?, last_synced_at = ? WHERE id = ?",
                (sync_status, size_kb, now, profile_id),
            )
        elif sync_status == "syncing":
            self._connection.execute(
                "UPDATE profiles SET sync_status = ? WHERE id = ?",
                (sync_status, profile_id),
            )
        else:
            self._connection.execute(
                "UPDATE profiles SET sync_status = ? WHERE id = ?",
                (sync_status, profile_id),
            )
        self._connection.commit()

    async def delete_profile(self, profile_id: str) -> bool:
        """Delete a profile, and the schedules that would otherwise fire against it."""
        self._connection.execute(
            "DELETE FROM schedule_runs WHERE schedule_id IN "
            "(SELECT id FROM schedules WHERE profile_id = ?)",
            (profile_id,),
        )
        self._connection.execute("DELETE FROM schedules WHERE profile_id = ?", (profile_id,))
        cursor = self._connection.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
        self._connection.commit()
        deleted = cursor.rowcount > 0

        if deleted:
            logger.debug(f"Profile {profile_id} deleted")

        return deleted

    async def set_profile_trashed(self, profile_id: str, trashed: bool) -> bool:
        """Retain the row and directory; pause schedules when moving into trash."""
        with self._connection:
            cursor = self._connection.execute(
                "UPDATE profiles SET deleted_at = ?, row_version = row_version + 1 "
                "WHERE id = ? AND deleted_at IS " + ("NULL" if trashed else "NOT NULL"),
                (datetime.now().isoformat() if trashed else None, profile_id),
            )
            if cursor.rowcount and trashed:
                self._connection.execute(
                    "UPDATE schedules SET enabled = 0 WHERE profile_id = ?", (profile_id,)
                )
        return cursor.rowcount > 0

    async def list_profiles(
        self, filters: dict | None = None, limit: int | None = None, offset: int = 0
    ) -> list[Profile]:
        """List profiles with optional filtering."""
        query = "SELECT * FROM profiles WHERE " + (
            "deleted_at IS NOT NULL"
            if filters and filters.get("trashed")
            else "1=1"
            if filters and filters.get("include_deleted")
            else "deleted_at IS NULL"
        )
        params = []

        if filters:
            if "user_id" in filters and filters["user_id"]:
                query += " AND user_id = ?"
                params.append(filters["user_id"])
            if "group" in filters:
                query += " AND group_id = ?"
                params.append(filters["group"])
            if "status" in filters:
                query += " AND status = ?"
                params.append(filters["status"])
            if "name_like" in filters:
                query += " AND name LIKE ?"
                params.append(f"%{filters['name_like']}%")

        query += " ORDER BY created_at DESC"

        # SQLite will not take an OFFSET without a LIMIT, so an offset on its own
        # used to be dropped and the caller silently got the first page back.
        if limit or offset:
            query += " LIMIT ?"
            params.append(limit if limit else -1)
        if offset:
            query += " OFFSET ?"
            params.append(offset)

        cursor = self._connection.execute(query, params)
        rows = cursor.fetchall()

        return [self._row_to_profile(row) for row in rows]

    async def count_profiles(self, filters: dict | None = None) -> int:
        """Count profiles."""
        query = "SELECT COUNT(*) FROM profiles WHERE deleted_at IS NULL"
        params = []

        if filters:
            if "user_id" in filters and filters["user_id"]:
                query += " AND user_id = ?"
                params.append(filters["user_id"])
            if "group" in filters:
                query += " AND group_id = ?"
                params.append(filters["group"])
            if "status" in filters:
                query += " AND status = ?"
                params.append(filters["status"])

        cursor = self._connection.execute(query, params)
        return cursor.fetchone()[0]

    # --- Profile groups ---

    async def save_profile_group(self, group: ProfileGroup):
        """Save a profile group."""
        self._connection.execute(
            """
            INSERT OR REPLACE INTO profile_groups (
                id, name, description, profile_count, created_at
            ) VALUES (?, ?, ?, ?, ?)
        """,
            (
                group.id,
                group.name,
                group.description,
                group.profile_count,
                group.created_at.isoformat(),
            ),
        )
        self._connection.commit()
        logger.debug(f"Group {group.name} saved")

    async def list_profile_groups(self) -> list[ProfileGroup]:
        """List all groups."""
        cursor = self._connection.execute("""
            SELECT pg.*, COUNT(p.id) as actual_count
            FROM profile_groups pg
            LEFT JOIN profiles p ON pg.id = p.group_id AND p.deleted_at IS NULL
            GROUP BY pg.id
            ORDER BY pg.created_at DESC
        """)
        rows = cursor.fetchall()

        groups = []
        for row in rows:
            group = ProfileGroup(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                profile_count=row["actual_count"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            groups.append(group)

        return groups

    async def delete_profile_group(self, group_id: str) -> bool:
        """Delete a profile group."""
        # Ungroup the profiles that belonged to this group
        self._connection.execute(
            "UPDATE profiles SET group_id = NULL WHERE group_id = ?", (group_id,)
        )

        # Delete the group
        cursor = self._connection.execute("DELETE FROM profile_groups WHERE id = ?", (group_id,))
        self._connection.commit()

        return cursor.rowcount > 0

    # --- Statistics ---

    async def log_usage(self, usage_stats: UsageStats):
        """Record a usage statistic."""
        self._connection.execute(
            """
            INSERT INTO usage_stats (
                profile_id, action, timestamp, duration, success, details
            ) VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                usage_stats.profile_id,
                usage_stats.action,
                usage_stats.timestamp.isoformat(),
                usage_stats.duration,
                usage_stats.success,
                json.dumps(usage_stats.details) if usage_stats.details else None,
            ),
        )
        self._connection.commit()

    async def get_profile_usage_stats(self, profile_id: str, limit: int = 100) -> list[UsageStats]:
        """Get usage statistics for a profile."""
        cursor = self._connection.execute(
            """
            SELECT * FROM usage_stats
            WHERE profile_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """,
            (profile_id, limit),
        )

        rows = cursor.fetchall()
        stats = []

        for row in rows:
            stat = UsageStats(
                id=row["id"],
                profile_id=row["profile_id"],
                action=row["action"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                duration=row["duration"],
                success=bool(row["success"]),
                details=json.loads(row["details"]) if row["details"] else None,
            )
            stats.append(stat)

        return stats

    # --- Users and sessions ---

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
        """Create a user; raises ``ValueError`` when the username is taken."""
        try:
            self._connection.execute(
                """
                INSERT INTO users (id, username, password_hash, role, plan_id, max_profiles, max_concurrent, expires_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    username,
                    password_hash,
                    role,
                    plan_id,
                    max_profiles,
                    max_concurrent,
                    expires_at,
                    datetime.now().isoformat(),
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"User {username!r} already exists") from exc
        self._connection.commit()
        # Deliberately logs the name only, never the hash.
        logger.info(f"User {username} created with role={role}")

    async def get_user_by_username(self, username: str) -> dict | None:
        cursor = self._connection.execute(
            """
            SELECT id, username, password_hash, role, plan_id, max_profiles, max_concurrent, expires_at, status, created_at,
                   api_status, api_app_id, api_app_secret
            FROM users WHERE username = ?
            """,
            (username,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    async def get_user_by_id(self, user_id: str) -> dict | None:
        cursor = self._connection.execute(
            """
            SELECT id, username, password_hash, role, plan_id, max_profiles, max_concurrent, expires_at, status, created_at,
                   api_status, api_app_id, api_app_secret
            FROM users WHERE id = ?
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    async def update_user_api_credentials(
        self, username: str, api_status: str, app_id: str, app_secret: str
    ) -> bool:
        cursor = self._connection.execute(
            "UPDATE users SET api_status = ?, api_app_id = ?, api_app_secret = ? WHERE username = ?",
            (api_status, app_id, app_secret, username),
        )
        self._connection.commit()
        return cursor.rowcount > 0

    async def update_user_password(self, username: str, password_hash: str) -> bool:
        cursor = self._connection.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?", (password_hash, username)
        )
        self._connection.commit()
        return cursor.rowcount > 0

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
        updates = []
        params = []
        if role is not None:
            updates.append("role = ?")
            params.append(role)
        if plan_id is not None:
            updates.append("plan_id = ?")
            params.append(plan_id)
        if max_profiles is not None:
            updates.append("max_profiles = ?")
            params.append(max_profiles)
        if max_concurrent is not None:
            updates.append("max_concurrent = ?")
            params.append(max_concurrent)
        if expires_at is not None:
            updates.append("expires_at = ?")
            params.append(expires_at)
        if status is not None:
            updates.append("status = ?")
            params.append(status)

        if not updates:
            return False

        params.append(username)
        cursor = self._connection.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE username = ?", params
        )
        self._connection.commit()
        return cursor.rowcount > 0

    async def delete_user(self, username: str) -> bool:
        """Delete a user; the foreign key cascades their open sessions away."""
        cursor = self._connection.execute("DELETE FROM users WHERE username = ?", (username,))
        self._connection.commit()
        return cursor.rowcount > 0

    async def count_users(self) -> int:
        cursor = self._connection.execute("SELECT COUNT(*) FROM users")
        return cursor.fetchone()[0]

    async def list_users(self) -> list[dict]:
        cursor = self._connection.execute(
            """
            SELECT id, username, role, plan_id, max_profiles, max_concurrent, expires_at, status, created_at
            FROM users ORDER BY created_at DESC
            """
        )
        return [dict(row) for row in cursor.fetchall()]

    async def create_session(self, token_hash: str, user_id: str, expires_at: datetime) -> None:
        self._connection.execute(
            "INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token_hash, user_id, datetime.now().isoformat(), expires_at.isoformat()),
        )
        self._connection.commit()

    async def get_session(self, token_hash: str) -> dict | None:
        cursor = self._connection.execute(
            """
            SELECT s.token_hash, s.user_id, s.expires_at, u.username
            FROM sessions s JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ?
            """,
            (token_hash,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    async def delete_session(self, token_hash: str) -> bool:
        cursor = self._connection.execute(
            "DELETE FROM sessions WHERE token_hash = ?", (token_hash,)
        )
        self._connection.commit()
        return cursor.rowcount > 0

    async def delete_expired_sessions(self) -> int:
        cursor = self._connection.execute(
            "DELETE FROM sessions WHERE expires_at <= ?", (datetime.now().isoformat(),)
        )
        self._connection.commit()
        return cursor.rowcount

    # --- Plans ---
    async def list_plans(self) -> list[dict]:
        cursor = self._connection.execute("SELECT * FROM plans ORDER BY price_usdt ASC")
        return [dict(row) for row in cursor.fetchall()]

    async def get_plan(self, plan_id: str) -> dict | None:
        cursor = self._connection.execute("SELECT * FROM plans WHERE id = ?", (plan_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    async def save_plan(self, plan: dict) -> None:
        self._connection.execute(
            """
            INSERT OR REPLACE INTO plans (id, name, max_profiles, max_concurrent, duration_days, price_usdt, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                plan["id"],
                plan["name"],
                plan["max_profiles"],
                plan["max_concurrent"],
                plan["duration_days"],
                plan["price_usdt"],
                plan.get("description", ""),
            ),
        )
        self._connection.commit()

    async def delete_plan(self, plan_id: str) -> bool:
        cursor = self._connection.execute("DELETE FROM plans WHERE id = ?", (plan_id,))
        self._connection.commit()
        return cursor.rowcount > 0

    # --- Orders ---
    async def create_order(self, order: dict) -> dict:
        self._connection.execute(
            """
            INSERT INTO orders (id, order_no, user_id, username, plan_id, plan_name, amount_usdt, status, pay_network, pay_address, tx_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
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
                order.get("tx_hash", None),
                order.get("created_at", datetime.now().isoformat()),
            ),
        )
        self._connection.commit()
        return order

    async def get_order(self, order_no: str) -> dict | None:
        cursor = self._connection.execute("SELECT * FROM orders WHERE order_no = ?", (order_no,))
        row = cursor.fetchone()
        return dict(row) if row else None

    async def list_orders(self, user_id: str | None = None, limit: int = 100) -> list[dict]:
        if user_id:
            cursor = self._connection.execute(
                "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit),
            )
        else:
            cursor = self._connection.execute(
                "SELECT * FROM orders ORDER BY created_at DESC LIMIT ?", (limit,)
            )
        return [dict(row) for row in cursor.fetchall()]

    async def update_order_status(
        self, order_no: str, status: str, tx_hash: str | None = None
    ) -> bool:
        updates = ["status = ?"]
        params = [status]
        if status == "paid":
            updates.append("paid_at = ?")
            params.append(datetime.now().isoformat())
        if tx_hash:
            updates.append("tx_hash = ?")
            params.append(tx_hash)
        params.append(order_no)

        cursor = self._connection.execute(
            f"UPDATE orders SET {', '.join(updates)} WHERE order_no = ?", params
        )
        self._connection.commit()
        return cursor.rowcount > 0

    # --- Admin Settings & Stats ---
    async def get_admin_settings(self) -> dict[str, str]:
        cursor = self._connection.execute("SELECT key, value FROM admin_settings")
        return {row["key"]: row["value"] or "" for row in cursor.fetchall()}

    async def update_admin_setting(self, key: str, value: str) -> None:
        self._connection.execute(
            "INSERT OR REPLACE INTO admin_settings (key, value) VALUES (?, ?)", (key, value)
        )
        self._connection.commit()

    async def get_admin_dashboard_stats(self) -> dict:
        user_count = self._connection.execute("SELECT COUNT(*) FROM users WHERE role != 'admin'").fetchone()[0]
        admin_count = self._connection.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'").fetchone()[0]
        profile_count = self._connection.execute(
            "SELECT COUNT(*) FROM profiles WHERE deleted_at IS NULL"
        ).fetchone()[0]
        active_running = self._connection.execute(
            "SELECT COUNT(*) FROM profiles WHERE locked_by IS NOT NULL AND julianday(lock_expires) > julianday('now')"
        ).fetchone()[0]
        total_orders = self._connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        paid_orders = self._connection.execute(
            "SELECT COUNT(*) FROM orders WHERE status = 'paid'"
        ).fetchone()[0]
        total_revenue = self._connection.execute(
            "SELECT COALESCE(SUM(amount_usdt), 0) FROM orders WHERE status = 'paid'"
        ).fetchone()[0]
        return {
            "user_count": user_count,
            "admin_count": admin_count,
            "profile_count": profile_count,
            "active_running": active_running,
            "total_orders": total_orders,
            "paid_orders": paid_orders,
            "total_revenue_usdt": round(float(total_revenue), 2),
        }

    # --- Schedules ---

    async def save_schedule(self, schedule: Schedule):
        """Insert or replace a schedule."""
        self._connection.execute(
            """
            INSERT OR REPLACE INTO schedules (
                id, profile_id, action, kind, interval_minutes, at_time, days,
                run_minutes, enabled, next_run_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                schedule.id,
                schedule.profile_id,
                schedule.action,
                schedule.kind,
                schedule.interval_minutes,
                schedule.at_time,
                json.dumps(schedule.days) if schedule.days else None,
                schedule.run_minutes,
                schedule.enabled,
                schedule.next_run_at.isoformat() if schedule.next_run_at else None,
                schedule.created_at.isoformat(),
                schedule.updated_at.isoformat(),
            ),
        )
        self._connection.commit()

    async def get_schedule(self, schedule_id: str) -> Schedule | None:
        """Get a schedule by ID."""
        cursor = self._connection.execute("SELECT * FROM schedules WHERE id = ?", (schedule_id,))
        row = cursor.fetchone()
        return self._row_to_schedule(row) if row else None

    async def list_schedules(self, profile_id: str | None = None) -> list[Schedule]:
        """List schedules, oldest first so the UI order is stable."""
        if profile_id:
            cursor = self._connection.execute(
                "SELECT * FROM schedules WHERE profile_id = ? ORDER BY created_at",
                (profile_id,),
            )
        else:
            cursor = self._connection.execute("SELECT * FROM schedules ORDER BY created_at")
        return [self._row_to_schedule(row) for row in cursor.fetchall()]

    async def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule and its run history."""
        self._connection.execute("DELETE FROM schedule_runs WHERE schedule_id = ?", (schedule_id,))
        cursor = self._connection.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
        self._connection.commit()
        return cursor.rowcount > 0

    async def log_schedule_run(self, run: ScheduleRun, keep: int = 20) -> ScheduleRun:
        """Record one firing and prune the history to the newest ``keep`` rows.

        Bounded per schedule rather than by age: an every-five-minutes schedule
        would otherwise write hundreds of rows a day into a database that also
        holds the profiles.
        """
        cursor = self._connection.execute(
            """
            INSERT INTO schedule_runs (schedule_id, started_at, finished_at, outcome, message)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                run.schedule_id,
                run.started_at.isoformat(),
                run.finished_at.isoformat() if run.finished_at else None,
                run.outcome,
                run.message,
            ),
        )
        run.id = cursor.lastrowid
        self._connection.execute(
            """
            DELETE FROM schedule_runs WHERE schedule_id = ? AND id NOT IN (
                SELECT id FROM schedule_runs WHERE schedule_id = ? ORDER BY id DESC LIMIT ?
            )
        """,
            (run.schedule_id, run.schedule_id, keep),
        )
        self._connection.commit()
        return run

    async def list_schedule_runs(self, schedule_id: str, limit: int = 20) -> list[ScheduleRun]:
        """Get the newest runs of a schedule, newest first."""
        cursor = self._connection.execute(
            "SELECT * FROM schedule_runs WHERE schedule_id = ? ORDER BY id DESC LIMIT ?",
            (schedule_id, limit),
        )
        return [
            ScheduleRun(
                id=row["id"],
                schedule_id=row["schedule_id"],
                started_at=datetime.fromisoformat(row["started_at"]),
                finished_at=(
                    datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None
                ),
                outcome=row["outcome"],
                message=row["message"],
            )
            for row in cursor.fetchall()
        ]

    # --- Leases ---

    # See core/leases.py for what a lease is and why it exists. Every method
    # here is a single statement whose WHERE clause carries the decision, so
    # SQLite's write lock — not the application — picks the winner when two
    # processes ask at once.

    async def acquire_lease(
        self, profile_id: str, holder: str, ttl_seconds: int, include_deleted: bool = False
    ) -> bool:
        """Take the lease on a profile, if it is free. Never blocks.

        The three arms of the guard are the three ways a lease may be taken:
        nobody holds it, the holder's TTL ran out (their machine is gone), or
        we already hold it. That last arm makes re-acquisition idempotent — a
        process must be able to pick its own lease back up instead of waiting
        out a TTL it set itself.

        Returns ``False`` without touching the row when someone else holds an
        unexpired lease; callers turn that into ``ProfileLocked``.
        """
        cursor = self._connection.execute(
            """
            UPDATE profiles
               SET locked_by = ?,
                   lock_expires = datetime('now', '+' || ? || ' seconds')
             WHERE id = ? AND (deleted_at IS NULL OR ?)
               AND (locked_by IS NULL
                    OR locked_by = ?
                    OR julianday(lock_expires) < julianday('now'))
            """,
            (holder, ttl_seconds, profile_id, include_deleted, holder),
        )
        # Without the commit the lease lives inside this connection's open
        # transaction, where no other process can see it — the opposite of
        # what it is for.
        self._connection.commit()
        return cursor.rowcount > 0

    async def renew_lease(self, profile_ids: list[str], holder: str, ttl_seconds: int) -> int:
        """Push out the expiry of the leases we still hold; returns how many.

        A profile missing from the count has been taken over or has expired.
        The caller treats that as a lost lease rather than trying to win it
        back: something else is already driving that identity.
        """
        if not profile_ids:
            return 0
        placeholders = ",".join("?" for _ in profile_ids)
        cursor = self._connection.execute(
            f"""
            UPDATE profiles
               SET lock_expires = datetime('now', '+' || ? || ' seconds')
             WHERE id IN ({placeholders}) AND locked_by = ?
            """,
            (ttl_seconds, *profile_ids, holder),
        )
        self._connection.commit()
        return cursor.rowcount

    async def release_lease(self, profile_id: str, holder: str) -> bool:
        """Hand the lease back, but only if we still hold it.

        Guarded on the holder id so a slow teardown cannot clear the lease of
        whoever took the profile over after ours expired.
        """
        cursor = self._connection.execute(
            "UPDATE profiles SET locked_by = NULL, lock_expires = NULL "
            "WHERE id = ? AND locked_by = ?",
            (profile_id, holder),
        )
        self._connection.commit()
        return cursor.rowcount > 0

    async def force_release_lease(self, profile_id: str) -> str | None:
        """Clear a lease whoever holds it; returns the holder it was taken from.

        Read then clear, because the UPDATE cannot report the value it just
        erased. Nothing can interleave: SQLite admits one writer at a time.

        Deliberately absent from the HTTP API. A force-unlock button is the
        quickest route back to two machines on one identity, so it lives only
        behind the CLI, where reaching for it means deliberate shell access to
        the host (``camoufox-pm unlock``).
        """
        row = self._connection.execute(
            "SELECT locked_by FROM profiles WHERE id = ? AND locked_by IS NOT NULL",
            (profile_id,),
        ).fetchone()
        if row is None:
            return None
        self._connection.execute(
            "UPDATE profiles SET locked_by = NULL, lock_expires = NULL WHERE id = ?",
            (profile_id,),
        )
        self._connection.commit()
        return row["locked_by"]

    async def get_lease(self, profile_id: str) -> tuple[str | None, str | None] | None:
        """Return ``(locked_by, lock_expires)``, or ``None`` if no such profile.

        A plain read, so it reports an expired lease exactly as stored. Callers
        asking "is this held right now" pass the expiry through
        :func:`~camoufox_pm.core.leases.lease_expired`, or simply try to acquire.
        """
        cursor = self._connection.execute(
            "SELECT locked_by, lock_expires FROM profiles WHERE id = ?", (profile_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return row["locked_by"], row["lock_expires"]

    async def get_lease_holders(self) -> list[dict]:
        """Every lease in the database, expired ones included, for inspection."""
        cursor = self._connection.execute(
            """
            SELECT id, name, locked_by, lock_expires
              FROM profiles
             WHERE locked_by IS NOT NULL
             ORDER BY id
            """
        )
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "locked_by": row["locked_by"],
                "lock_expires": row["lock_expires"],
                "expired": lease_expired(row["lock_expires"]),
            }
            for row in cursor.fetchall()
        ]

    async def acquire_recovery_lock(self, holder: str, ttl_seconds: int) -> bool:
        cursor = self._connection.execute(
            "UPDATE recovery_lock SET holder = ?, expires = datetime('now', '+' || ? || ' seconds') "
            "WHERE id = 1 AND (holder IS NULL OR holder = ? "
            "OR julianday(expires) < julianday('now'))",
            (holder, ttl_seconds, holder),
        )
        self._connection.commit()
        return cursor.rowcount > 0

    async def release_recovery_lock(self, holder: str) -> None:
        self._connection.execute(
            "UPDATE recovery_lock SET holder = NULL, expires = NULL WHERE id = 1 AND holder = ?",
            (holder,),
        )
        self._connection.commit()

    # --- Proxies ---

    async def create_proxy(self, data: dict) -> dict:
        proxy_id = data.get("id") or generate_short_id(8)
        password = encrypt(data["password"]) if data.get("password") else None
        self._connection.execute(
            """
            INSERT INTO proxies (id, name, type, server, port, username, password, status, latency_ms, country, city, ip, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                proxy_id,
                data.get("name") or f"{data.get('type', 'http').upper()}-{data.get('server')}:{data.get('port', 80)}",
                data.get("type", "http").lower(),
                data.get("server"),
                data.get("port"),
                data.get("username"),
                password,
                data.get("status", "uncheck"),
                data.get("latency_ms"),
                data.get("country"),
                data.get("city"),
                data.get("ip"),
                data.get("user_id"),
            ),
        )
        self._connection.commit()
        return await self.get_proxy(proxy_id)

    async def batch_create_proxies(self, proxies_list: list[dict], user_id: str | None = None) -> int:
        count = 0
        for data in proxies_list:
            proxy_id = data.get("id") or generate_short_id(8)
            password = encrypt(data["password"]) if data.get("password") else None
            self._connection.execute(
                """
                INSERT INTO proxies (id, name, type, server, port, username, password, status, latency_ms, country, city, ip, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proxy_id,
                    data.get("name") or f"{data.get('type', 'http').upper()}-{data.get('server')}:{data.get('port', 80)}",
                    data.get("type", "http").lower(),
                    data.get("server"),
                    data.get("port"),
                    data.get("username"),
                    password,
                    data.get("status", "uncheck"),
                    data.get("latency_ms"),
                    data.get("country"),
                    data.get("city"),
                    data.get("ip"),
                    user_id or data.get("user_id"),
                ),
            )
            count += 1
        self._connection.commit()
        return count

    async def get_proxy(self, proxy_id: str) -> dict | None:
        cursor = self._connection.execute("SELECT * FROM proxies WHERE id = ?", (proxy_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_proxy(row)

    async def list_proxies(self, user_id: str | None = None) -> list[dict]:
        if user_id:
            cursor = self._connection.execute(
                "SELECT * FROM proxies WHERE user_id = ? OR user_id IS NULL ORDER BY created_at DESC",
                (user_id,),
            )
        else:
            cursor = self._connection.execute("SELECT * FROM proxies ORDER BY created_at DESC")
        return [self._row_to_proxy(r) for r in cursor.fetchall()]

    async def update_proxy(self, proxy_id: str, updates: dict) -> bool:
        fields = []
        params = []
        for k, v in updates.items():
            if k == "password" and v is not None:
                v = encrypt(v)
            fields.append(f"{k} = ?")
            params.append(v)
        if not fields:
            return False
        params.append(proxy_id)
        sql = f"UPDATE proxies SET {', '.join(fields)} WHERE id = ?"
        cursor = self._connection.execute(sql, params)
        self._connection.commit()
        return cursor.rowcount > 0

    async def delete_proxy(self, proxy_id: str) -> bool:
        cursor = self._connection.execute("DELETE FROM proxies WHERE id = ?", (proxy_id,))
        self._connection.commit()
        return cursor.rowcount > 0

    async def delete_proxies_batch(self, proxy_ids: list[str]) -> int:
        if not proxy_ids:
            return 0
        placeholders = ",".join("?" for _ in proxy_ids)
        cursor = self._connection.execute(f"DELETE FROM proxies WHERE id IN ({placeholders})", proxy_ids)
        self._connection.commit()
        return cursor.rowcount

    def _row_to_proxy(self, row) -> dict:
        keys = row.keys()
        pwd = None
        if "password" in keys and row["password"]:
            try:
                pwd = decrypt(row["password"])
            except Exception:
                pwd = row["password"]
        return {
            "id": row["id"],
            "name": row["name"],
            "type": row["type"],
            "server": row["server"],
            "port": row["port"],
            "username": row["username"],
            "password": pwd,
            "status": row["status"],
            "latency_ms": row["latency_ms"],
            "country": row["country"],
            "city": row["city"],
            "ip": row["ip"],
            "user_id": row["user_id"] if "user_id" in keys else None,
            "created_at": row["created_at"],
            "last_checked_at": row["last_checked_at"] if "last_checked_at" in keys else None,
        }

    # --- Extensions ---

    async def list_extensions(self) -> list[dict]:
        cursor = self._connection.execute("SELECT * FROM extensions ORDER BY is_preset DESC, created_at DESC")
        return [dict(r) for r in cursor.fetchall()]

    async def get_extension(self, ext_id: str) -> dict | None:
        cursor = self._connection.execute("SELECT * FROM extensions WHERE id = ?", (ext_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    async def create_extension(self, data: dict) -> dict:
        ext_id = data.get("id") or generate_short_id(8)
        self._connection.execute(
            """
            INSERT OR REPLACE INTO extensions (id, name, version, icon_url, description, category, crx_id, download_url, local_path, is_preset, enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ext_id,
                data["name"],
                data.get("version", "1.0.0"),
                data.get("icon_url"),
                data.get("description"),
                data.get("category", "general"),
                data.get("crx_id"),
                data.get("download_url"),
                data.get("local_path"),
                data.get("is_preset", 0),
                data.get("enabled", 1),
            ),
        )
        self._connection.commit()
        return await self.get_extension(ext_id)

    async def update_extension(self, ext_id: str, updates: dict) -> bool:
        fields = [f"{k} = ?" for k in updates.keys()]
        if not fields:
            return False
        params = list(updates.values()) + [ext_id]
        cursor = self._connection.execute(f"UPDATE extensions SET {', '.join(fields)} WHERE id = ?", params)
        self._connection.commit()
        return cursor.rowcount > 0

    async def delete_extension(self, ext_id: str) -> bool:
        cursor = self._connection.execute("DELETE FROM extensions WHERE id = ? AND is_preset = 0", (ext_id,))
        self._connection.commit()
        return cursor.rowcount > 0

    # --- Client & Kernel Releases Management ---

    async def list_client_releases(self, active_only: bool = False) -> list[dict]:
        query = "SELECT * FROM client_releases"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY created_at DESC"
        cursor = self._connection.execute(query)
        return [dict(r) for r in cursor.fetchall()]

    async def get_client_release(self, release_id: str) -> dict | None:
        cursor = self._connection.execute("SELECT * FROM client_releases WHERE id = ? OR version = ?", (release_id, release_id))
        row = cursor.fetchone()
        return dict(row) if row else None

    async def get_latest_client_release(self) -> dict | None:
        cursor = self._connection.execute("SELECT * FROM client_releases WHERE is_active = 1 ORDER BY created_at DESC LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None

    async def create_client_release(self, data: dict) -> dict:
        r_id = data.get("id") or f"cr_{generate_short_id(8)}"
        self._connection.execute(
            """
            INSERT OR REPLACE INTO client_releases (
                id, version, title, changelog, changelog_en, min_version,
                is_force_update, is_active, mac_arm64_url, mac_x64_url, win_x64_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                r_id,
                data["version"],
                data.get("title", f"CamouHub {data['version']}"),
                data.get("changelog", ""),
                data.get("changelog_en", ""),
                data.get("min_version", "1.0.0"),
                int(bool(data.get("is_force_update", False))),
                int(bool(data.get("is_active", True))),
                data.get("mac_arm64_url"),
                data.get("mac_x64_url"),
                data.get("win_x64_url"),
            ),
        )
        self._connection.commit()
        return await self.get_client_release(r_id)

    async def update_client_release(self, release_id: str, updates: dict) -> bool:
        updates["updated_at"] = datetime.now().isoformat()
        fields = [f"{k} = ?" for k in updates.keys()]
        if not fields:
            return False
        params = list(updates.values()) + [release_id]
        cursor = self._connection.execute(f"UPDATE client_releases SET {', '.join(fields)} WHERE id = ?", params)
        self._connection.commit()
        return cursor.rowcount > 0

    async def delete_client_release(self, release_id: str) -> bool:
        cursor = self._connection.execute("DELETE FROM client_releases WHERE id = ?", (release_id,))
        self._connection.commit()
        return cursor.rowcount > 0

    async def list_kernel_releases(self, engine: str | None = None, active_only: bool = False) -> list[dict]:
        clauses = []
        params = []
        if engine:
            clauses.append("engine = ?")
            params.append(engine)
        if active_only:
            clauses.append("is_active = 1")
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        query = f"SELECT * FROM kernel_releases{where} ORDER BY is_recommended DESC, created_at DESC"
        cursor = self._connection.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]

    async def get_kernel_release(self, release_id: str) -> dict | None:
        cursor = self._connection.execute("SELECT * FROM kernel_releases WHERE id = ? OR version = ?", (release_id, release_id))
        row = cursor.fetchone()
        return dict(row) if row else None

    async def create_kernel_release(self, data: dict) -> dict:
        k_id = data.get("id") or f"kr_{generate_short_id(8)}"
        self._connection.execute(
            """
            INSERT OR REPLACE INTO kernel_releases (
                id, engine, version, display_name, changelog, is_recommended, is_active,
                mac_arm64_url, mac_arm64_sha256, mac_x64_url, mac_x64_sha256,
                win_x64_url, win_x64_sha256
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                k_id,
                data.get("engine", "chromium"),
                data["version"],
                data.get("display_name", f"{data.get('engine', 'Chromium')} {data['version']}"),
                data.get("changelog", ""),
                int(bool(data.get("is_recommended", False))),
                int(bool(data.get("is_active", True))),
                data.get("mac_arm64_url"),
                data.get("mac_arm64_sha256"),
                data.get("mac_x64_url"),
                data.get("mac_x64_sha256"),
                data.get("win_x64_url"),
                data.get("win_x64_sha256"),
            ),
        )
        self._connection.commit()
        return await self.get_kernel_release(k_id)

    async def update_kernel_release(self, release_id: str, updates: dict) -> bool:
        updates["updated_at"] = datetime.now().isoformat()
        fields = [f"{k} = ?" for k in updates.keys()]
        if not fields:
            return False
        params = list(updates.values()) + [release_id]
        cursor = self._connection.execute(f"UPDATE kernel_releases SET {', '.join(fields)} WHERE id = ?", params)
        self._connection.commit()
        return cursor.rowcount > 0

    async def delete_kernel_release(self, release_id: str) -> bool:
        cursor = self._connection.execute("DELETE FROM kernel_releases WHERE id = ?", (release_id,))
        self._connection.commit()
        return cursor.rowcount > 0

    # --- Profile Snapshots (时光机) ---

    async def record_profile_snapshot(
        self, profile_id: str, snapshot_name: str, size_kb: float, r2_key: str
    ) -> dict:
        import uuid
        snapshot_id = f"snap_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        self._connection.execute(
            """
            INSERT INTO profile_snapshots (id, profile_id, snapshot_name, size_kb, r2_key, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (snapshot_id, profile_id, snapshot_name, size_kb, r2_key, now),
        )

        # Enforce rolling retention: keep the newest 5 snapshots
        cursor = self._connection.execute(
            "SELECT id FROM profile_snapshots WHERE profile_id = ? ORDER BY created_at DESC",
            (profile_id,),
        )
        all_snaps = cursor.fetchall()
        if len(all_snaps) > 5:
            for old in all_snaps[5:]:
                self._connection.execute("DELETE FROM profile_snapshots WHERE id = ?", (old["id"],))

        self._connection.commit()
        return {
            "id": snapshot_id,
            "profile_id": profile_id,
            "snapshot_name": snapshot_name,
            "size_kb": size_kb,
            "r2_key": r2_key,
            "created_at": now,
        }

    async def list_profile_snapshots(self, profile_id: str) -> list[dict]:
        cursor = self._connection.execute(
            "SELECT * FROM profile_snapshots WHERE profile_id = ? ORDER BY created_at DESC",
            (profile_id,),
        )
        return [dict(row) for row in cursor.fetchall()]

    async def get_profile_snapshot(self, snapshot_id: str) -> dict | None:
        cursor = self._connection.execute(
            "SELECT * FROM profile_snapshots WHERE id = ?", (snapshot_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    async def delete_profile_snapshot(self, snapshot_id: str) -> bool:
        cursor = self._connection.execute(
            "DELETE FROM profile_snapshots WHERE id = ?", (snapshot_id,)
        )
        self._connection.commit()
        return cursor.rowcount > 0

    # --- Utilities ---


    def _row_to_schedule(self, row) -> Schedule:
        """Convert a database row into a Schedule object."""
        return Schedule(
            id=row["id"],
            profile_id=row["profile_id"],
            action=row["action"],
            kind=row["kind"],
            interval_minutes=row["interval_minutes"],
            at_time=row["at_time"],
            days=json.loads(row["days"]) if row["days"] else None,
            run_minutes=row["run_minutes"],
            enabled=bool(row["enabled"]),
            next_run_at=(
                datetime.fromisoformat(row["next_run_at"]) if row["next_run_at"] else None
            ),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _row_to_profile(self, row) -> Profile:
        """Convert a database row into a Profile object."""
        from .models import BrowserSettings

        # Parse browser_settings
        browser_settings_data = json.loads(row["browser_settings"])
        browser_settings = BrowserSettings(**browser_settings_data)

        # Parse proxy_config if present (password is decrypted on read).
        proxy = None
        if row["proxy_config"]:
            proxy = _deserialize_proxy(json.loads(row["proxy_config"]))

        # Parse extensions
        extensions = json.loads(row["extensions"]) if row["extensions"] else []

        # Present only once the profile has been launched, and absent entirely on
        # rows written before the column existed.
        keys = row.keys()
        fingerprint = (
            json.loads(row["fingerprint"]) if "fingerprint" in keys and row["fingerprint"] else None
        )
        stored_check = None
        if "proxy_check" in keys and row["proxy_check"]:
            try:
                stored_check = ProxyCheckRecord.model_validate_json(row["proxy_check"])
            except ValidationError as error:
                # A cosmetic column must not be able to take down the list: this
                # runs for every row, so raising here 500s the whole screen over
                # one unreadable value. Losing the dot is the right cost.
                logger.warning(f"Profile {row['id']}: unreadable proxy check, ignoring ({error})")

        user_id = row["user_id"] if "user_id" in keys else None

        return Profile(
            id=row["id"],
            name=row["name"],
            user_id=user_id,
            group=row["group_id"],
            status=ProfileStatus(row["status"]),
            browser_settings=browser_settings,
            proxy=proxy,
            extensions=extensions,
            storage_path=row["storage_path"],
            notes=row["notes"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            last_used=datetime.fromisoformat(row["last_used"]) if row["last_used"] else None,
            fingerprint=fingerprint,
            proxy_check=stored_check,
            row_version=row["row_version"],
            deleted_at=datetime.fromisoformat(row["deleted_at"]) if row["deleted_at"] else None,
            cookies=row["cookies"] if "cookies" in keys else None,
            account=row["account"] if "account" in keys else None,
            is_favorite=bool(row["is_favorite"]) if "is_favorite" in keys and row["is_favorite"] else False,
            tags=json.loads(row["tags"]) if "tags" in keys and row["tags"] else [],
            sync_status=row["sync_status"] if "sync_status" in keys and row["sync_status"] else "synced",
            last_synced_at=datetime.fromisoformat(row["last_synced_at"]) if "last_synced_at" in keys and row["last_synced_at"] else None,
            sync_size_kb=float(row["sync_size_kb"]) if "sync_size_kb" in keys and row["sync_size_kb"] is not None else None,
            cloud_sync_enabled=bool(row["cloud_sync_enabled"]) if "cloud_sync_enabled" in keys and row["cloud_sync_enabled"] is not None else True,
        )

    async def close(self):
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection: sqlite3.Connection = None  # type: ignore[assignment]
        logger.info("Database connection closed")


class StorageManager:
    """StorageManager with dual-engine support: SQLite WAL or PostgreSQL."""

    def __init__(self, db_path: str = "data/profiles.db"):
        import os
        self.db_path = db_path
        self.local_db = DatabaseManager(db_path)
        database_url = os.environ.get("DATABASE_URL") or os.environ.get("CPM_DATABASE_URL")
        target = database_url or db_path
        if target.startswith("postgresql://") or target.startswith("postgres://"):
            from .postgres_database import PostgresDatabaseManager
            self.db = PostgresDatabaseManager(target)
            logger.info("StorageManager initialized with Enterprise PostgreSQL backend")
        else:
            self.db = self.local_db
            logger.info(f"StorageManager initialized with SQLite database: {db_path}")

    async def initialize(self):
        """Initialize the database with graceful SQLite fallback."""
        await self.local_db.initialize()
        if self.db is not self.local_db:
            try:
                await self.db.initialize()
            except Exception as exc:
                logger.warning(
                    f"PostgreSQL initialization failed ({exc}). Falling back to local SQLite WAL engine."
                )
                self.db = self.local_db

    def _get_handler(self, name: str):
        if hasattr(self.db, name):
            return getattr(self.db, name)
        return getattr(self.local_db, name)

    def __getattr__(self, name: str):
        if hasattr(self.db, name):
            return getattr(self.db, name)
        if hasattr(self.local_db, name):
            return getattr(self.local_db, name)
        raise AttributeError(f"'StorageManager' object has no attribute '{name}'")



    # Profile methods
    async def save_profile(self, profile: Profile, expected_row_version: int | None = None):
        await self.db.save_profile(profile, expected_row_version)

    async def get_profile(self, profile_id: str, include_deleted: bool = False) -> Profile | None:
        return await self.db.get_profile(profile_id, include_deleted)

    async def update_profile(self, profile: Profile, expected_row_version: int | None = None):
        await self.db.update_profile(profile, expected_row_version)

    async def set_proxy_check(self, profile_id: str, record: ProxyCheckRecord | None) -> None:
        await self.db.set_proxy_check(profile_id, record)

    async def set_launch_pin(
        self, profile_id: str, fingerprint: dict | None, last_used: datetime
    ) -> None:
        await self.db.set_launch_pin(profile_id, fingerprint, last_used)

    async def set_cloud_sync_status(
        self,
        profile_id: str,
        sync_status: str,
        size_kb: float | None = None,
        last_synced_at: datetime | None = None,
    ) -> None:
        await self.db.set_cloud_sync_status(profile_id, sync_status, size_kb, last_synced_at)

    async def delete_profile(self, profile_id: str) -> bool:
        return await self.db.delete_profile(profile_id)

    async def list_profiles(
        self, filters: dict | None = None, limit: int | None = None, offset: int = 0
    ) -> list[Profile]:
        return await self._get_handler("list_profiles")(filters, limit, offset)

    async def set_profile_trashed(self, profile_id: str, trashed: bool) -> bool:
        return await self._get_handler("set_profile_trashed")(profile_id, trashed)

    async def count_profiles(self, filters: dict | None = None) -> int:
        return await self._get_handler("count_profiles")(filters)

    # Group methods
    async def save_profile_group(self, group: ProfileGroup):
        await self._get_handler("save_profile_group")(group)

    async def list_profile_groups(self) -> list[ProfileGroup]:
        return await self._get_handler("list_profile_groups")()

    # Statistics methods
    async def log_usage(self, usage_stats: UsageStats):
        await self._get_handler("log_usage")(usage_stats)

    async def get_profile_usage_stats(self, profile_id: str) -> list[UsageStats]:
        return await self._get_handler("get_profile_usage_stats")(profile_id)

    async def delete_profile_group(self, group_id: str) -> bool:
        return await self._get_handler("delete_profile_group")(group_id)

    # User and session methods
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
        await self._get_handler("create_user")(
            user_id, username, password_hash, role, plan_id, max_profiles, max_concurrent, expires_at
        )

    async def get_user_by_username(self, username: str) -> dict | None:
        return await self._get_handler("get_user_by_username")(username)

    async def get_user_by_id(self, user_id: str) -> dict | None:
        return await self._get_handler("get_user_by_id")(user_id)

    async def update_user_password(self, username: str, password_hash: str) -> bool:
        return await self._get_handler("update_user_password")(username, password_hash)

    async def update_user_api_credentials(
        self, username: str, api_status: str, app_id: str, app_secret: str
    ) -> bool:
        return await self._get_handler("update_user_api_credentials")(username, api_status, app_id, app_secret)

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
        return await self._get_handler("update_user_admin")(
            username, role, plan_id, max_profiles, max_concurrent, expires_at, status
        )

    async def delete_user(self, username: str) -> bool:
        return await self._get_handler("delete_user")(username)

    async def count_users(self) -> int:
        return await self._get_handler("count_users")()

    async def list_users(self) -> list[dict]:
        return await self._get_handler("list_users")()

    async def create_session(self, token_hash: str, user_id: str, expires_at: datetime) -> None:
        await self._get_handler("create_session")(token_hash, user_id, expires_at)

    async def get_session(self, token_hash: str) -> dict | None:
        return await self._get_handler("get_session")(token_hash)

    async def delete_session(self, token_hash: str) -> bool:
        return await self._get_handler("delete_session")(token_hash)

    async def delete_expired_sessions(self) -> int:
        return await self._get_handler("delete_expired_sessions")()

    # Plan methods
    async def list_plans(self) -> list[dict]:
        return await self._get_handler("list_plans")()

    async def get_plan(self, plan_id: str) -> dict | None:
        return await self._get_handler("get_plan")(plan_id)

    async def save_plan(self, plan: dict) -> None:
        await self._get_handler("save_plan")(plan)

    async def delete_plan(self, plan_id: str) -> bool:
        return await self._get_handler("delete_plan")(plan_id)

    # Order methods
    async def create_order(self, order: dict) -> dict:
        return await self._get_handler("create_order")(order)

    async def get_order(self, order_no: str) -> dict | None:
        return await self._get_handler("get_order")(order_no)

    async def list_orders(self, user_id: str | None = None, limit: int = 100) -> list[dict]:
        return await self._get_handler("list_orders")(user_id, limit)

    async def update_order_status(
        self, order_no: str, status: str, tx_hash: str | None = None
    ) -> bool:
        return await self._get_handler("update_order_status")(order_no, status, tx_hash)

    # Admin Settings & Dashboard
    async def get_admin_settings(self) -> dict[str, str]:
        return await self._get_handler("get_admin_settings")()

    async def update_admin_setting(self, key: str, value: str) -> None:
        await self._get_handler("update_admin_setting")(key, value)

    async def get_admin_dashboard_stats(self) -> dict:
        return await self._get_handler("get_admin_dashboard_stats")()

    # Schedule methods
    async def save_schedule(self, schedule: Schedule):
        await self._get_handler("save_schedule")(schedule)

    async def get_schedule(self, schedule_id: str) -> Schedule | None:
        return await self._get_handler("get_schedule")(schedule_id)

    async def list_schedules(self, profile_id: str | None = None) -> list[Schedule]:
        return await self._get_handler("list_schedules")(profile_id)

    async def delete_schedule(self, schedule_id: str) -> bool:
        return await self._get_handler("delete_schedule")(schedule_id)

    async def log_schedule_run(self, run: ScheduleRun) -> ScheduleRun:
        return await self._get_handler("log_schedule_run")(run)

    async def list_schedule_runs(self, schedule_id: str, limit: int = 20) -> list[ScheduleRun]:
        return await self._get_handler("list_schedule_runs")(schedule_id, limit)

    # Lease methods
    async def acquire_lease(
        self, profile_id: str, holder: str, ttl_seconds: int, include_deleted: bool = False
    ) -> bool:
        from .redis_lease import get_redis_lease_manager
        redis_mgr = get_redis_lease_manager()
        if redis_mgr and redis_mgr.is_available:
            ok = await redis_mgr.acquire_lease(profile_id, holder, ttl_seconds)
            if not ok:
                return False
        return await self.db.acquire_lease(profile_id, holder, ttl_seconds, include_deleted)

    async def renew_lease(self, profile_ids: list[str], holder: str, ttl_seconds: int) -> int:
        from .redis_lease import get_redis_lease_manager
        redis_mgr = get_redis_lease_manager()
        if redis_mgr and redis_mgr.is_available:
            await redis_mgr.renew_lease(profile_ids, holder, ttl_seconds)
        return await self.db.renew_lease(profile_ids, holder, ttl_seconds)

    async def release_lease(self, profile_id: str, holder: str) -> bool:
        from .redis_lease import get_redis_lease_manager
        redis_mgr = get_redis_lease_manager()
        if redis_mgr and redis_mgr.is_available:
            await redis_mgr.release_lease(profile_id, holder)
        return await self.db.release_lease(profile_id, holder)


    async def force_release_lease(self, profile_id: str) -> str | None:
        return await self.db.force_release_lease(profile_id)

    async def get_lease(self, profile_id: str) -> tuple[str | None, str | None] | None:
        return await self.db.get_lease(profile_id)

    async def get_lease_holders(self) -> list[dict]:
        return await self._get_handler("get_lease_holders")()

    async def acquire_recovery_lock(self, holder: str, ttl_seconds: int) -> bool:
        return await self._get_handler("acquire_recovery_lock")(holder, ttl_seconds)

    async def release_recovery_lock(self, holder: str) -> None:
        await self._get_handler("release_recovery_lock")(holder)

    # Proxy pool methods
    async def create_proxy(self, data: dict) -> dict:
        return await self._get_handler("create_proxy")(data)

    async def batch_create_proxies(self, proxies_list: list[dict], user_id: str | None = None) -> int:
        return await self._get_handler("batch_create_proxies")(proxies_list, user_id)

    async def get_proxy(self, proxy_id: str) -> dict | None:
        return await self._get_handler("get_proxy")(proxy_id)

    async def list_proxies(self, user_id: str | None = None) -> list[dict]:
        return await self._get_handler("list_proxies")(user_id)

    async def update_proxy(self, proxy_id: str, updates: dict) -> bool:
        return await self._get_handler("update_proxy")(proxy_id, updates)

    async def delete_proxy(self, proxy_id: str) -> bool:
        return await self._get_handler("delete_proxy")(proxy_id)

    async def delete_proxies_batch(self, proxy_ids: list[str]) -> int:
        return await self._get_handler("delete_proxies_batch")(proxy_ids)

    # Extension methods
    async def list_extensions(self) -> list[dict]:
        return await self._get_handler("list_extensions")()

    async def get_extension(self, ext_id: str) -> dict | None:
        return await self._get_handler("get_extension")(ext_id)

    async def create_extension(self, data: dict) -> dict:
        return await self._get_handler("create_extension")(data)

    async def update_extension(self, ext_id: str, updates: dict) -> bool:
        return await self._get_handler("update_extension")(ext_id, updates)

    async def delete_extension(self, ext_id: str) -> bool:
        return await self._get_handler("delete_extension")(ext_id)

    # Releases methods
    async def list_client_releases(self, active_only: bool = False) -> list[dict]:
        return await self._get_handler("list_client_releases")(active_only)

    async def get_client_release(self, release_id: str) -> dict | None:
        return await self._get_handler("get_client_release")(release_id)

    async def get_latest_client_release(self) -> dict | None:
        return await self._get_handler("get_latest_client_release")()

    async def create_client_release(self, data: dict) -> dict:
        return await self._get_handler("create_client_release")(data)

    async def update_client_release(self, release_id: str, updates: dict) -> bool:
        return await self._get_handler("update_client_release")(release_id, updates)

    async def delete_client_release(self, release_id: str) -> bool:
        return await self._get_handler("delete_client_release")(release_id)

    async def list_kernel_releases(self, engine: str | None = None, active_only: bool = False) -> list[dict]:
        return await self._get_handler("list_kernel_releases")(engine, active_only)

    async def get_kernel_release(self, release_id: str) -> dict | None:
        return await self._get_handler("get_kernel_release")(release_id)

    async def create_kernel_release(self, data: dict) -> dict:
        return await self._get_handler("create_kernel_release")(data)

    async def update_kernel_release(self, release_id: str, updates: dict) -> bool:
        return await self._get_handler("update_kernel_release")(release_id, updates)

    async def delete_kernel_release(self, release_id: str) -> bool:
        return await self._get_handler("delete_kernel_release")(release_id)

    # Snapshot methods (时光机)
    async def record_profile_snapshot(
        self, profile_id: str, snapshot_name: str, size_kb: float, r2_key: str
    ) -> dict:
        return await self._get_handler("record_profile_snapshot")(profile_id, snapshot_name, size_kb, r2_key)

    async def list_profile_snapshots(self, profile_id: str) -> list[dict]:
        return await self._get_handler("list_profile_snapshots")(profile_id)

    async def get_profile_snapshot(self, snapshot_id: str) -> dict | None:
        return await self._get_handler("get_profile_snapshot")(snapshot_id)

    async def delete_profile_snapshot(self, snapshot_id: str) -> bool:
        return await self._get_handler("delete_profile_snapshot")(snapshot_id)

    async def close(self):
        """Close the database."""
        await self.db.close()


