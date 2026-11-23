# 0001 - Storage

## Status

Accepted, 2026-11-23. Answers [#12](https://github.com/DanielKirshner/Yad2-Car-Finder/issues/12), which proposed MongoDB.

## Context

Scans and seen listings were kept in memory and lost on every restart. The bot is one process, writes a few hundred small rows per scan, and is the only reader. A web dashboard ([#34](https://github.com/DanielKirshner/Yad2-Car-Finder/issues/34)) may read the same data on the same machine later.

## Decision

SQLite, through `aiosqlite`, with plain SQL in repositories and a list of migrations.

- No second service to run, secure, back up and wait for. The database is one file in a Docker volume
- The data is relational: chats have scans, and scans sent listings. Foreign keys and transactions keep it consistent
- WAL mode lets another process read while the bot writes
- A few tables need no ORM and no migration framework

## Consequences

- One machine only. Two bot processes must not share the file over a network
- Writes are serialized, which is far from a limit here
- The issue's collections became tables: `chats`, `scans`, `listings` and `scan_notifications`

## Revisit if

Several machines have to share the data, or the bot becomes a service for many users.
