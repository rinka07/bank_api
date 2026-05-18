import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Float, Boolean, DateTime, ForeignKey, Enum, Text
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from .database import Base


def gen_uuid():
    return str(uuid.uuid4())


# ─── Enums ────────────────────────────────────────────────────────────────────

class TransactionType(str, enum.Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"


class UserRole(str, enum.Enum):
    ADMIN = "admin"      # Administrateur de la banque
    CLIENT = "client"    # Client


# ─── Bank ─────────────────────────────────────────────────────────────────────

class Bank(Base):
    __tablename__ = "banks"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String(100), unique=True, nullable=False, index=True)
    code = Column(String(10), unique=True, nullable=False)   # code court ex: "BCA"
    email = Column(String(150), unique=True, nullable=False)
    phone = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    users = relationship("User", back_populates="bank", cascade="all, delete-orphan")
    accounts = relationship("Account", back_populates="bank", cascade="all, delete-orphan")


# ─── User ─────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    first_name = Column(String(80), nullable=False)
    last_name = Column(String(80), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.CLIENT, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    bank_id = Column(UUID(as_uuid=False), ForeignKey("banks.id"), nullable=True)
    bank = relationship("Bank", back_populates="users")

    # Un utilisateur peut avoir plusieurs comptes
    accounts = relationship("Account", back_populates="owner", cascade="all, delete-orphan")


# ─── Account ──────────────────────────────────────────────────────────────────

class Account(Base):
    __tablename__ = "accounts"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    account_number = Column(String(20), unique=True, nullable=False, index=True)
    balance = Column(Float, default=0.0, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="accounts")

    bank_id = Column(UUID(as_uuid=False), ForeignKey("banks.id"), nullable=False)
    bank = relationship("Bank", back_populates="accounts")

    # Transactions envoyées ou reçues
    sent_transactions = relationship(
        "Transaction", foreign_keys="Transaction.sender_account_id", back_populates="sender_account"
    )
    received_transactions = relationship(
        "Transaction", foreign_keys="Transaction.receiver_account_id", back_populates="receiver_account"
    )


# ─── Transaction ──────────────────────────────────────────────────────────────

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    type = Column(Enum(TransactionType), nullable=False)
    amount = Column(Float, nullable=False)          # Montant brut envoyé/retiré
    fee = Column(Float, default=0.0)                # Frais appliqués
    net_amount = Column(Float, nullable=False)      # Montant réellement crédité
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    sender_account_id = Column(UUID(as_uuid=False), ForeignKey("accounts.id"), nullable=True)
    receiver_account_id = Column(UUID(as_uuid=False), ForeignKey("accounts.id"), nullable=True)

    sender_account = relationship("Account", foreign_keys=[sender_account_id], back_populates="sent_transactions")
    receiver_account = relationship("Account", foreign_keys=[receiver_account_id], back_populates="received_transactions")
