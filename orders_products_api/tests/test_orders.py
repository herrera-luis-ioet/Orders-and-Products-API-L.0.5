import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from datetime import datetime
import time

from app.main import app
from app.models import Product, Order, OrderStatus
from app.database import get_db, Base

# Create in-memory SQLite database for testing with proper isolation
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def _enable_foreign_keys(dbapi_connection, connection_record):
    """Enable foreign key constraints for SQLite"""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# Enable foreign key constraints for SQLite
event.listen(engine, 'connect', _enable_foreign_keys)

@pytest.fixture(scope="function")
def db_session():
    """Fixture that creates a new database session for a test with proper isolation"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db_session):
    """Fixture that creates a test client with a test database session"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture
def test_product(db_session):
    """Fixture that creates a sample product for testing"""
    product = Product(
        name="Test Product",
        description="Test Description",
        price=10.0,
        stock_quantity=10
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product

@pytest.fixture
def test_order(db_session, test_product):
    """Fixture that creates a sample order for testing"""
    order = Order(
        product_id=test_product.id,
        quantity=2,
        total_price=20.0,
        status=OrderStatus.PENDING
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    return order

@pytest.fixture
def multiple_products(db_session):
    """Fixture that creates multiple products for testing pagination"""
    products = []
    for i in range(5):
        product = Product(
            name=f"Product {i}",
            description=f"Description {i}",
            price=10.0 * (i + 1),
            stock_quantity=20
        )
        db_session.add(product)
        products.append(product)
    db_session.commit()
    for product in products:
        db_session.refresh(product)
    return products

@pytest.fixture
def multiple_orders(db_session, multiple_products):
    """Fixture that creates multiple orders for testing pagination"""
    orders = []
    for i, product in enumerate(multiple_products):
        order = Order(
            product_id=product.id,
            quantity=1,
            total_price=product.price,
            status=OrderStatus.PENDING
        )
        db_session.add(order)
        orders.append(order)
    db_session.commit()
    for order in orders:
        db_session.refresh(order)
    return orders

def test_create_order_success(client, test_product, db_session):
    """Test case TC_ORDER_001: Create a new order with valid product and quantity"""
    initial_stock = test_product.stock_quantity
    response = client.post(
        "/orders/",
        json={"product_id": test_product.id, "quantity": 5}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["quantity"] == 5
    assert data["total_price"] == test_product.price * 5
    assert data["status"] == OrderStatus.PENDING
    
    # Verify stock update
    db_session.refresh(test_product)
    assert test_product.stock_quantity == initial_stock - 5

def test_create_order_insufficient_stock(client, test_product):
    """Test case TC_ORDER_002: Attempt to create order with insufficient stock"""
    response = client.post(
        "/orders/",
        json={"product_id": test_product.id, "quantity": 15}
    )
    assert response.status_code == 400
    assert "Not enough stock" in response.json()["detail"]
    
    # Verify stock remains unchanged
    response = client.get(f"/products/{test_product.id}")
    assert response.json()["stock_quantity"] == test_product.stock_quantity

def test_create_order_nonexistent_product(client):
    """Test case TC_ORDER_003: Attempt to create order with non-existent product"""
    response = client.post(
        "/orders/",
        json={"product_id": 999, "quantity": 1}
    )
    assert response.status_code == 404
    assert "Product with id 999 not found" in response.json()["detail"]

def test_get_orders_pagination(client, multiple_orders):
    """Test case TC_ORDER_004: Get list of orders with pagination"""
    # Test default pagination
    response = client.get("/orders/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == len(multiple_orders)
    
    # Test custom pagination
    response = client.get("/orders/?skip=1&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["id"] == multiple_orders[1].id

def test_get_order_by_id(client, test_order):
    """Test case TC_ORDER_005: Get specific order by ID"""
    response = client.get(f"/orders/{test_order.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_order.id
    assert data["quantity"] == test_order.quantity
    assert data["product"]["id"] == test_order.product_id
    assert isinstance(data["created_at"], str)

def test_update_order_quantity(client, test_order, test_product, db_session):
    """Test case TC_ORDER_006: Update order quantity with sufficient stock"""
    initial_stock = test_product.stock_quantity
    response = client.put(
        f"/orders/{test_order.id}",
        json={"quantity": 4}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["quantity"] == 4
    assert data["total_price"] == test_product.price * 4
    
    # Verify stock update
    db_session.refresh(test_product)
    assert test_product.stock_quantity == initial_stock - 2  # Difference from original quantity

def test_update_order_status_transitions(client, test_order):
    """Test case TC_ORDER_007: Update order status through valid transitions"""
    # Test transition to COMPLETED
    response = client.put(
        f"/orders/{test_order.id}",
        json={"status": OrderStatus.COMPLETED}
    )
    assert response.status_code == 200
    assert response.json()["status"] == OrderStatus.COMPLETED
    
    # Test transition to CANCELLED
    response = client.put(
        f"/orders/{test_order.id}",
        json={"status": OrderStatus.CANCELLED}
    )
    assert response.status_code == 200
    assert response.json()["status"] == OrderStatus.CANCELLED

def test_delete_order_restore_stock(client, test_order, test_product, db_session):
    """Test case TC_ORDER_008: Delete order and verify stock restoration"""
    initial_stock = test_product.stock_quantity
    response = client.delete(f"/orders/{test_order.id}")
    assert response.status_code == 204
    
    # Verify stock restoration
    db_session.refresh(test_product)
    assert test_product.stock_quantity == initial_stock + test_order.quantity
    
    # Verify order is deleted
    response = client.get(f"/orders/{test_order.id}")
    assert response.status_code == 404

def test_delete_cancelled_order_stock_handling(client, test_order, test_product, db_session):
    """Test case TC_ORDER_009: Delete cancelled order and verify stock handling"""
    # Update order to cancelled status
    test_order.status = OrderStatus.CANCELLED
    db_session.commit()
    
    initial_stock = test_product.stock_quantity
    response = client.delete(f"/orders/{test_order.id}")
    assert response.status_code == 204
    
    # Verify stock remains unchanged for cancelled orders
    db_session.refresh(test_product)
    assert test_product.stock_quantity == initial_stock

def test_concurrent_order_creation(client, test_product, db_session):
    """Test case TC_ORDER_010: Test concurrent order creation with stock management"""
    # Create multiple orders in sequence but verify stock management
    initial_stock = test_product.stock_quantity
    responses = []
    
    # Try to create 3 orders for the same product
    for _ in range(3):
        response = client.post(
            "/orders/",
            json={"product_id": test_product.id, "quantity": 2}
        )
        responses.append(response)
        # Small delay to simulate concurrent access
        time.sleep(0.1)
    
    # Verify responses and stock consistency
    success_count = sum(1 for r in responses if r.status_code == 201)
    failed_count = sum(1 for r in responses if r.status_code == 400)
    
    # Should only allow orders up to available stock
    assert success_count <= initial_stock // 2
    assert success_count + failed_count == 3
    
    # Verify final stock is consistent
    db_session.refresh(test_product)
    expected_stock = initial_stock - (success_count * 2)
    assert test_product.stock_quantity == expected_stock
    
    # Verify that stock was properly managed
    assert test_product.stock_quantity >= 0

def test_update_order_invalid_quantity(client, test_order):
    """Additional test: Update order with invalid quantity"""
    response = client.put(
        f"/orders/{test_order.id}",
        json={"quantity": -1}
    )
    assert response.status_code == 422
    assert "greater than 0" in response.json()["detail"][0]["msg"]

def test_get_nonexistent_order(client):
    """Additional test: Get non-existent order"""
    response = client.get("/orders/999")
    assert response.status_code == 404
    assert "Order with id 999 not found" in response.json()["detail"]

def test_update_nonexistent_order(client):
    """Additional test: Update non-existent order"""
    response = client.put(
        "/orders/999",
        json={"status": OrderStatus.COMPLETED}
    )
    assert response.status_code == 404
    assert "Order with id 999 not found" in response.json()["detail"]
