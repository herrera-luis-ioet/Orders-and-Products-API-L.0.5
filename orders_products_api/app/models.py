from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from .database import Base

class OrderStatus(str, enum.Enum):
    """Enum for order status"""
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class Product(Base):
    """
    Product model representing items in the inventory.
    
    Attributes:
        id (int): Primary key
        name (str): Name of the product
        description (str): Description of the product
        price (float): Price of the product
        stock_quantity (int): Available quantity in stock
        orders (relationship): Relationship to Order model
    """
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    price = Column(Float)
    stock_quantity = Column(Integer)

    # Relationship with Order model
    orders = relationship("Order", back_populates="product")

class Order(Base):
    """
    Order model representing customer orders.
    
    Attributes:
        id (int): Primary key
        product_id (int): Foreign key to Product
        quantity (int): Quantity ordered
        total_price (float): Total price of the order
        status (OrderStatus): Status of the order
        created_at (datetime): Timestamp of order creation
        product (relationship): Relationship to Product model
    """
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"))
    quantity = Column(Integer)
    total_price = Column(Float)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship with Product model
    product = relationship("Product", back_populates="orders")
