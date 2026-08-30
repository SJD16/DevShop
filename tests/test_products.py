from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_get_products_empty():
    response = client.get("/products")

    assert response.status_code == 200
    assert response.json() == []


def test_create_product():
    response = client.post(
        "/products",
        json={
            "name": "Test Keyboard",
            "description": "Keyboard created by automated test",
            "price": 99.99,
            "stock_quantity": 10,
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "Test Keyboard"
    assert data["description"] == "Keyboard created by automated test"
    assert data["price"] == "99.99"
    assert data["stock_quantity"] == 10
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
