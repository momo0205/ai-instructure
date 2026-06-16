"""
skill-generator 数据库模块
"""
import os
from sqlmodel import SQLModel, Session, create_engine
from config import settings

# 确保数据目录存在
db_path = settings.DATABASE_URL.replace("sqlite:///", "")
db_dir = os.path.dirname(db_path)
if db_dir:
    os.makedirs(db_dir, exist_ok=True)

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args={"check_same_thread": False},  # SQLite 多线程支持
)


def init_db():
    """初始化数据库，创建所有表"""
    SQLModel.metadata.create_all(engine)


def get_session():
    """获取数据库 Session（用于 FastAPI Depends）"""
    with Session(engine) as session:
        yield session
