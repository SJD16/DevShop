# DevShop API Contract

## Products

### GET /products

Returns a list of products.

- Request body: none
- Status: 200 OK
- Response: array of product objects

#### Example request

```http
GET /products HTTP/1.1
Host: api.devshop.local
Accept: application/json
```

#### Example response

```json
[
  {
    "id": 1,
    "name": "Mechanical Keyboard",
    "description": "75% mechanical keyboard",
    "price": 129.99,
    "stock_quantity": 25,
    "is_active": true,
    "created_at": "2026-08-20T17:00:00Z",
    "updated_at": "2026-08-20T17:00:00Z"
  },
  {
    "id": 2,
    "name": "Wireless Mouse",
    "description": "Ergonomic wireless mouse",
    "price": 59.5,
    "stock_quantity": 40,
    "is_active": true,
    "created_at": "2026-08-20T17:05:00Z",
    "updated_at": "2026-08-20T17:05:00Z"
  }
]
```

---

### GET /products/{product_id}

Returns a single product.

- Request body: none
- Status on success: 200 OK
- Status if `product_id` is malformed or not in a valid format: 422 Unprocessable Entity
- Status if product does not exist: 404 Not Found

#### Example request

```http
GET /products/1 HTTP/1.1
Host: api.devshop.local
Accept: application/json
```

#### Example success response

```json
{
  "id": 1,
  "name": "Mechanical Keyboard",
  "description": "75% mechanical keyboard",
  "price": 129.99,
  "stock_quantity": 25,
  "is_active": true,
  "created_at": "2026-08-20T17:00:00Z",
  "updated_at": "2026-08-20T17:00:00Z"
}
```

#### Example invalid ID format response

```json
{
  "error": {
    "code": "INVALID_PRODUCT_ID",
    "message": "Product ID is not in a valid format."
  }
}
```

#### Example not found response

```json
{
  "error": {
    "code": "PRODUCT_NOT_FOUND",
    "message": "Product not found."
  }
}
```

---

### POST /products

Creates a product.

#### Request body

```json
{
  "name": "Mechanical Keyboard",
  "description": "75% mechanical keyboard",
  "price": 129.99,
  "stock_quantity": 25
}
```

#### Validation rules

- `name`: required
- `description`: optional
- `price`: required and must be greater than 0
- `stock_quantity`: required and must be 0 or greater

#### Status codes

- 201 Created on success
- 422 Unprocessable Entity if validation fails

#### Example request

```http
POST /products HTTP/1.1
Host: api.devshop.local
Content-Type: application/json
Accept: application/json

{
  "name": "Mechanical Keyboard",
  "description": "75% mechanical keyboard",
  "price": 129.99,
  "stock_quantity": 25
}
```

#### Example success response

```json
{
  "id": 1,
  "name": "Mechanical Keyboard",
  "description": "75% mechanical keyboard",
  "price": 129.99,
  "stock_quantity": 25,
  "is_active": true,
  "created_at": "2026-08-20T17:00:00Z",
  "updated_at": "2026-08-20T17:00:00Z"
}
```

#### Example validation error response

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed.",
    "details": {
      "price": "Price must be greater than 0.",
      "stock_quantity": "Stock quantity must be 0 or greater."
    }
  }
}
```

---

### PATCH /products/{product_id}

Updates an existing product.

- Only fields that need to change should be provided.
- If provided, `name` must not be empty.
- If provided, `price` must be greater than 0.
- If provided, `stock_quantity` must be 0 or greater.
- If provided, `description` may be updated.
- If provided, `is_active` must be a boolean.
- Soft delete behavior: a product may be deactivated without removing the row from the database.
- Status on success: 200 OK
- Status if `product_id` is malformed or not in a valid format: 422 Unprocessable Entity
- Status if product does not exist: 404 Not Found
- Status if validation fails: 422 Unprocessable Entity

#### Example request: update stock and price

```http
PATCH /products/1 HTTP/1.1
Host: api.devshop.local
Content-Type: application/json
Accept: application/json

{
  "price": 139.99,
  "stock_quantity": 18
}
```

#### Example request: soft delete product

```http
PATCH /products/1 HTTP/1.1
Host: api.devshop.local
Content-Type: application/json
Accept: application/json

{
  "is_active": false
}
```

#### Example success response: soft delete product?

```json
{
  "id": 1,
  "name": "Mechanical Keyboard",
  "description": "75% mechanical keyboard",
  "price": 139.99,
  "stock_quantity": 18,
  "is_active": false,
  "created_at": "2026-08-20T17:00:00Z",
  "updated_at": "2026-08-20T17:15:00Z"
}
```

#### Example validation error response

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed.",
    "details": {
      "name": "Name cannot be empty.",
      "price": "Price must be greater than 0.",
      "is_active": "is_active must be a boolean value."
    }
  }
}
```

#### Example invalid ID format response

```json
{
  "error": {
    "code": "INVALID_PRODUCT_ID",
    "message": "Product ID is not in a valid format."
  }
}
```

#### Example not found response

```json
{
  "error": {
    "code": "PRODUCT_NOT_FOUND",
    "message": "Product not found."
  }
}
```

---

## Product object

The product resource has the following fields:

```json
{
  "id": 1,
  "name": "Mechanical Keyboard",
  "description": "75% mechanical keyboard",
  "price": 129.99,
  "stock_quantity": 25,
  "is_active": true,
  "created_at": "2026-08-20T17:00:00Z",
  "updated_at": "2026-08-20T17:00:00Z"
}
```

### Field definitions

- `id`: unique product identifier
- `name`: product name
- `description`: optional product description
- `price`: product price; must be greater than 0
- `stock_quantity`: available stock; must be 0 or greater
- `is_active`: indicates whether the product is active
- `created_at`: UTC timestamp when the product was created
- `updated_at`: UTC timestamp when the product was most recently updated

### Error rules

- Validation failures return `422 Unprocessable Entity`.
- Malformed or invalid `product_id` values return `422 Unprocessable Entity`.
- Missing products return `404 Not Found`.
- All error responses should include a machine-readable `error.code` and a human-readable `error.message` when possible.
- Historical order records must remain intact even when a product is deactivated through the soft-delete pattern.
