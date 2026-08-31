from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_get_orders_empty(customer_client):
    response = customer_client.get("/orders")

    assert response.status_code == 200
    assert response.json() == []


def test_get_nonexistent_order(customer_client):
    response = customer_client.get("/orders/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found"


def test_create_order_without_cart(customer_client):
    response = customer_client.post("/orders")

    assert response.status_code == 404
    assert response.json()["detail"] == "Cart not found"


def test_create_order_with_empty_cart(customer_client, test_product):
    # Create the cart by adding the product first.
    add_response = customer_client.post(
        "/cart/items",
        json={
            "product_id": test_product.id,
            "quantity": 1,
        },
    )

    assert add_response.status_code == 201

    # Remove the item so the cart exists but is empty.
    item_id = add_response.json()["id"]

    delete_response = customer_client.delete(
        f"/cart/items/{item_id}"
    )

    assert delete_response.status_code == 204

    response = customer_client.post("/orders")

    assert response.status_code == 400
    assert response.json()["detail"] == "Cart is empty"


def test_create_order_successfully(customer_client, test_product):
    # Add two units of the product to the customer's cart.
    add_response = customer_client.post(
        "/cart/items",
        json={
            "product_id": test_product.id,
            "quantity": 2,
        },
    )

    assert add_response.status_code == 201

    # Create the order.
    response = customer_client.post("/orders")

    assert response.status_code == 201

    data = response.json()

    # Verify the basic order data.
    assert data["id"] is not None
    assert data["user_id"] is not None
    assert data["status"] == "pending"

    # Product price is $50 and quantity is 2.
    assert data["total_amount"] == "100.00"

    # Verify the order contains one item.
    assert len(data["items"]) == 1

    item = data["items"][0]

    assert item["product_id"] == test_product.id
    assert item["quantity"] == 2
    assert item["unit_price"] == "50.00"


def test_create_order_decreases_product_stock(customer_client, test_product):
    # Add two units to the cart.
    add_response = customer_client.post(
        "/cart/items",
        json={
            "product_id": test_product.id,
            "quantity": 2,
        },
    )

    assert add_response.status_code == 201

    # Create the order.
    response = customer_client.post("/orders")

    assert response.status_code == 201

    # Fetch the product through the API.
    product_response = client.get(
        f"/products/{test_product.id}"
    )

    assert product_response.status_code == 200

    product_data = product_response.json()

    # Original stock was 20.
    # Two units were ordered.
    assert product_data["stock_quantity"] == 18


def test_create_order_clears_cart(customer_client, test_product):
    # Add two units to the cart.
    add_response = customer_client.post(
        "/cart/items",
        json={
            "product_id": test_product.id,
            "quantity": 2,
        },
    )

    assert add_response.status_code == 201

    # Confirm the cart contains the item before checkout.
    cart_response = customer_client.get("/cart")

    assert cart_response.status_code == 200
    assert len(cart_response.json()["items"]) == 1

    # Create the order.
    order_response = customer_client.post("/orders")

    assert order_response.status_code == 201

    # The cart should now exist but contain no items.
    cart_response = customer_client.get("/cart")

    assert cart_response.status_code == 200
    assert cart_response.json()["items"] == []

def test_create_order_fails_with_insufficient_stock(
    customer_client,
    test_product,
):
    # test_product starts with 20 units in stock.
    add_response = customer_client.post(
        "/cart/items",
        json={
            "product_id": test_product.id,
            "quantity": 21,
        },
    )

    assert add_response.status_code == 201

    # Attempt to create an order requiring more stock than is available.
    response = customer_client.post("/orders")

    assert response.status_code == 400
    assert response.json()["detail"] == (
        f"Insufficient stock for product {test_product.id}"
    )

    # The product stock must remain unchanged.
    product_response = client.get(
        f"/products/{test_product.id}"
    )

    assert product_response.status_code == 200

    product_data = product_response.json()

    assert product_data["stock_quantity"] == 20

    # The failed order must not have been created.
    orders_response = customer_client.get("/orders")

    assert orders_response.status_code == 200
    assert orders_response.json() == []

    # The cart must still contain the item because checkout failed.
    cart_response = customer_client.get("/cart")

    assert cart_response.status_code == 200

    cart_data = cart_response.json()

    assert len(cart_data["items"]) == 1
    assert cart_data["items"][0]["product_id"] == test_product.id
    assert cart_data["items"][0]["quantity"] == 21


def test_create_order_fails_if_product_becomes_inactive(
    customer_client,
    test_product,
    admin_client,
):
    # Add the active product to the customer's cart.
    add_response = customer_client.post(
        "/cart/items",
        json={
            "product_id": test_product.id,
            "quantity": 1,
        },
    )

    assert add_response.status_code == 201

    # Deactivate the product after it has entered the cart.
    update_response = admin_client.patch(
        f"/products/{test_product.id}",
        json={
            "is_active": False,
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()["is_active"] is False

    # Checkout should now fail because the product is inactive.
    response = customer_client.post("/orders")

    assert response.status_code == 400
    assert response.json()["detail"] == (
        f"Product {test_product.id} is not active"
    )

    # No order should have been created.
    orders_response = customer_client.get("/orders")

    assert orders_response.status_code == 200
    assert orders_response.json() == []

    # The cart should remain intact.
    cart_response = customer_client.get("/cart")

    assert cart_response.status_code == 200

    cart_data = cart_response.json()

    assert len(cart_data["items"]) == 1
    assert cart_data["items"][0]["product_id"] == test_product.id
    assert cart_data["items"][0]["quantity"] == 1


def test_customer_can_get_own_order(customer_client, test_product):
    # Add a product to the customer's cart.
    add_response = customer_client.post(
        "/cart/items",
        json={
            "product_id": test_product.id,
            "quantity": 2,
        },
    )

    assert add_response.status_code == 201

    # Create the order.
    create_response = customer_client.post("/orders")

    assert create_response.status_code == 201

    order_id = create_response.json()["id"]

    # Retrieve the customer's own order.
    response = customer_client.get(
        f"/orders/{order_id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == order_id
    assert data["status"] == "pending"
    assert data["total_amount"] == "100.00"
    assert len(data["items"]) == 1
    assert data["items"][0]["product_id"] == test_product.id
    assert data["items"][0]["quantity"] == 2


def test_customer_cannot_get_another_customers_order(
    customer_client,
    customer_2_client,
    test_product,
):
    # Customer 1 creates an order.
    add_response = customer_client.post(
        "/cart/items",
        json={
            "product_id": test_product.id,
            "quantity": 1,
        },
    )

    assert add_response.status_code == 201

    create_response = customer_client.post("/orders")

    assert create_response.status_code == 201

    order_id = create_response.json()["id"]

    # Customer 2 attempts to access Customer 1's order.
    response = customer_2_client.get(
        f"/orders/{order_id}"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found"


def test_get_orders_returns_only_current_customers_orders(
    customer_client,
    customer_2_client,
    test_product,
):
    # Customer 1 creates an order.
    add_response = customer_client.post(
        "/cart/items",
        json={
            "product_id": test_product.id,
            "quantity": 1,
        },
    )

    assert add_response.status_code == 201

    create_response = customer_client.post("/orders")

    assert create_response.status_code == 201

    customer_1_order_id = create_response.json()["id"]

    # Customer 1 should see their order.
    response = customer_client.get("/orders")

    assert response.status_code == 200

    orders = response.json()

    assert len(orders) == 1
    assert orders[0]["id"] == customer_1_order_id

    # Customer 2 should see no orders.
    response = customer_2_client.get("/orders")

    assert response.status_code == 200
    assert response.json() == []


def test_customer_cannot_confirm_order(
    customer_client,
    admin_client,
    test_product,
):
    # Create an order as the customer.
    add_response = customer_client.post(
        "/cart/items",
        json={
            "product_id": test_product.id,
            "quantity": 1,
        },
    )

    assert add_response.status_code == 201

    order_response = customer_client.post("/orders")

    assert order_response.status_code == 201

    order_id = order_response.json()["id"]

    # Customer attempts to confirm their own order.
    response = customer_client.patch(
        f"/orders/{order_id}/status",
        json={
            "status": "confirmed",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Only administrators can confirm orders"
    )


def test_admin_can_confirm_order(
    customer_client,
    admin_client,
    test_product,
):
    # Create an order as the customer.
    add_response = customer_client.post(
        "/cart/items",
        json={
            "product_id": test_product.id,
            "quantity": 1,
        },
    )

    assert add_response.status_code == 201

    order_response = customer_client.post("/orders")

    assert order_response.status_code == 201

    order_id = order_response.json()["id"]

    # Administrator confirms the order.
    response = admin_client.patch(
        f"/orders/{order_id}/status",
        json={
            "status": "confirmed",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == order_id
    assert data["status"] == "confirmed"


def test_customer_can_cancel_own_order(
    customer_client,
    test_product,
):
    # Add product to cart.
    add_response = customer_client.post(
        "/cart/items",
        json={
            "product_id": test_product.id,
            "quantity": 2,
        },
    )

    assert add_response.status_code == 201

    # Create order.
    order_response = customer_client.post("/orders")

    assert order_response.status_code == 201

    order_id = order_response.json()["id"]

    # Inventory should now be reduced from 20 to 18.
    product_response = client.get(
        f"/products/{test_product.id}"
    )

    assert product_response.status_code == 200
    assert product_response.json()["stock_quantity"] == 18

    # Customer cancels their own order.
    response = customer_client.patch(
        f"/orders/{order_id}/status",
        json={
            "status": "cancelled",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == order_id
    assert data["status"] == "cancelled"


def test_cancelling_order_restores_inventory(
    customer_client,
    test_product,
):
    # Add three units to the cart.
    add_response = customer_client.post(
        "/cart/items",
        json={
            "product_id": test_product.id,
            "quantity": 3,
        },
    )

    assert add_response.status_code == 201

    # Create the order.
    order_response = customer_client.post("/orders")

    assert order_response.status_code == 201

    order_id = order_response.json()["id"]

    # Stock should decrease from 20 to 17.
    product_response = client.get(
        f"/products/{test_product.id}"
    )

    assert product_response.status_code == 200
    assert product_response.json()["stock_quantity"] == 17

    # Cancel the order.
    cancel_response = customer_client.patch(
        f"/orders/{order_id}/status",
        json={
            "status": "cancelled",
        },
    )

    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"

    # Stock should be restored from 17 back to 20.
    product_response = client.get(
        f"/products/{test_product.id}"
    )

    assert product_response.status_code == 200
    assert product_response.json()["stock_quantity"] == 20

def test_customer_cannot_cancel_another_customers_order(
    customer_client,
    customer_2_client,
    test_product,
):
    # Customer 1 creates an order.
    add_response = customer_client.post(
        "/cart/items",
        json={
            "product_id": test_product.id,
            "quantity": 1,
        },
    )

    assert add_response.status_code == 201

    order_response = customer_client.post("/orders")

    assert order_response.status_code == 201

    order_id = order_response.json()["id"]

    # Customer 2 attempts to cancel Customer 1's order.
    response = customer_2_client.patch(
        f"/orders/{order_id}/status",
        json={
            "status": "cancelled",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "You can only cancel your own orders"
    )

    # Confirm the order is still pending.
    own_order_response = customer_client.get(
        f"/orders/{order_id}"
    )

    assert own_order_response.status_code == 200
    assert own_order_response.json()["status"] == "pending"

def test_confirmed_order_cannot_be_cancelled(
    customer_client,
    admin_client,
    test_product,
):
    # Customer creates an order.
    add_response = customer_client.post(
        "/cart/items",
        json={
            "product_id": test_product.id,
            "quantity": 1,
        },
    )

    assert add_response.status_code == 201

    order_response = customer_client.post("/orders")

    assert order_response.status_code == 201

    order_id = order_response.json()["id"]

    # Administrator confirms the order.
    confirm_response = admin_client.patch(
        f"/orders/{order_id}/status",
        json={
            "status": "confirmed",
        },
    )

    assert confirm_response.status_code == 200
    assert confirm_response.json()["status"] == "confirmed"

    # Customer attempts to cancel the already-confirmed order.
    response = customer_client.patch(
        f"/orders/{order_id}/status",
        json={
            "status": "cancelled",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Only pending orders can change status"
    )

def test_cancelled_order_cannot_be_confirmed(
    customer_client,
    admin_client,
    test_product,
):
    # Customer creates an order.
    add_response = customer_client.post(
        "/cart/items",
        json={
            "product_id": test_product.id,
            "quantity": 1,
        },
    )

    assert add_response.status_code == 201

    order_response = customer_client.post("/orders")

    assert order_response.status_code == 201

    order_id = order_response.json()["id"]

    # Customer cancels the order.
    cancel_response = customer_client.patch(
        f"/orders/{order_id}/status",
        json={
            "status": "cancelled",
        },
    )

    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"

    # Administrator attempts to confirm the cancelled order.
    response = admin_client.patch(
        f"/orders/{order_id}/status",
        json={
            "status": "confirmed",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Only pending orders can change status"
    )


def test_unauthenticated_user_cannot_get_orders():
    response = client.get("/orders")

    assert response.status_code == 401


def test_unauthenticated_user_cannot_create_order():
    response = client.post("/orders")

    assert response.status_code == 401


def test_get_order_invalid_id(customer_client):
    response = customer_client.get("/orders/abc")

    assert response.status_code == 422


def test_invalid_order_status(
    customer_client,
    test_product,
):
    # Create an order first.
    add_response = customer_client.post(
        "/cart/items",
        json={
            "product_id": test_product.id,
            "quantity": 1,
        },
    )

    assert add_response.status_code == 201

    order_response = customer_client.post("/orders")

    assert order_response.status_code == 201

    order_id = order_response.json()["id"]

    # Attempt to use a status that is not part of OrderStatus.
    response = customer_client.patch(
        f"/orders/{order_id}/status",
        json={
            "status": "banana",
        },
    )

    assert response.status_code == 422

def test_admin_cannot_cancel_another_customers_order(
    customer_client,
    admin_client,
    test_product,
):
    # Customer creates an order.
    add_response = customer_client.post(
        "/cart/items",
        json={
            "product_id": test_product.id,
            "quantity": 2,
        },
    )

    assert add_response.status_code == 201

    order_response = customer_client.post("/orders")

    assert order_response.status_code == 201

    order_id = order_response.json()["id"]

    # Administrator attempts to cancel the customer's order.
    response = admin_client.patch(
        f"/orders/{order_id}/status",
        json={
            "status": "cancelled",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "You can only cancel your own orders"
    )

    # Confirm the order remains pending.
    own_order_response = customer_client.get(
        f"/orders/{order_id}"
    )

    assert own_order_response.status_code == 200
    assert own_order_response.json()["status"] == "pending"

    # Confirm inventory was not restored because cancellation failed.
    product_response = client.get(
        f"/products/{test_product.id}"
    )

    assert product_response.status_code == 200
    assert product_response.json()["stock_quantity"] == 18
