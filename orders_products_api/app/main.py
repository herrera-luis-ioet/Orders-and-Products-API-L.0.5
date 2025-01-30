from fastapi import FastAPI
from .routers import products, orders
from . import models
from .database import engine
from fastapi.middleware.cors import CORSMiddleware

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Orders and Products API",
    description="""
    A comprehensive API for managing orders and products in an e-commerce system.
    
    ## Features
    
    * **Products Management**
        * Create, read, update, and delete products
        * Track product inventory
        * Manage product details and pricing
    
    * **Orders Management**
        * Create and manage orders
        * Automatic stock management
        * Order status tracking
    
    ## Error Handling
    
    The API uses standard HTTP status codes:
    * `200`: Successful operation
    * `201`: Resource created successfully
    * `204`: Resource deleted successfully
    * `400`: Bad request (validation error, insufficient stock)
    * `404`: Resource not found
    * `500`: Internal server error
    
    ## Rate Limiting
    
    * Default rate limit: 100 requests per minute
    * Burst: up to 200 requests
    
    ## Authentication
    
    * Currently using development mode (no authentication required)
    * Production deployment should implement proper authentication
    
    ## Data Models
    
    * **Product**: Represents items available for purchase
    * **Order**: Represents customer orders with associated products
    
    For detailed schema information, refer to the schemas section below.
    """,
    version="1.0.0",
    contact={
        "name": "API Support",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=[
        {
            "name": "products",
            "description": "Operations with products. Manage product inventory, pricing, and details.",
        },
        {
            "name": "orders",
            "description": "Operations with orders. Create and manage customer orders with automatic stock management.",
        }
    ]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(products.router)
app.include_router(orders.router)

@app.get("/")
async def root():
    return {"message": "Welcome to Orders and Products API"}
