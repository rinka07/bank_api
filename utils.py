import random
import string
from sqlalchemy.orm import Session
from . import models


def generate_account_number(bank_code: str, db: Session) -> str:
    """Génère un numéro de compte unique: CODE-XXXXXXXXXXXXXXXX"""
    while True:
        digits = "".join(random.choices(string.digits, k=12))
        account_number = f"{bank_code.upper()}-{digits}"
        exists = db.query(models.Account).filter(
            models.Account.account_number == account_number
        ).first()
        if not exists:
            return account_number


def calculate_transfer_fee(sender_account: models.Account, receiver_account: models.Account) -> float:
    """
    Calcule le pourcentage de frais selon si les deux comptes sont dans la même banque.
    - Même banque   : 1.0%
    - Banques diff. : 2.5%
    """
    if sender_account.bank_id == receiver_account.bank_id:
        return 0.01   # 1%
    return 0.025      # 2.5%
