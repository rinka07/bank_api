from pydantic import BaseModel, EmailStr, Field, model_validator
from typing import Optional, List
from datetime import datetime
from .models import UserRole, TransactionType


# ═══════════════════════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════════════════════

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[str] = None
    role: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ═══════════════════════════════════════════════════════════════════
# BANK
# ═══════════════════════════════════════════════════════════════════

class BankCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, example="Banque Centrale Africaine")
    code: str = Field(..., min_length=2, max_length=10, example="BCA")
    email: EmailStr = Field(..., example="contact@bca.cm")
    phone: Optional[str] = Field(None, example="+237 600 000 000")
    address: Optional[str] = Field(None, example="Yaoundé, Cameroun")
    # Mot de passe admin de la banque
    admin_password: str = Field(..., min_length=8, example="SecurePass123!")


class BankUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None


class BankOut(BaseModel):
    id: str
    name: str
    code: str
    email: str
    phone: Optional[str]
    address: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class BankWithStats(BankOut):
    total_clients: int
    total_accounts: int
    total_balance: float


# ═══════════════════════════════════════════════════════════════════
# USER
# ═══════════════════════════════════════════════════════════════════

class UserCreate(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=80, example="Jean")
    last_name: str = Field(..., min_length=2, max_length=80, example="Dupont")
    email: EmailStr = Field(..., example="jean.dupont@email.com")
    phone: Optional[str] = Field(None, example="+237 699 000 000")
    password: str = Field(..., min_length=8, example="MonMotDePasse123!")
    bank_id: str = Field(..., example="uuid-de-la-banque")


class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=2, max_length=80)
    last_name: Optional[str] = Field(None, min_length=2, max_length=80)
    phone: Optional[str] = None
    is_active: Optional[bool] = None


class UserOut(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str]
    role: UserRole
    is_active: bool
    bank_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class UserOutWithAccounts(UserOut):
    accounts: List["AccountOut"] = []


# ═══════════════════════════════════════════════════════════════════
# ACCOUNT
# ═══════════════════════════════════════════════════════════════════

class AccountCreate(BaseModel):
    bank_id: str = Field(..., example="uuid-de-la-banque")
    initial_deposit: float = Field(0.0, ge=0, example=50000.0)


class AccountOut(BaseModel):
    id: str
    account_number: str
    balance: float
    is_active: bool
    bank_id: str
    owner_id: str
    created_at: datetime

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════════
# TRANSACTIONS
# ═══════════════════════════════════════════════════════════════════

class DepositRequest(BaseModel):
    account_id: str = Field(..., example="uuid-du-compte")
    amount: float = Field(..., gt=0, example=10000.0)
    description: Optional[str] = Field(None, example="Dépôt initial")


class WithdrawalRequest(BaseModel):
    account_id: str = Field(..., example="uuid-du-compte")
    amount: float = Field(..., gt=0, example=5000.0)
    description: Optional[str] = Field(None, example="Retrait ATM")


class TransferRequest(BaseModel):
    sender_account_id: str = Field(..., example="uuid-du-compte-envoyeur")
    receiver_account_id: str = Field(..., example="uuid-du-compte-receveur")
    amount: float = Field(..., gt=0, example=20000.0)
    description: Optional[str] = Field(None, example="Paiement loyer")


class TransactionOut(BaseModel):
    id: str
    type: TransactionType
    amount: float
    fee: float
    net_amount: float
    description: Optional[str]
    sender_account_id: Optional[str]
    receiver_account_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class TransferPreview(BaseModel):
    """Aperçu avant confirmation d'un transfert"""
    amount: float
    fee_percent: float
    fee_amount: float
    net_received: float
    same_bank: bool


# ═══════════════════════════════════════════════════════════════════
# GENERIC
# ═══════════════════════════════════════════════════════════════════

class MessageResponse(BaseModel):
    message: str


# Résoudre les références circulaires
UserOutWithAccounts.model_rebuild()
