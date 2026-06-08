"""SQLite 持久化层：回合记录初始化与 CRUD。"""

import aiosqlite

# 建表 DDL
_CREATE_TABLE_SQL: str = """
CREATE TABLE IF NOT EXISTS rounds (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    topic       TEXT NOT NULL,
    guess       TEXT NOT NULL,
    is_correct  INTEGER NOT NULL,
    model_name  TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

# 索引 DDL
_CREATE_INDEX_SQL: str = """
CREATE INDEX IF NOT EXISTS idx_rounds_created_at ON rounds(created_at);
"""

# INSERT SQL
_INSERT_ROUND_SQL: str = """
INSERT INTO rounds (topic, guess, is_correct, model_name)
VALUES (?, ?, ?, ?);
"""

# SELECT SQL
_LIST_ROUNDS_SQL: str = """
SELECT id, topic, guess, is_correct, model_name, created_at
FROM rounds
ORDER BY created_at DESC
LIMIT ?;
"""


async def init_db(db_path: str) -> None:
    """初始化数据库：建表 + 创建索引（幂等）。"""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(_CREATE_TABLE_SQL)
        await db.execute(_CREATE_INDEX_SQL)
        await db.commit()


async def insert_round(
    db_path: str,
    topic: str,
    guess: str,
    is_correct: bool,
    model_name: str,
) -> None:
    """插入一条回合记录。"""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            _INSERT_ROUND_SQL,
            (topic, guess, int(is_correct), model_name),
        )
        await db.commit()


async def list_rounds(
    db_path: str,
    limit: int = 20,
) -> list[dict[str, object]]:
    """按时间倒序查询回合记录。"""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(_LIST_ROUNDS_SQL, (limit,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
