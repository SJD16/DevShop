from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_get_cart_without_cart(customer_client):
    response = customer_client.get("/cart")

    assert response.status_code == 404
    assert response.json()["detail"] == "Cart not found"
