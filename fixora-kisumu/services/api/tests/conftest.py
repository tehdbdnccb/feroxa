import os
os.environ["DATABASE_URL"]="sqlite:///./test_fixora.db"
os.environ["JWT_SECRET"]="test-secret-key-that-is-at-least-32-bytes-long"
from fastapi.testclient import TestClient
import pytest
from app.db import Base,engine
from app.main import app
@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine)
    with TestClient(app) as c: yield c
    Base.metadata.drop_all(bind=engine)
