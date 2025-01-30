from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas
from ..database import get_db

router = APIRouter(
    prefix="/orders",
    tags=["orders"]
)

# PUBLIC_INTERFACE
@router.post("/", response_model=schemas.Order, status_code=status.HTTP_201_CREATED)
def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    """
    Create a new order.
    
    Args:
        order: Order data
        db: Database session
    
    Returns:
        Created order
    
    Raises:
        HTTPException: If order creation fails or product not found
    """
    # Check if product exists and has enough stock
    product = db.query(models.Product).filter(models.Product.id == order.product_id).first()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {order.product_id} not found"
        )
    
    if product.stock_quantity < order.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not enough stock. Available: {product.stock_quantity}"
        )
    
    # Calculate total price and create order
    total_price = product.price * order.quantity
    db_order = models.Order(
        product_id=order.product_id,
        quantity=order.quantity,
        total_price=total_price
    )
    
    # Update product stock
    product.stock_quantity -= order.quantity
    
    db.add(db_order)
    try:
        db.commit()
        db.refresh(db_order)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create order"
        ) from e
    
    return db_order

# PUBLIC_INTERFACE
@router.get("/", response_model=List[schemas.Order])
def get_orders(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Get list of orders with pagination.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
    
    Returns:
        List of orders
    """
    orders = db.query(models.Order).offset(skip).limit(limit).all()
    return orders

# PUBLIC_INTERFACE
@router.get("/{order_id}", response_model=schemas.Order)
def get_order(order_id: int, db: Session = Depends(get_db)):
    """
    Get a specific order by ID.
    
    Args:
        order_id: ID of the order
        db: Database session
    
    Returns:
        Order details
    
    Raises:
        HTTPException: If order is not found
    """
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with id {order_id} not found"
        )
    return order

# PUBLIC_INTERFACE
@router.put("/{order_id}", response_model=schemas.Order)
def update_order(
    order_id: int,
    order_update: schemas.OrderUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an order.
    
    Args:
        order_id: ID of the order to update
        order_update: Updated order data
        db: Database session
    
    Returns:
        Updated order
    
    Raises:
        HTTPException: If order is not found or update fails
    """
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if db_order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with id {order_id} not found"
        )
    
    # Handle quantity update
    if order_update.quantity is not None:
        product = db.query(models.Product).filter(models.Product.id == db_order.product_id).first()
        stock_diff = order_update.quantity - db_order.quantity
        
        if stock_diff > 0 and product.stock_quantity < stock_diff:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Not enough stock. Available: {product.stock_quantity}"
            )
        
        product.stock_quantity -= stock_diff
        db_order.quantity = order_update.quantity
        db_order.total_price = product.price * order_update.quantity
    
    # Handle status update
    if order_update.status is not None:
        db_order.status = order_update.status
    
    try:
        db.commit()
        db.refresh(db_order)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not update order"
        ) from e
    return db_order

# PUBLIC_INTERFACE
@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    """
    Delete an order.
    
    Args:
        order_id: ID of the order to delete
        db: Database session
    
    Raises:
        HTTPException: If order is not found or delete fails
    """
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if db_order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with id {order_id} not found"
        )
    
    # Restore product stock quantity
    if db_order.status != models.OrderStatus.CANCELLED:
        product = db.query(models.Product).filter(models.Product.id == db_order.product_id).first()
        if product:
            product.stock_quantity += db_order.quantity
    
    try:
        db.delete(db_order)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not delete order"
        ) from e