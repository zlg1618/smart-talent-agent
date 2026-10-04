"""pytest 公共夹具。

测试使用独立的 SQLite 临时库，不污染开发库。
必须在导入任何 app 模块之前设置 DATABASE_URL，
因为 app.config.database 在导入时就会根据配置创建 engine。
"""

import os
import tempfile
from pathlib import Path

_DB_PATH = Path(tempfile.gettempdir()) / "smart_talent_agent_test.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_DB_PATH.as_posix()}")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config.database import SessionLocal, init_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def prepared_db():
    """建表并写入一套种子数据，供整个测试会话复用。"""
    init_db()

    from seed_data import clear_all, seed

    db = SessionLocal()
    try:
        # 先清空再写入，保证重复运行测试也幂等
        clear_all(db)
        seed(db)
    finally:
        db.close()
    return True


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c
