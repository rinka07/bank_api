from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas, auth
from ..database import get_db
from ..utils import generate_account_number

router = APIRouter(prefix="/accounts", tags=["💳 Comptes bancaires"])


@router.post(
    "/",
    response_model=schemas.AccountOut,
    status_code=status.HTTP_201_CREATED,
    summary="Ouvrir un nouveau compte",
    description=(
        "Un client peut ouvrir un compte dans n'importe quelle banque active. "
        "Il peut avoir plusieurs comptes dans la même banque ou dans des banques différentes."
    )
)
def open_account(
    payload: schemas.AccountCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    bank = db.query(models.Bank).filter(
        models.Bank.id == payload.bank_id,
        models.Bank.is_active == True
    ).first()
    if not bank:
        raise HTTPException(status_code=404, detail="Banque introuvable ou inactive.")

    if payload.initial_deposit < 0:
        raise HTTPException(status_code=400, detail="Le dépôt initial ne peut pas être négatif.")

    account = models.Account(
        account_number=generate_account_number(bank.code, db),
        balance=payload.initial_deposit,
        owner_id=current_user.id,
        bank_id=bank.id,
    )
    db.add(account)

    # Enregistrer le dépôt initial comme transaction si > 0
    if payload.initial_deposit > 0:
        tx = models.Transaction(
            type=models.TransactionType.DEPOSIT,
            amount=payload.initial_deposit,
            fee=0.0,
            net_amount=payload.initial_deposit,
            description="Dépôt initial à l'ouverture du compte",
            receiver_account_id=account.id,
        )
        db.add(tx)

    db.commit()
    db.refresh(account)
    return account


@router.get(
    "/my",
    response_model=List[schemas.AccountOut],
    summary="Mes comptes",
    description="Retourne tous les comptes du client connecté. Un client ne voit que ses propres comptes."
)
def my_accounts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    return db.query(models.Account).filter(
        models.Account.owner_id == current_user.id,
        models.Account.is_active == True
    ).all()


@router.get(
    "/{account_id}",
    response_model=schemas.AccountOut,
    summary="Détails d'un compte",
    description="Un client ne peut voir que ses propres comptes."
)
def get_account(
    account_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    account = db.query(models.Account).filter(
        models.Account.id == account_id,
        models.Account.is_active == True
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="Compte introuvable")

    # Sécurité : un client ne peut voir que ses propres comptes
    if current_user.role == models.UserRole.CLIENT and account.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé à ce compte")

    return account


@router.get(
    "/{account_id}/transactions",
    response_model=List[schemas.TransactionOut],
    summary="Historique des transactions d'un compte",
    description="Retourne toutes les transactions (envoyées et reçues) d'un compte. Réservé au propriétaire."
)
def account_transactions(
    account_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Compte introuvable")

    if current_user.role == models.UserRole.CLIENT and account.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé à ce compte")

    transactions = (
        db.query(models.Transaction)
        .filter(
            (models.Transaction.sender_account_id == account_id) |
            (models.Transaction.receiver_account_id == account_id)
        )
        .order_by(models.Transaction.created_at.desc())
        .all()
    )
    return transactions


@router.delete(
    "/{account_id}",
    response_model=schemas.MessageResponse,
    summary="Fermer un compte",
    description="Désactive un compte bancaire. Le compte doit avoir un solde nul pour être fermé."
)
def close_account(
    account_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    account = db.query(models.Account).filter(
        models.Account.id == account_id,
        models.Account.is_active == True
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="Compte introuvable")

    if current_user.role == models.UserRole.CLIENT and account.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Vous ne pouvez fermer que vos propres comptes")

    if account.balance > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Impossible de fermer ce compte : solde restant de {account.balance} FCFA. Veuillez d'abord vider votre compte."
        )

    account.is_active = False
    db.commit()
    return {"message": f"Le compte {account.account_number} a été fermé."}
