from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base
from .routers import auth_router, banks, users, accounts, transactions

# ─── Créer les tables au démarrage ────────────────────────────────
Base.metadata.create_all(bind=engine)

# ─── Application FastAPI ──────────────────────────────────────────
app = FastAPI(
    title="🏦 Banking API",
    description="""
## API de gestion multi-banques

Cette API permet à des **banques** de s'inscrire et à des **clients** d'ouvrir des comptes, 
effectuer des dépôts, retraits et transferts.

---

### 🔐 Authentification
Tous les endpoints (sauf inscription et login) nécessitent un **JWT Bearer token**.
Utilisez `/auth/login` pour obtenir un token, puis cliquez **Authorize** en haut à droite.

---

### 👥 Rôles
| Rôle | Capacités |
|------|-----------|
| **Admin** | Gérer les clients et comptes de sa banque |
| **Client** | Gérer ses propres comptes et transactions |

---

### 💸 Frais de transfert
| Type | Frais |
|------|-------|
| Même banque | **1%** |
| Banques différentes | **2.5%** |

---
    """,
    version="1.0.0",
    contact={
        "name": "Banking API Support",
        "email": "support@banking-api.cm",
    },
    license_info={
        "name": "MIT",
    },
    swagger_ui_parameters={
        "persistAuthorization": True,   # Le token reste après refresh de la page
        "docExpansion": "none",          # Les sections sont fermées par défaut
        "tagsSorter": "alpha",
        "operationsSorter": "alpha",
    },
)

# ─── CORS ─────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # En prod, restreindre aux domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────
app.include_router(auth_router.router)
app.include_router(banks.router)
app.include_router(users.router)
app.include_router(accounts.router)
app.include_router(transactions.router)


# ─── Health check ─────────────────────────────────────────────────
@app.get("/", tags=["📡 Santé"], summary="Health check")
def root():
    return {
        "status": "ok",
        "message": "Banking API is running 🚀",
        "docs": "/docs",
        "redoc": "/redoc",
    }
