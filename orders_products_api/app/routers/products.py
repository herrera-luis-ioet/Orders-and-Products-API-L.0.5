from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas
from ..database import get_db

router = APIRouter(
    prefix="/products",
    tags=["products"]
)

# PUBLIC_INTERFACE
@router.post("/", response_model=schemas.Product, status_code=status.HTTP_201_CREATED)
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db)):
    """
    Create a new product.
    
    Args:
        product: Product data
        db: Database session
    
    Returns:
        Created product
    
    Raises:
        HTTPException: If product creation fails
    """
    db_product = models.Product(**product.model_dump())
    db.add(db_product)
    try:
        db.commit()
        db.refresh(db_product)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create product"
        ) from e
    return db_product

# PUBLIC_INTERFACE
@router.get("/", response_model=List[schemas.Product])
def get_products(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Get list of products with pagination.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
    
    Returns:
        List of products
    """
    products = db.query(models.Product).offset(skip).limit(limit).all()
    return products

# PUBLIC_INTERFACE
@router.get("/{product_id}", response_model=schemas.Product)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """
    Get a specific product by ID.
    
    Args:
        product_id: ID of the product
        db: Database session
    
    Returns:
        Product details
    
    Raises:
        HTTPException: If product is not found
    """
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found"
        )
    return product

# PUBLIC_INTERFACE
@router.put("/{product_id}", response_model=schemas.Product)
def update_product(
    product_id: int,
    product_update: schemas.ProductUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a product.
    
    Args:
        product_id: ID of the product to update
        product_update: Updated product data
        db: Database session
    
    Returns:
        Updated product
    
    Raises:
        HTTPException: If product is not found or update fails
    """
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if db_product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found"
        )
    
    update_data = product_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_product, field, value)
    
    try:
        db.commit()
        db.refresh(db_product)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not update product"
        ) from e
    return db_product

# PUBLIC_INTERFACE
@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """
    Delete a product.
    
    Args:
        product_id: ID of the product to delete
        db: Database session
    
    Raises:
        HTTPException: If product is not found or delete fails
    """
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if db_product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found"
        )
    
    # Check if product has associated orders
    if db_product.orders:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete product with associated orders"
        )
    
    try:
        db.delete(db_product)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not delete product"
        ) from e
