from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas, auth
from ..database import get_db
from ..auth import hash_password
from ..utils import generate_account_number

router = APIRouter(prefix="/users", tags=["👤 Utilisateurs"])


@router.post(
    "/register",
    response_model=schemas.UserOutWithAccounts,
    status_code=status.HTTP_201_CREATED,
    summary="Inscription d'un client",
    description=(
        "Permet à un client de s'inscrire et de choisir sa banque. "
        "Un compte bancaire principal est automatiquement créé à l'inscription."
    )
)
def register_client(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    # Vérifier que la banque existe
    bank = db.query(models.Bank).filter(
        models.Bank.id == payload.bank_id,
        models.Bank.is_active == True
    ).first()
    if not bank:
        raise HTTPException(status_code=404, detail="Banque introuvable ou inactive.")

    # Email unique
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Un compte avec cet email existe déjà.")

    user = models.User(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        phone=payload.phone,
        hashed_password=hash_password(payload.password),
        role=models.UserRole.CLIENT,
        bank_id=payload.bank_id,
    )
    db.add(user)
    db.flush()

    # Créer un premier compte bancaire automatiquement
    account = models.Account(
        account_number=generate_account_number(bank.code, db),
        balance=0.0,
        owner_id=user.id,
        bank_id=bank.id,
    )
    db.add(account)
    db.commit()
    db.refresh(user)
    return user


@router.get(
    "/",
    response_model=List[schemas.UserOut],
    summary="Liste des utilisateurs",
    description="Liste tous les utilisateurs de la banque de l'admin connecté."
)
def list_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin)
):
    return db.query(models.User).filter(
        models.User.bank_id == current_user.bank_id,
        models.User.role == models.UserRole.CLIENT
    ).all()


@router.get(
    "/{user_id}",
    response_model=schemas.UserOutWithAccounts,
    summary="Détails d'un utilisateur",
    description="Un client peut voir son propre profil. Un admin peut voir n'importe quel client de sa banque."
)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    # Un client ne peut voir que son propre profil
    if current_user.role == models.UserRole.CLIENT and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Accès refusé")

    # Un admin ne peut voir que les clients de sa banque
    if current_user.role == models.UserRole.ADMIN and user.bank_id != current_user.bank_id:
        raise HTTPException(status_code=403, detail="Ce client n'appartient pas à votre banque")

    return user


@router.put(
    "/{user_id}",
    response_model=schemas.UserOut,
    summary="Modifier un utilisateur",
    description="Un client peut modifier ses propres infos. Un admin peut modifier tout client de sa banque."
)
def update_user(
    user_id: str,
    payload: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    if current_user.role == models.UserRole.CLIENT and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Vous ne pouvez modifier que votre propre profil")

    if current_user.role == models.UserRole.ADMIN and user.bank_id != current_user.bank_id:
        raise HTTPException(status_code=403, detail="Ce client n'appartient pas à votre banque")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.delete(
    "/{user_id}",
    response_model=schemas.MessageResponse,
    summary="Supprimer un utilisateur",
    description="Désactive un compte utilisateur. Un admin peut supprimer les clients de sa banque."
)
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    if user.bank_id != current_user.bank_id:
        raise HTTPException(status_code=403, detail="Ce client n'appartient pas à votre banque")

    user.is_active = False
    db.commit()
    return {"message": f"L'utilisateur {user.first_name} {user.last_name} a été désactivé."}
