import io
import pandas as pd
from config import settings
from sqlalchemy import text
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import models, schema, authentication, database
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import FastAPI, Depends, HTTPException, status

models.Base.metadata.create_all(bind=database.db_engine)

app = FastAPI(title= settings.PROJECT_NAME, version = settings.VERSION)
# basic info
@app.get("/", tags=["System"])
def basic_info():
    basic_details = {
        "app_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "assignee": settings.OWNER_NAME,
        "employee id": settings.EMP_ID,
        "email": settings.EMAIL_ID
    }
    return basic_details

# app health
@app.get("/health", tags=["System"])
def health_status(db: Session = Depends(database.obtain_db_session)):
    health_report = {
        "app_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "server_time": datetime.now(timezone.utc).isoformat() + " UTC",
        "services": {
            "api": "online",
            "database": "unknown"
        }
    }

    try:
        db.execute(text("SELECT 1"))
        health_report["services"]["database"] = "online"
        return health_report
    except Exception as e:
        health_report["services"]["database"] = "offline"
        health_report["error_details"] = str(e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail=health_report
        )

# logib auth check
@app.post("/register", response_model=schema.Token)
def register_user(user: schema.UserCreate, db: Session = Depends(database.obtain_db_session)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_pwd = authentication.get_password_hash(user.password)
    new_user = models.User(username=user.username, hashed_password=hashed_pwd)
    db.add(new_user)
    db.commit()
    access_token = authentication.generate_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/login", response_model=schema.Token)
def login_handler(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.obtain_db_session)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not authentication.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect creds")
    access_token = authentication.generate_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


# app func
@app.post("/categories/", response_model=schema.Category)
def create_category(category: schema.CategoryCreate, db: Session = Depends(database.obtain_db_session), current_user: str = Depends(authentication.verify_user_session)):
    db_cat = models.Category(name=category.name)
    db.add(db_cat)
    db.commit()
    db.refresh(db_cat)
    return db_cat

@app.post("/suppliers/", response_model=schema.Supplier)
def create_supplier(supplier: schema.SupplierCreate, db: Session = Depends(database.obtain_db_session), current_user: str = Depends(authentication.verify_user_session)):
    db_sup = models.Supplier(name=supplier.name, contact_email=supplier.contact_email)
    db.add(db_sup)
    db.commit()
    db.refresh(db_sup)
    return db_sup

# app crud
@app.post("/products/", response_model=schema.Product)
def create_product(product: schema.ProductCreate, db: Session = Depends(database.obtain_db_session), current_user: str = Depends(authentication.verify_user_session)):
    db_product = models.Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@app.get("/products/", response_model=List[schema.Product])
def read_products(skip: int = 0, limit: int = 100, search: Optional[str] = None, db: Session = Depends(database.obtain_db_session)):
    query = db.query(models.Product)
    if search:
        query = query.filter(models.Product.name.contains(search))
    return query.offset(skip).limit(limit).all()

@app.put("/products/{product_id}", response_model=schema.Product)
def update_product(product_id: int, product_update: schema.ProductCreate, db: Session = Depends(database.obtain_db_session), current_user: str = Depends(authentication.verify_user_session)):
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    for key, value in product_update.dict().items():
        setattr(db_product, key, value)
    
    db.commit()
    db.refresh(db_product)
    return db_product

@app.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(database.obtain_db_session), current_user: str = Depends(authentication.verify_user_session)):
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(db_product)
    db.commit()
    return {"detail": "Product deleted"}


# app sales logic
@app.post("/sales/")
def make_sale(sale: schema.Sale, db: Session = Depends(database.obtain_db_session), current_user: str = Depends(authentication.verify_user_session)):
    db_product = db.query(models.Product).filter(models.Product.id == sale.product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if db_product.stock_quantity < sale.quantity_sold:
        raise HTTPException(status_code=400, detail="Not enough stock available")
    
    db_product.stock_quantity -= sale.quantity_sold
    db.commit()
    return {"message": "Sale successful", "new_stock_count": db_product.stock_quantity}

# app generate report
@app.get("/report/inventory")
def get_inventory_report(db: Session = Depends(database.obtain_db_session)):
    query = db.query(models.Product).statement
    df = pd.read_sql(query, db.bind)
    
    df['total_value'] = df['price'] * df['stock_quantity']
    
    stream = io.StringIO()
    df.to_csv(stream, index=False)
    response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=inventory_report.csv"
    return response