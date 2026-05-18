from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas, auth
from ..database import get_db
from ..utils import calculate_transfer_fee

router = APIRouter(prefix="/transactions", tags=["💸 Transactions"])


def _get_own_account(account_id: str, user: models.User, db: Session) -> models.Account:
    """Récupère un compte actif et vérifie que l'utilisateur en est propriétaire."""
    account = db.query(models.Account).filter(
        models.Account.id == account_id,
        models.Account.is_active == True
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="Compte introuvable ou inactif")
    if account.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Ce compte ne vous appartient pas")
    return account


# ─── Dépôt ───────────────────────────────────────────────────────

@router.post(
    "/deposit",
    response_model=schemas.TransactionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Effectuer un dépôt",
    description="Dépose de l'argent sur l'un de vos comptes. Aucun frais appliqué."
)
def deposit(
    payload: schemas.DepositRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    account = _get_own_account(payload.account_id, current_user, db)

    account.balance += payload.amount

    tx = models.Transaction(
        type=models.TransactionType.DEPOSIT,
        amount=payload.amount,
        fee=0.0,
        net_amount=payload.amount,
        description=payload.description or "Dépôt",
        receiver_account_id=account.id,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


# ─── Retrait ─────────────────────────────────────────────────────

@router.post(
    "/withdraw",
    response_model=schemas.TransactionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Effectuer un retrait",
    description="Retire de l'argent depuis l'un de vos comptes. Aucun frais appliqué."
)
def withdraw(
    payload: schemas.WithdrawalRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    account = _get_own_account(payload.account_id, current_user, db)

    if account.balance < payload.amount:
        raise HTTPException(
            status_code=400,
            detail=f"Solde insuffisant. Solde actuel : {account.balance:.2f} FCFA"
        )

    account.balance -= payload.amount

    tx = models.Transaction(
        type=models.TransactionType.WITHDRAWAL,
        amount=payload.amount,
        fee=0.0,
        net_amount=payload.amount,
        description=payload.description or "Retrait",
        sender_account_id=account.id,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


# ─── Aperçu du transfert ─────────────────────────────────────────

@router.get(
    "/transfer/preview",
    response_model=schemas.TransferPreview,
    summary="Aperçu des frais de transfert",
    description=(
        "Calcule les frais avant d'effectuer un transfert. "
        "**1%** si les deux comptes sont dans la même banque, **2.5%** sinon."
    )
)
def preview_transfer(
    sender_account_id: str,
    receiver_account_id: str,
    amount: float,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Le montant doit être positif")

    sender = _get_own_account(sender_account_id, current_user, db)
    receiver = db.query(models.Account).filter(
        models.Account.id == receiver_account_id,
        models.Account.is_active == True
    ).first()
    if not receiver:
        raise HTTPException(status_code=404, detail="Compte destinataire introuvable")

    fee_pct = calculate_transfer_fee(sender, receiver)
    fee_amount = amount * fee_pct
    net_received = amount - fee_amount
    same_bank = sender.bank_id == receiver.bank_id

    return schemas.TransferPreview(
        amount=amount,
        fee_percent=fee_pct * 100,
        fee_amount=round(fee_amount, 2),
        net_received=round(net_received, 2),
        same_bank=same_bank,
    )


# ─── Transfert ───────────────────────────────────────────────────

@router.post(
    "/transfer",
    response_model=schemas.TransactionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Effectuer un transfert",
    description=(
        "Transfère de l'argent vers un autre compte (le vôtre ou celui d'un autre client). "
        "\n\n**Frais :** 1% (même banque) ou 2.5% (banque différente). "
        "Les frais sont déduits du montant envoyé."
    )
)
def transfer(
    payload: schemas.TransferRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    if payload.sender_account_id == payload.receiver_account_id:
        raise HTTPException(status_code=400, detail="Impossible de transférer vers le même compte")

    sender = _get_own_account(payload.sender_account_id, current_user, db)
    receiver = db.query(models.Account).filter(
        models.Account.id == payload.receiver_account_id,
        models.Account.is_active == True
    ).first()
    if not receiver:
        raise HTTPException(status_code=404, detail="Compte destinataire introuvable ou inactif")

    fee_pct = calculate_transfer_fee(sender, receiver)
    fee_amount = payload.amount * fee_pct
    net_amount = payload.amount - fee_amount

    if sender.balance < payload.amount:
        raise HTTPException(
            status_code=400,
            detail=f"Solde insuffisant. Solde actuel : {sender.balance:.2f} FCFA"
        )

    # Débiter l'envoyeur (montant total)
    sender.balance -= payload.amount
    # Créditer le receveur (montant net)
    receiver.balance += net_amount

    tx = models.Transaction(
        type=models.TransactionType.TRANSFER,
        amount=payload.amount,
        fee=round(fee_amount, 2),
        net_amount=round(net_amount, 2),
        description=payload.description or "Transfert",
        sender_account_id=sender.id,
        receiver_account_id=receiver.id,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx
