"""Product API integration tests.

These checks exercise the product endpoints through the real FastAPI app and confirm
that the API enforces authentication, authorization, validation, and CRUD behavior.
The suite is intentionally written to verify the public contract exposed to clients,
including response codes and serialized payloads.
"""

from fastapi.testclient import TestClient

from app.main import app


# Shared client used across tests to exercise the application through HTTP requests.
client = TestClient(app)


def test_create_test_product():
    """Verify that unauthenticated callers are blocked from creating products.

    This test is intended to confirm the API's expected authentication boundary for
    write operations. It documents the current contract that a create request without
    admin credentials is rejected before any product is persisted.
    """
    response = client.post(
        "/products",
        json={
            "name": "Isolation Test Product",
            "description": "Testing database isolation",
            "price": 10.00,
            "stock_quantity": 5,
        },
    )

    # The endpoint requires admin privileges, so an anonymous request is denied.
    assert response.status_code == 401


def test_products_is_empty_after_previous_test():
    """Assert the product listing is empty when the database has been reset.

    This acts as a regression guard for test isolation. If prior tests leave data in
    the database, the list would contain records and this assertion would fail.
    """
    response = client.get("/products")

    assert response.status_code == 200
    assert response.json() == []


def test_customer_fixture(test_customer):
    """Verify the seeded customer fixture matches the expected user contract."""
    assert test_customer.id is not None
    assert test_customer.email == "test_customer@example.com"
    assert test_customer.role == "customer"
    assert test_customer.is_active is True


"""
def test_customer_token_fixture(test_customer, customer_token):
    assert test_customer.id is not None
    assert isinstance(customer_token, str)
    assert len(customer_token) > 0
"""


def test_customer_cannot_create_product(customer_client):
    """Customers are forbidden from creating products.

    The API distinguishes between authentication and authorization: a customer is
    logged in, but not allowed to perform admin-only product creation.
    """
    response = customer_client.post(
        "/products",
        json={
            "name": "Customer Product",
            "description": "Customer should not be able to create products",
            "price": 99.99,
            "stock_quantity": 10,
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Administrator privileges required"


def test_admin_can_create_product(admin_client):
    """An administrator can create a product and receives the persisted payload."""
    response = admin_client.post(
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


def test_get_products(admin_client):
    """List products after creating one through the admin client.

    This checks the list endpoint returns the created record and that the returned
    serialized representation matches the API contract for price formatting.
    """
    response = admin_client.post(
        "/products",
        json={
            "name": "GET Test Product",
            "description": "Product for GET test",
            "price": 49.99,
            "stock_quantity": 20,
        },
    )

    assert response.status_code == 201

    response = client.get("/products")

    assert response.status_code == 200

    products = response.json()

    assert len(products) == 1
    assert products[0]["name"] == "GET Test Product"
    assert products[0]["price"] == "49.99"
    assert products[0]["stock_quantity"] == 20


def test_get_product_by_id(admin_client):
    """Fetch a single product by its database id and validate the payload."""
    create_response = admin_client.post(
        "/products",
        json={
            "name": "Single Product Test",
            "description": "Product for GET by ID test",
            "price": 79.99,
            "stock_quantity": 15,
        },
    )

    assert create_response.status_code == 201

    product_id = create_response.json()["id"]

    response = client.get(f"/products/{product_id}")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == product_id
    assert data["name"] == "Single Product Test"
    assert data["description"] == "Product for GET by ID test"
    assert data["price"] == "79.99"
    assert data["stock_quantity"] == 15


def test_get_nonexistent_product():
    """A missing product id should produce the standard not-found API error."""
    response = client.get("/products/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


def test_get_product_invalid_id():
    """Invalid path values should be rejected by request validation before lookup."""
    response = client.get("/products/abc")

    assert response.status_code == 422



def test_unauthenticated_user_cannot_update_product(admin_client):
    """Patch requests are rejected for users who are not authenticated."""
    create_response = admin_client.post(
        "/products",
        json={
            "name": "Protected Product",
            "description": "Unauthenticated user must not modify this",
            "price": 100.00,
            "stock_quantity": 10,
        },
    )

    assert create_response.status_code == 201

    product_id = create_response.json()["id"]

    response = client.patch(
        f"/products/{product_id}",
        json={
            "price": 50.00,
        },
    )

    assert response.status_code == 401


def test_update_nonexistent_product(admin_client):
    """Attempting to patch a missing product should return a not-found error."""
    response = admin_client.patch(
        "/products/999999",
        json={
            "price": 50.00,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


# This name is repeated later in the file; in Python the final definition wins for the
# module-level symbol, which is a subtle testing pitfall worth noting when reading this suite.
def test_admin_can_update_product(admin_client):
    """The update path should accept valid patch data and return the new state."""
    create_response = admin_client.post(
        "/products",
        json={
            "name": "Update Test Product",
            "description": "Original description",
            "price": 50.00,
            "stock_quantity": 10,
        },
    )

    assert create_response.status_code == 201

    product_id = create_response.json()["id"]

    response = admin_client.patch(
        f"/products/{product_id}",
        json={
            "price": 75.00,
            "stock_quantity": 20,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == product_id
    assert data["price"] == "75.00"
    assert data["stock_quantity"] == 20
    assert data["name"] == "Update Test Product"


# The same name is reused here intentionally in the same module; the later definition is
# the one pytest will effectively expose under that symbol name in Python.
def test_customer_cannot_update_product(admin_client, customer_client):
    """Customers should still be blocked even when a product exists and is writable by admins."""
    create_response = admin_client.post(
        "/products",
        json={
            "name": "Customer Update Target",
            "description": "Product owned by nobody",
            "price": 50.00,
            "stock_quantity": 10,
        },
    )

    assert create_response.status_code == 201

    product_id = create_response.json()["id"]

    response = customer_client.patch(
        f"/products/{product_id}",
        json={
            "price": 75.00,
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Administrator privileges required"


def test_admin_cannot_create_product_with_invalid_price(admin_client):
    """Negative prices are rejected as invalid input values for product creation."""
    response = admin_client.post(
        "/products",
        json={
            "name": "Invalid Price Product",
            "description": "Price should be greater than zero",
            "price": -10.00,
            "stock_quantity": 10,
        },
    )

    assert response.status_code == 422


def test_admin_cannot_create_product_with_negative_stock(admin_client):
    """Stock levels below zero are rejected to enforce inventory invariants."""
    response = admin_client.post(
        "/products",
        json={
            "name": "Negative Stock Product",
            "description": "Stock cannot be negative",
            "price": 25.00,
            "stock_quantity": -5,
        },
    )

    assert response.status_code == 422


def test_admin_can_create_product_with_zero_stock(admin_client):
    """Zero inventory is treated as valid and indicates an out-of-stock product."""
    response = admin_client.post(
        "/products",
        json={
            "name": "Out Of Stock Product",
            "description": "Valid product with zero inventory",
            "price": 25.00,
            "stock_quantity": 0,
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "Out Of Stock Product"
    assert data["price"] == "25.00"
    assert data["stock_quantity"] == 0
    assert data["is_active"] is True


def test_admin_cannot_update_product_with_invalid_price(admin_client):
    """PATCH validation should reject negative prices even after a product exists."""
    create_response = admin_client.post(
        "/products",
        json={
            "name": "Patch Price Test",
            "description": "Testing invalid PATCH price",
            "price": 50.00,
            "stock_quantity": 10,
        },
    )

    assert create_response.status_code == 201

    product_id = create_response.json()["id"]

    response = admin_client.patch(
        f"/products/{product_id}",
        json={
            "price": -20.00,
        },
    )

    assert response.status_code == 422


def test_admin_cannot_update_product_with_negative_stock(admin_client):
    """PATCH validation should also reject negative stock updates."""
    create_response = admin_client.post(
        "/products",
        json={
            "name": "Patch Stock Test",
            "description": "Testing invalid PATCH stock",
            "price": 50.00,
            "stock_quantity": 10,
        },
    )

    assert create_response.status_code == 201

    product_id = create_response.json()["id"]

    response = admin_client.patch(
        f"/products/{product_id}",
        json={
            "stock_quantity": -5,
        },
    )

    assert response.status_code == 422


def test_admin_partial_update_preserves_existing_fields(admin_client):
    """PATCH should merge new data into the existing product rather than replace it."""
    create_response = admin_client.post(
        "/products",
        json={
            "name": "Partial Update Test",
            "description": "Original description",
            "price": 100.00,
            "stock_quantity": 25,
        },
    )

    assert create_response.status_code == 201

    product_id = create_response.json()["id"]

    response = admin_client.patch(
        f"/products/{product_id}",
        json={
            "price": 125.00,
        },
    )

    assert response.status_code == 200

    data = response.json()

    # The requested field changed, while the rest of the record remains intact.
    assert data["price"] == "125.00"

    # This confirms the API applies partial updates instead of replacing the whole object.
    assert data["name"] == "Partial Update Test"
    assert data["description"] == "Original description"
    assert data["stock_quantity"] == 25
    assert data["is_active"] is True


def test_admin_can_deactivate_product(admin_client):
    """Admins can deactivate a product by toggling the active flag to false."""
    create_response = admin_client.post(
        "/products",
        json={
            "name": "Deactivation Test Product",
            "description": "Testing product deactivation",
            "price": 75.00,
            "stock_quantity": 10,
        },
    )

    assert create_response.status_code == 201

    product_id = create_response.json()["id"]

    response = admin_client.patch(
        f"/products/{product_id}",
        json={
            "is_active": False,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == product_id
    assert data["is_active"] is False


def test_inactive_product_is_not_returned_in_product_list(
    admin_client,
):
    create_response = admin_client.post(
        "/products",
        json={
            "name": "Inactive List Product",
            "description": "Should not appear in public product listing",
            "price": 25.00,
            "stock_quantity": 10,
        },
    )

    assert create_response.status_code == 201

    product_id = create_response.json()["id"]

    update_response = admin_client.patch(
        f"/products/{product_id}",
        json={
            "is_active": False,
        },
    )

    assert update_response.status_code == 200

    response = client.get("/products")

    assert response.status_code == 200

    products = response.json()

    assert all(product["id"] != product_id for product in products)


def test_inactive_product_is_not_returned_by_id(
    admin_client,
):
    create_response = admin_client.post(
        "/products",
        json={
            "name": "Inactive Detail Product",
            "description": "Should not be publicly accessible",
            "price": 30.00,
            "stock_quantity": 10,
        },
    )

    assert create_response.status_code == 201

    product_id = create_response.json()["id"]

    update_response = admin_client.patch(
        f"/products/{product_id}",
        json={
            "is_active": False,
        },
    )

    assert update_response.status_code == 200

    response = client.get(f"/products/{product_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"
