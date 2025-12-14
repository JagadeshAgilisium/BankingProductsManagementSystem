import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from database import Base, obtain_db_session
from config import settings

engine = create_engine(
    settings.SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[obtain_db_session] = override_get_db
client = TestClient(app)


@pytest.fixture
def auth_header():
    # Register User
    client.post("/register", json={"username": "testadmin", "password": "password123"})

    # Login
    response = client.post("/login", data={"username": "testadmin", "password": "password123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
# Root test
def test_root_response():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["app_name"] == "Banking Asset Inventory System"
    assert response.json()["assignee"] == "Jagadesh PJ"
    assert response.json()["employee id"] == "10461"
    assert response.json()["email"] == "jagadesh.jayaraman@agilisium.com"

# Health test
def test_health_response():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["app_name"] == "Banking Asset Inventory System"
    assert "services" in response.json()

# New user - Register and Login
def test_new_user_register_and_login_response():
    username = "admin"
    password = "admin@3150"
    user_register_response = client.post("/register", json={"username": username, "password": password})
    assert user_register_response.status_code == 200
    assert "access_token" in user_register_response.json()

    duplicate_user_register_response = client.post("/register", json={"username": username, "password": password})
    assert duplicate_user_register_response.status_code == 400

    login_response = client.post("/login", data={"username": username, "password": password})
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()

# New Category and Supplier
def test_create_category_and_supplier_response(auth_header):
    create_catetory_response = client.post("/categories/", json={"name": "C1-Electronics"}, headers=auth_header)
    assert create_catetory_response.status_code == 200
    assert create_catetory_response.json()["name"] == "C1-Electronics"
    
    create_supplier_response = client.post("/suppliers/", json={"name": "AGSCorp", "contact_email": "sales@agscorp.com"}, headers=auth_header)
    assert create_supplier_response.status_code == 200
    assert create_supplier_response.json()["name"] == "AGSCorp"

# CRUD Operations
def test_banking_product_management_crud_response(auth_header):
    client.post("/categories/", json={"name": "Furniture"}, headers=auth_header)
    client.post("/suppliers/", json={"name": "Pearl Wood-works", "contact_email": "sales@pearlwoodworks.com"}, headers=auth_header)
    
    # CREATE
    product_data = {
        "name": "Office Desk",
        "description": "A sleek, durable desk designed for efficient, professional workspaces.",
        "price": 8000.0,
        "stock_quantity": 20,
        "category_id": 1,
        "supplier_id": 1
    }
    
    response = client.post("/products/", json=product_data, headers=auth_header)
    
    if response.status_code == 500:
        pytest.fail("Failed due to category and supplier id!")
        
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "Office Desk"
    assert data["stock_quantity"] == 20
    assert data["price"] == 8000.0

    # READ
    product_id = data["id"]
    get_response = client.get("/products/")
    assert get_response.status_code == 200
    assert len(get_response.json()) > 0

    # UPDATE
    updated_product_data = {
        "name": "Office Desk - Circular",
        "description": "A sleek, durable wooden desk designed for efficient, professional workspaces.",
        "price": 9000.0,
        "stock_quantity": 15,
        "category_id": 1,
        "supplier_id": 1
    }
    update_response = client.put(f"/products/{product_id}", json=updated_product_data, headers=auth_header)
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Office Desk - Circular"
    assert update_response.json()["stock_quantity"] == 15
    assert update_response.json()["price"] == 9000.0

    # DELETE
    del_response = client.delete(f"/products/{product_id}", headers=auth_header)
    assert del_response.status_code == 200
    
    get_response = client.get(f"/products/")
    products = get_response.json()
    assert not any(p['id'] == product_id for p in products)

# Sales report
def test_sales(auth_header):
    product_data = {
        "name": "Office Desk",
        "description": "A sleek, durable desk designed for efficient, professional workspaces.",
        "price": 8000.0,
        "stock_quantity": 20,
        "category_id": 1,
        "supplier_id": 1
    }
    productResponse = client.post("/products/", json=product_data, headers=auth_header)
    productId = productResponse.json()["id"]

    # Positive Sale
    positive_sale_response = client.post("/sales/", json={"product_id": productId, "quantity_sold": 4}, headers=auth_header)
    assert positive_sale_response.status_code == 200
    assert positive_sale_response.json()["new_stock_count"] == 16

    # Negative Sale
    negative_sale_response = client.post("/sales/", json={"product_id": productId, "quantity_sold": 100}, headers=auth_header)
    assert negative_sale_response.status_code == 400
    assert negative_sale_response.json()["detail"] == "Not enough stock available"