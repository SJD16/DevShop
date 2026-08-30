import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.security import hash_password
from app.models.user import User
from app.core.security import create_access_token
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app


TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://devshop:devshop_dev_password@localhost:5432/devshop_test",
)

test_engine = create_engine(TEST_DATABASE_URL)

TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autocommit=False,
    autoflush=False,
)


def override_get_db():
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def clean_database():
    db = TestingSessionLocal()

    try:
        db.execute(
            text(
                """
                TRUNCATE TABLE
                    order_items,
                    orders,
                    cart_items,
                    carts,
                    products,
                    users
                RESTART IDENTITY CASCADE
                """
            )
        )

        db.commit()

        yield

    finally:
        db.close()


@pytest.fixture
def test_customer():
    db = TestingSessionLocal()

    try:
        user = User(
            email="test_customer@example.com",
            password_hash=hash_password("test-password"),
            role="customer",
            is_active=True,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user

    finally:
        db.close()


@pytest.fixture
def customer_token(test_customer):
    return create_access_token(
        user_id=test_customer.id,
        role=test_customer.role,
    )




@pytest.fixture
def customer_client(customer_token):
    client = TestClient(app)

    client.headers.update({
        "Authorization": f"Bearer {customer_token}"
    })

    return client


@pytest.fixture
def admin_client(admin_token):
    client = TestClient(app)

    client.headers.update({
        "Authorization": f"Bearer {admin_token}"
    })

    return client

@pytest.fixture
def admin_token(test_admin):
    return create_access_token(
        user_id=test_admin.id,
        role=test_admin.role,
    )

@pytest.fixture
def test_admin():
    db = TestingSessionLocal()

    try:
        user = User(
            email="test_admin@example.com",
            password_hash=hash_password("test-password"),
            role="administrator",
            is_active=True,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user

    finally:
        db.close()

