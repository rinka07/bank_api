from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/auth", tags=["🔐 Authentification"])


@router.post(
    "/login",
    response_model=schemas.Token,
    summary="Connexion",
    description="Connecte un utilisateur (client ou admin banque) et retourne un JWT."
)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(
        models.User.email == form_data.username,
        models.User.is_active == True
    ).first()

    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth.create_access_token({"sub": user.id, "role": user.role.value})
    return {"access_token": token, "token_type": "bearer"}


@router.get(
    "/me",
    response_model=schemas.UserOutWithAccounts,
    summary="Mon profil",
    description="Retourne le profil et les comptes de l'utilisateur connecté."
)
def get_me(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    return current_user
