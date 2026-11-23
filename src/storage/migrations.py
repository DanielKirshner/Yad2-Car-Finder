"""Database schema, as a list of migrations.

Each migration is a list of statements. Never change one that was released, add a new one instead.
The database stores how many it applied in `PRAGMA user_version`.
"""

MIGRATIONS: list[list[str]] = [
    [
        """
        CREATE TABLE chats (
            chat_id INTEGER PRIMARY KEY,
            username TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL REFERENCES chats (chat_id),
            car_filter TEXT NOT NULL,
            model_names TEXT NOT NULL,
            interval_minutes INTEGER NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        "CREATE INDEX active_scans_by_chat ON scans (chat_id) WHERE is_active = 1",
        """
        CREATE TABLE listings (
            url TEXT PRIMARY KEY,
            manufacturer TEXT,
            model TEXT,
            sub_model TEXT,
            year INTEGER,
            hand INTEGER,
            price INTEGER,
            first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE scan_notifications (
            scan_id INTEGER NOT NULL REFERENCES scans (id),
            url TEXT NOT NULL REFERENCES listings (url),
            notified_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (scan_id, url)
        ) WITHOUT ROWID
        """,
    ],
]
