import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models import Product, Order

# Create in-memory SQLite database for testing
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

@pytest.fixture
def db_session():
    """Fixture that creates a new database session for a test"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
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
def sample_product(db_session):
    """Fixture that creates a sample product in the database"""
    product = Product(
        name="Test Product",
        description="A test product",
        price=99.99,
        stock_quantity=10
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product

@pytest.fixture
def sample_product_with_orders(db_session):
    """Fixture that creates a sample product with associated orders"""
    product = Product(
        name="Test Product with Orders",
        description="A test product that has orders",
        price=49.99,
        stock_quantity=5
    )
    db_session.add(product)
    db_session.commit()
    
    order = Order(
        product_id=product.id,
        quantity=2,
        total_price=99.98,
        status="pending"
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(product)
    return product

def test_create_product_valid_data(client):
    """Test case TC_PROD_001: Create a new product with valid data"""
    product_data = {
        "name": "New Product",
        "description": "A brand new product",
        "price": 29.99,
        "stock_quantity": 100
    }
    response = client.post("/products/", json=product_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == product_data["name"]
    assert data["price"] == product_data["price"]
    assert "id" in data

def test_create_product_invalid_price(client):
    """Test case TC_PROD_002: Create a product with invalid price"""
    product_data = {
        "name": "Invalid Product",
        "description": "A product with invalid price",
        "price": -10.00,  # Invalid negative price
        "stock_quantity": 50
    }
    response = client.post("/products/", json=product_data)
    assert response.status_code == 422  # Validation error

def test_get_products_default_pagination(client, sample_product):
    """Test case TC_PROD_003: Get list of products with default pagination"""
    response = client.get("/products/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["name"] == sample_product.name

def test_get_products_custom_pagination(client, sample_product):
    """Test case TC_PROD_004: Get list of products with custom pagination"""
    response = client.get("/products/?skip=0&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 5

def test_get_product_by_valid_id(client, sample_product):
    """Test case TC_PROD_005: Get specific product by valid ID"""
    response = client.get(f"/products/{sample_product.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_product.id
    assert data["name"] == sample_product.name

def test_get_product_nonexistent_id(client):
    """Test case TC_PROD_006: Get product with non-existent ID"""
    response = client.get("/products/999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_update_product_valid_partial_data(client, sample_product):
    """Test case TC_PROD_007: Update product with valid partial data"""
    update_data = {
        "name": "Updated Product Name",
        "price": 149.99
    }
    response = client.put(f"/products/{sample_product.id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == update_data["name"]
    assert data["price"] == update_data["price"]
    assert data["description"] == sample_product.description  # Unchanged field

def test_update_product_invalid_data(client, sample_product):
    """Test case TC_PROD_008: Update product with invalid data"""
    update_data = {
        "price": -50.00  # Invalid negative price
    }
    response = client.put(f"/products/{sample_product.id}", json=update_data)
    assert response.status_code == 422  # Validation error

def test_delete_existing_product(client, sample_product):
    """Test case TC_PROD_009: Delete existing product"""
    response = client.delete(f"/products/{sample_product.id}")
    assert response.status_code == 204
    
    # Verify product is deleted
    get_response = client.get(f"/products/{sample_product.id}")
    assert get_response.status_code == 404

def test_delete_product_with_orders(client, sample_product_with_orders):
    """Test case TC_PROD_010: Delete product with associated orders"""
    response = client.delete(f"/products/{sample_product_with_orders.id}")
    assert response.status_code == 400  # Should fail due to foreign key constraint
