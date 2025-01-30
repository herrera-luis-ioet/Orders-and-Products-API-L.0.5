from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from .models import OrderStatus

class ProductBase(BaseModel):
    """
    Base schema for Product with common attributes.
    
    This model defines the core attributes that all product-related schemas share.
    All fields are required unless explicitly marked as optional.
    """
    name: str = Field(..., description="Name of the product", min_length=1)
    description: str = Field(..., description="Description of the product")
    price: float = Field(..., description="Price of the product", gt=0)
    stock_quantity: int = Field(..., description="Available quantity in stock", ge=0)

class ProductCreate(ProductBase):
    """
    Schema for creating a new product.
    
    Inherits all fields from ProductBase. All fields are required for product creation.
    
    Example:
        {
            "name": "Sample Product",
            "description": "A detailed product description",
            "price": 29.99,
            "stock_quantity": 100
        }
    """
    pass

class ProductUpdate(BaseModel):
    """
    Schema for updating a product with optional fields.
    
    All fields are optional, allowing partial updates to products.
    Only the fields that need to be updated should be included in the request.
    
    Example:
        {
            "price": 24.99,
            "stock_quantity": 150
        }
    """
    name: Optional[str] = Field(None, description="Name of the product", min_length=1)
    description: Optional[str] = Field(None, description="Description of the product")
    price: Optional[float] = Field(None, description="Price of the product", gt=0)
    stock_quantity: Optional[int] = Field(None, description="Available quantity in stock", ge=0)

class Product(ProductBase):
    """
    Schema for product response including database id.
    
    This schema is used for API responses and includes all product fields
    plus the database ID. It inherits all fields from ProductBase.
    
    Example:
        {
            "id": 1,
            "name": "Sample Product",
            "description": "A detailed product description",
            "price": 29.99,
            "stock_quantity": 100
        }
    """
    id: int

    class Config:
        """Configure Pydantic to handle ORM objects"""
        from_attributes = True

class OrderBase(BaseModel):
    """
    Base schema for Order with common attributes.
    
    This model defines the core attributes that all order-related schemas share.
    The product_id and quantity fields are required for all order operations.
    """
    product_id: int = Field(..., description="ID of the product being ordered")
    quantity: int = Field(..., description="Quantity of products to order", gt=0)

class OrderCreate(OrderBase):
    """
    Schema for creating a new order.
    
    Inherits product_id and quantity fields from OrderBase.
    The total price is calculated automatically based on the product price.
    
    Example:
        {
            "product_id": 1,
            "quantity": 5
        }
    """
    pass

class OrderUpdate(BaseModel):
    """
    Schema for updating an order.
    
    Allows updating the quantity and status of an existing order.
    The total price is automatically recalculated if the quantity changes.
    
    Example:
        {
            "quantity": 3,
            "status": "COMPLETED"
        }
    """
    quantity: Optional[int] = Field(None, description="Quantity of products to order", gt=0)
    status: Optional[OrderStatus] = Field(None, description="Status of the order")

class Order(OrderBase):
    """
    Schema for order response including all fields.
    
    This schema is used for API responses and includes all order fields
    plus additional information like total price, status, and creation date.
    It also includes the associated product details.
    
    Example:
        {
            "id": 1,
            "product_id": 1,
            "quantity": 5,
            "total_price": 149.95,
            "status": "PENDING",
            "created_at": "2024-03-15T10:30:00",
            "product": {
                "id": 1,
                "name": "Sample Product",
                "description": "A detailed product description",
                "price": 29.99,
                "stock_quantity": 95
            }
        }
    """
    id: int
    total_price: float
    status: OrderStatus
    created_at: datetime
    product: Product

    class Config:
        """Configure Pydantic to handle ORM objects"""
        from_attributes = True
