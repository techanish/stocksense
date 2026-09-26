from typing import Optional
from pydantic import BaseModel, EmailStr


# ── Auth ─────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Optional[str] = "staff"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


# ── Warehouses ────────────────────────────────────────────────────────────────

class WarehouseCreate(BaseModel):
    name: str
    code: str
    address: Optional[str] = None


class LocationCreate(BaseModel):
    name: str
    code: str


# ── Categories ────────────────────────────────────────────────────────────────

class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None


# ── Products ──────────────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    name: str
    sku: str
    category_id: Optional[int] = None
    unit_of_measure: str
    reorder_level: Optional[float] = 0
    description: Optional[str] = None
    initial_stock: Optional[float] = 0
    initial_location_id: Optional[int] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[int] = None
    unit_of_measure: Optional[str] = None
    reorder_level: Optional[float] = None
    description: Optional[str] = None
    is_active: Optional[int] = None


# ── Receipts ──────────────────────────────────────────────────────────────────

class ReceiptLineCreate(BaseModel):
    product_id: int
    location_id: int
    quantity_expected: float
    quantity_received: Optional[float] = 0


class ReceiptCreate(BaseModel):
    supplier: Optional[str] = None
    warehouse_id: int
    notes: Optional[str] = None
    lines: list[ReceiptLineCreate] = []


class ReceiptUpdate(BaseModel):
    supplier: Optional[str] = None
    notes: Optional[str] = None
    lines: Optional[list[ReceiptLineCreate]] = None


# ── Deliveries ────────────────────────────────────────────────────────────────

class DeliveryLineCreate(BaseModel):
    product_id: int
    location_id: int
    quantity_demanded: float
    quantity_picked: Optional[float] = 0


class DeliveryCreate(BaseModel):
    customer: Optional[str] = None
    warehouse_id: int
    notes: Optional[str] = None
    lines: list[DeliveryLineCreate] = []


class DeliveryUpdate(BaseModel):
    customer: Optional[str] = None
    notes: Optional[str] = None
    lines: Optional[list[DeliveryLineCreate]] = None


# ── Transfers ─────────────────────────────────────────────────────────────────

class TransferLineCreate(BaseModel):
    product_id: int
    quantity: float


class TransferCreate(BaseModel):
    from_location_id: int
    to_location_id: int
    notes: Optional[str] = None
    lines: list[TransferLineCreate] = []


# ── Adjustments ───────────────────────────────────────────────────────────────

class AdjustmentLineCreate(BaseModel):
    product_id: int
    quantity_counted: float


class AdjustmentCreate(BaseModel):
    location_id: int
    reason: Optional[str] = None
    notes: Optional[str] = None
    lines: list[AdjustmentLineCreate] = []
