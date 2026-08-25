DevShop Reference Application
=============================

Purpose
-------

A REST API for managing products and customer orders.

Entities
--------

Product
- id
- name
- description
- price
- created_at
- updated_at

Order
- id
- status
- created_at
- updated_at

OrderItem
- id
- order_id
- product_id
- quantity
- unit_price

Relationships
-------------

Order 1 ──── * OrderItem * ──── 1 Product

API
---

Products:
POST   /products
GET    /products
GET    /products/{product_id}
PUT    /products/{product_id}
DELETE /products/{product_id}

Orders:
POST   /orders
GET    /orders
GET    /orders/{order_id}
PATCH  /orders/{order_id}/status
POST   /orders/{order_id}/cancel
