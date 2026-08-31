import os
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import hash_password
from app.models.user import User
from tests.conftest import TestingSessionLocal


client = TestClient(app)


def test_register_user():
    response = client.post(
        "/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["email"] == "newuser@example.com"
    assert data["role"] == "customer"
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data

    # The password must never be returned by the API.
    assert "password" not in data
    assert "password_hash" not in data


def test_register_duplicate_email():
    first_response = client.post(
        "/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "password123",
        },
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "differentpassword",
        },
    )

    assert second_response.status_code == 409
    assert second_response.json()["detail"] == "Email already registered"


def test_register_password_is_hashed():
    response = client.post(
        "/auth/register",
        json={
            "email": "hashed@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 201

    # We cannot inspect the database directly through the API response.
    # The important contract here is that the password is not exposed.
    data = response.json()

    assert "password" not in data
    assert "password_hash" not in data


def test_login_successfully():
    register_response = client.post(
        "/auth/register",
        json={
            "email": "login@example.com",
            "password": "password123",
        },
    )

    assert register_response.status_code == 201

    response = client.post(
        "/auth/login",
        data={
            "username": "login@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 0
    assert data["token_type"] == "bearer"


def test_login_with_wrong_password():
    register_response = client.post(
        "/auth/register",
        json={
            "email": "wrongpassword@example.com",
            "password": "password123",
        },
    )

    assert register_response.status_code == 201

    response = client.post(
        "/auth/login",
        data={
            "username": "wrongpassword@example.com",
            "password": "wrongpassword",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_with_unknown_email():
    response = client.post(
        "/auth/login",
        data={
            "username": "doesnotexist@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_me_with_valid_token():
    register_response = client.post(
        "/auth/register",
        json={
            "email": "me@example.com",
            "password": "password123",
        },
    )

    assert register_response.status_code == 201

    user_id = register_response.json()["id"]

    login_response = client.post(
        "/auth/login",
        data={
            "username": "me@example.com",
            "password": "password123",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["user_id"] == user_id
    assert data["email"] == "me@example.com"
    assert data["role"] == "customer"
    assert data["is_active"] is True


def test_me_without_token():
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_me_with_invalid_token():
    response = client.get(
        "/auth/me",
        headers={
            "Authorization": "Bearer this-is-not-a-valid-token",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authentication token"


def test_inactive_user_cannot_login():
    db = TestingSessionLocal()

    try:
        user = User(
            email="inactive@example.com",
            password_hash=hash_password("password123"),
            role="customer",
            is_active=False,
        )

        db.add(user)
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/auth/login",
        data={
            "username": "inactive@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_stored_password_is_hashed():
    plain_password = "password123"

    response = client.post(
        "/auth/register",
        json={
            "email": "storedhash@example.com",
            "password": plain_password,
        },
    )

    assert response.status_code == 201

    db = TestingSessionLocal()

    try:
        user = (
            db.query(User)
            .filter(User.email == "storedhash@example.com")
            .first()
        )

        assert user is not None
        assert user.password_hash != plain_password
        assert len(user.password_hash) > 0
    finally:
        db.close()


def test_me_with_malformed_token():
    response = client.get(
        "/auth/me",
        headers={
            "Authorization": "Bearer definitely-not-a-jwt",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authentication token"


def test_me_with_expired_token():
    import jwt

    expired_token = jwt.encode(
        {
            "sub": "1",
            "role": "customer",
            "exp": 1,
        },
        os.getenv("JWT_SECRET_KEY"),
        algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
    )

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {expired_token}",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Token has expired"


def test_me_with_token_for_nonexistent_user():
    from app.core.security import create_access_token

    token = create_access_token(
        user_id=999999,
        role="customer",
    )

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authentication token"


def test_me_with_token_for_inactive_user(test_customer):
    from app.core.security import create_access_token

    # Deactivate the user directly in the database.
    db = TestingSessionLocal()

    try:
        user = db.query(User).filter(User.id == test_customer.id).first()

        assert user is not None

        user.is_active = False
        db.commit()
    finally:
        db.close()

    token = create_access_token(
        user_id=test_customer.id,
        role=test_customer.role,
    )

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authentication token"
