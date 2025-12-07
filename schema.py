from pydantic import BaseModel
from typing import Optional, List

# --- Auth Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    username: str
    password: str

# --- Category Schemas ---
class CategoryBase(BaseModel):
    name: str

class CategoryCreate(CategoryBase):
    pass

class Category(CategoryBase):
    id: int
    class Config:
        from_attributes = True

# --- Supplier Schemas ---
class SupplierBase(BaseModel):
    name: str
    contact_email: str

class SupplierCreate(SupplierBase):
    pass

class Supplier(SupplierBase):
    id: int
    class Config:
        from_attributes = True

# --- Product Schemas ---
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    stock_quantity: int
    category_id: int
    supplier_id: int

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    stock_quantity: int

class Product(ProductBase):
    id: int
    category: Optional[Category] = None
    supplier: Optional[Supplier] = None
    class Config:
        from_attributes = True

class Sale(BaseModel):
    product_id: int
    quantity_sold: int