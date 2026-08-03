import io
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_dehqon.db")
os.environ.setdefault("AUTH_OTP_MODE", "demo")
os.environ.setdefault("RATE_LIMIT_DEFAULT", "1000/minute")

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app
from app.rate_limit import limiter

TEST_DB_PATH = "./test_dehqon.db"
_engine = create_engine(f"sqlite:///{TEST_DB_PATH}", connect_args={"check_same_thread": False})
_TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture(autouse=True)
def _fresh_db():
    Base.metadata.create_all(bind=_engine)
    limiter.reset()
    yield
    Base.metadata.drop_all(bind=_engine)


def _override_get_db():
    db = _TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def make_test_jpeg_bytes(width=400, height=400, color=(90, 160, 70)) -> bytes:
    img = Image.new("RGB", (width, height), color)
    # Checkerboard blocks give enough edge variance after the classifier's internal
    # 64x64 downsample that it is never mistaken for a flat/blurry photo.
    pixels = img.load()
    block = max(4, width // 20)
    dark = (max(0, color[0] - 60), max(0, color[1] - 80), max(0, color[2] - 20))
    for by in range(0, height, block):
        for bx in range(0, width, block):
            if ((bx // block) + (by // block)) % 2 == 0:
                for x in range(bx, min(bx + block, width)):
                    for y in range(by, min(by + block, height)):
                        pixels[x, y] = dark
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


@pytest.fixture
def authed_headers(client):
    phone = "+998901234567"
    req = client.post("/v1/auth/otp/request", json={"phone_number": phone}).json()
    verify = client.post(
        "/v1/auth/otp/verify",
        json={"request_id": req["request_id"], "code": "123456"},
    ).json()
    token = verify["access_token"]
    return {"Authorization": f"Bearer {token}"}
