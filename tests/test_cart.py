from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_get_cart_without_cart(customer_client):
    response = customer_client.get("/cart")

    assert response.status_code == 404
    assert response.json()["detail"] == "Cart not found"

def test_add_product_to_cart(customer_client, test_product):
    response = customer_client.post(
        "/cart/items",
        json={
            "product_id": test_product.id,
            "quantity": 2,
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["product_id"] == test_product.id
    assert data["quantity"] == 2
    assert "id" in data

def test_add_same_product_increases_quantity(customer_client, test_product):
    first_response = customer_client.post(
        "/cart/items",
        json={
            "product_id": test_product.id,
            "quantity": 2,
        },
    )

    assert first_response.status_code == 201

    second_response = customer_client.post(
        "/cart/items",
        json={
            "product_id": test_product.id,
            "quantity": 3,
        },
    )

    assert second_response.status_code == 201

    data = second_response.json()

    assert data["product_id"] == test_product.id
    assert data["quantity"] == 5

def test_get_cart_with_items(customer_client, test_product):
    add_response = customer_client.post(
        "/cart/items",
        json={
            "product_id": test_product.id,
            "quantity": 4,
        },
    )

    assert add_response.status_code == 201

    response = customer_client.get("/cart")

    assert response.status_code == 200

    data = response.json()

    assert data["user_id"] is not None
    assert data["id"] is not None
    assert len(data["items"]) == 1

    item = data["items"][0]

    assert item["product_id"] == test_product.id
    assert item["quantity"] == 4


def test_add_nonexistent_product(customer_client):
    response = customer_client.post(
        "/cart/items",
        json={
            "product_id": 999999,
            "quantity": 1,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found" 


def test_cannot_add_inactive_product(customer_client, inactive_product):
    response = customer_client.post(
        "/cart/items",
        json={
            "product_id": inactive_product.id,
            "quantity": 1,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Product is not active"

def test_add_product_with_zero_quantity(customer_client, test_product):
    response = customer_client.post(
        "/cart/items",
        json={
            "product_id": test_product.id,
            "quantity": 0,
        },
    )

    assert response.status_code == 422

def test_add_product_with_negative_quantity(customer_client, test_product):
    response = customer_client.post(
        "/cart/items",
        json={
            "product_id": test_product.id,
            "quantity": -5,
        },
    )

    assert response.status_code == 422

def test_update_cart_item_quantity(customer_client, test_product):
    add_response = customer_client.post(
        "/cart/items",
        json={
            "product_id": test_product.id,
            "quantity": 2,
        },
    )

    assert add_response.status_code == 201

    item = add_response.json()

    response = customer_client.patch(
        f"/cart/items/{item['id']}",
        json={
            "quantity": 7,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == item["id"]
    assert data["product_id"] == test_product.id
    assert data["quantity"] == 7


def test_customer_cannot_access_another_customers_cart(
    customer_client,
    customer_2_client,
    test_product,
):
    # Customer 1 creates a cart.
    add_response = customer_client.post(
        "/cart/items",
        json={
            "product_id": test_product.id,
            "quantity": 2,
        },
    )

    assert add_response.status_code == 201

    # Customer 2 attempts to access Customer 1's cart.
    response = customer_2_client.get("/cart")

    assert response.status_code == 404
    assert response.json()["detail"] == "Cart not found"

def test_customer_cannot_update_another_customers_cart_item(
    customer_client,
    customer_2_client,
    test_product,
):
    add_response = customer_client.post(
        "/cart/items",
        json={
            "product_id": test_product.id,
            "quantity": 2,
        },
    )

    assert add_response.status_code == 201

    item_id = add_response.json()["id"]

    response = customer_2_client.patch(
        f"/cart/items/{item_id}",
        json={
            "quantity": 99,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Cart not found"


def test_customer_cannot_delete_another_customers_cart_item(
    customer_client,
    customer_2_client,
    test_product,
):
    add_response = customer_client.post(
        "/cart/items",
        json={
            "product_id": test_product.id,
            "quantity": 2,
        },
    )

    assert add_response.status_code == 201

    item_id = add_response.json()["id"]

    response = customer_2_client.delete(
        f"/cart/items/{item_id}"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Cart not found"


def test_update_cart_item_with_zero_quantity(
    customer_client,
    test_product,
):
    add_response = customer_client.post(
        "/cart/items",
        json={
            "product_id": test_product.id,
            "quantity": 2,
        },
    )

    assert add_response.status_code == 201

    item_id = add_response.json()["id"]

    response = customer_client.patch(
        f"/cart/items/{item_id}",
        json={
            "quantity": 0,
        },
    )

    assert response.status_code == 422


def test_update_cart_item_with_negative_quantity(
    customer_client,
    test_product,
):
    add_response = customer_client.post(
        "/cart/items",
        json={
            "product_id": test_product.id,
            "quantity": 2,
        },
    )

    assert add_response.status_code == 201

    item_id = add_response.json()["id"]

    response = customer_client.patch(
        f"/cart/items/{item_id}",
        json={
            "quantity": -3,
        },
    )

    assert response.status_code == 422


def test_update_nonexistent_cart_item(
    customer_client,
    test_product,
):
    # Create the customer's cart.
    add_response = customer_client.post(
        "/cart/items",
        json={
            "product_id": test_product.id,
            "quantity": 1,
        },
    )

    assert add_response.status_code == 201

    response = customer_client.patch(
        "/cart/items/999999",
        json={
            "quantity": 2,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Cart item not found"


def test_delete_cart_item(
    customer_client,
    test_product,
):
    add_response = customer_client.post(
        "/cart/items",
        json={
            "product_id": test_product.id,
            "quantity": 2,
        },
    )

    assert add_response.status_code == 201

    item_id = add_response.json()["id"]

    response = customer_client.delete(
        f"/cart/items/{item_id}"
    )

    assert response.status_code == 204

    # Verify the cart still exists but contains no items.
    cart_response = customer_client.get("/cart")

    assert cart_response.status_code == 200
    assert cart_response.json()["items"] == []

