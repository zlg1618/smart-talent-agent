"""SQLite 轻量 schema 迁移：对比 ORM 元数据，补齐缺失的列。

SQLite 不会随模型变更自动加列，开发环境里重建库又不方便，
因此在建表后、写数据前跑一次补列即可。
"""

from sqlalchemy import text


def add_missing_columns(engine) -> list[str]:
    """返回本次新增的列清单（形如 "table.column"）。"""
    from app.config.database import Base

    if not engine.dialect.name == "sqlite":
        return []

    added: list[str] = []
    with engine.connect() as conn:
        for table in Base.metadata.sorted_tables:
            existing = {
                row[1]
                for row in conn.execute(
                    text(f'PRAGMA table_info("{table.name}")')
                ).all()
            }
            if not existing:
                continue  # 表还没建，交给 create_all 处理
            for col in table.columns:
                if col.name in existing:
                    continue
                coltype = col.type.compile(engine.dialect)
                conn.execute(
                    text(f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {coltype}')
                )
                added.append(f"{table.name}.{col.name}")
            if added:
                conn.commit()
    return added
