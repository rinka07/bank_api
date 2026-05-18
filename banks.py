from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas, auth
from ..database import get_db
from ..auth import hash_password

router = APIRouter(prefix="/banks", tags=["🏦 Banques"])


@router.post(
    "/",
    response_model=schemas.BankOut,
    status_code=status.HTTP_201_CREATED,
    summary="Inscrire une banque",
    description=(
        "Enregistre une nouvelle banque dans le système. "
        "Un compte administrateur est automatiquement créé pour gérer la banque. "
        "Le mot de passe fourni sera celui de l'admin."
    )
)
def register_bank(payload: schemas.BankCreate, db: Session = Depends(get_db)):
    # Vérifier unicité
    if db.query(models.Bank).filter(
        (models.Bank.name == payload.name) | (models.Bank.code == payload.code.upper()) | (models.Bank.email == payload.email)
    ).first():
        raise HTTPException(status_code=400, detail="Une banque avec ce nom, ce code ou cet email existe déjà.")

    bank = models.Bank(
        name=payload.name,
        code=payload.code.upper(),
        email=payload.email,
        phone=payload.phone,
        address=payload.address,
    )
    db.add(bank)
    db.flush()  # Obtenir l'ID sans commit

    # Créer l'utilisateur admin de la banque
    admin = models.User(
        first_name="Admin",
        last_name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.admin_password),
        role=models.UserRole.ADMIN,
        bank_id=bank.id,
    )
    db.add(admin)
    db.commit()
    db.refresh(bank)
    return bank


@router.get(
    "/",
    response_model=List[schemas.BankWithStats],
    summary="Liste des banques",
    description="Retourne toutes les banques avec leurs statistiques (clients, comptes, solde total)."
)
def list_banks(db: Session = Depends(get_db)):
    banks = db.query(models.Bank).filter(models.Bank.is_active == True).all()
    result = []
    for bank in banks:
        clients = db.query(models.User).filter(
            models.User.bank_id == bank.id,
            models.User.role == models.UserRole.CLIENT
        ).count()
        accounts = db.query(models.Account).filter(models.Account.bank_id == bank.id).all()
        total_balance = sum(a.balance for a in accounts)
        result.append(schemas.BankWithStats(
            **{c.name: getattr(bank, c.name) for c in bank.__table__.columns},
            total_clients=clients,
            total_accounts=len(accounts),
            total_balance=total_balance,
        ))
    return result


@router.get(
    "/{bank_id}",
    response_model=schemas.BankWithStats,
    summary="Détails d'une banque"
)
def get_bank(bank_id: str, db: Session = Depends(get_db)):
    bank = db.query(models.Bank).filter(models.Bank.id == bank_id).first()
    if not bank:
        raise HTTPException(status_code=404, detail="Banque introuvable")
    clients = db.query(models.User).filter(
        models.User.bank_id == bank.id,
        models.User.role == models.UserRole.CLIENT
    ).count()
    accounts = db.query(models.Account).filter(models.Account.bank_id == bank.id).all()
    return schemas.BankWithStats(
        **{c.name: getattr(bank, c.name) for c in bank.__table__.columns},
        total_clients=clients,
        total_accounts=len(accounts),
        total_balance=sum(a.balance for a in accounts),
    )


@router.get(
    "/{bank_id}/clients",
    response_model=List[schemas.UserOut],
    summary="Clients d'une banque",
    description="Liste tous les clients d'une banque. Réservé à l'admin de la banque."
)
def list_bank_clients(
    bank_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin)
):
    if current_user.bank_id != bank_id:
        raise HTTPException(status_code=403, detail="Vous n'administrez pas cette banque.")

    clients = db.query(models.User).filter(
        models.User.bank_id == bank_id,
        models.User.role == models.UserRole.CLIENT
    ).all()
    return clients


@router.put(
    "/{bank_id}",
    response_model=schemas.BankOut,
    summary="Modifier une banque",
    description="Met à jour les informations d'une banque. Réservé à l'admin de la banque."
)
def update_bank(
    bank_id: str,
    payload: schemas.BankUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin)
):
    if current_user.bank_id != bank_id:
        raise HTTPException(status_code=403, detail="Vous n'administrez pas cette banque.")

    bank = db.query(models.Bank).filter(models.Bank.id == bank_id).first()
    if not bank:
        raise HTTPException(status_code=404, detail="Banque introuvable")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(bank, field, value)

    db.commit()
    db.refresh(bank)
    return bank


@router.delete(
    "/{bank_id}",
    response_model=schemas.MessageResponse,
    summary="Supprimer une banque",
    description="Désactive une banque (soft delete). Réservé à l'admin de la banque."
)
def delete_bank(
    bank_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin)
):
    if current_user.bank_id != bank_id:
        raise HTTPException(status_code=403, detail="Vous n'administrez pas cette banque.")

    bank = db.query(models.Bank).filter(models.Bank.id == bank_id).first()
    if not bank:
        raise HTTPException(status_code=404, detail="Banque introuvable")

    bank.is_active = False
    db.commit()
    return {"message": f"La banque '{bank.name}' a été désactivée."}
