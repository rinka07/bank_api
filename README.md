# 🏦 Banking API

API REST de gestion multi-banques construite avec **FastAPI**, **PostgreSQL (Neon)** et déployable sur **Render**.

---

## ✨ Fonctionnalités

- 🏦 **Multi-banques** — plusieurs banques peuvent s'inscrire, chacune avec son propre espace
- 👤 **Clients** — inscription, choix de la banque, plusieurs comptes possibles
- 💳 **Comptes** — un client peut ouvrir plusieurs comptes dans une ou plusieurs banques
- 💸 **Transactions** — dépôt, retrait, transfert avec frais automatiques
- 🔒 **Sécurité** — JWT, isolation des données (un client ne voit que ses comptes)
- 📚 **Swagger UI** — documentation interactive disponible sur `/docs`

### Frais de transfert
| Scénario | Frais |
|----------|-------|
| Même banque | **1%** |
| Banques différentes | **2.5%** |

---

## 🚀 Installation locale

### 1. Cloner et installer

```bash
git clone <votre-repo>
cd banking-api
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurer les variables d'environnement

```bash
cp .env.example .env
```

Édite `.env` et remplis :

```env
# Copie ta connection string depuis console.neon.tech
DATABASE_URL=postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/bankingdb?sslmode=require

# Génère avec: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=ta_cle_secrete_ici
```

### 3. Lancer l'API

```bash
uvicorn banking_api.main:app --reload
```

L'API est accessible sur : http://localhost:8000  
Swagger UI : http://localhost:8000/docs

---

## 🗄️ Configuration Neon (PostgreSQL)

1. Va sur [console.neon.tech](https://console.neon.tech)
2. Crée un projet → copie la **Connection string**
3. Colle-la dans `DATABASE_URL` dans ton `.env`
4. Les tables se créent **automatiquement** au premier démarrage

---

## ☁️ Déploiement sur Render

### Option A — Via le dashboard Render (recommandé)

1. Push ton code sur GitHub
2. Va sur [render.com](https://render.com) → **New Web Service**
3. Connecte ton repo GitHub
4. Configure :
   - **Build Command :** `pip install -r requirements.txt`
   - **Start Command :** `uvicorn banking_api.main:app --host 0.0.0.0 --port $PORT`
5. Ajoute les **variables d'environnement** :
   - `DATABASE_URL` → ta connection string Neon
   - `SECRET_KEY` → une clé aléatoire (ou laisse Render la générer via `render.yaml`)
   - `ALGORITHM` → `HS256`
   - `ACCESS_TOKEN_EXPIRE_MINUTES` → `60`

### Option B — Via render.yaml (Infrastructure as Code)

Le fichier `render.yaml` est déjà configuré. Il suffit de :
1. Push sur GitHub
2. Dans Render → **New → Blueprint**
3. Sélectionner ton repo
4. Définir manuellement `DATABASE_URL` (non synchronisée pour sécurité)

---

## 📖 Utilisation de l'API

### 1. Inscrire une banque

```bash
POST /banks/
{
  "name": "Banque Centrale Africaine",
  "code": "BCA",
  "email": "admin@bca.cm",
  "admin_password": "SecurePass123!"
}
```

### 2. Se connecter (admin ou client)

```bash
POST /auth/login
Content-Type: application/x-www-form-urlencoded
username=admin@bca.cm&password=SecurePass123!
```

→ Récupère le `access_token` et utilise-le dans l'en-tête :
`Authorization: Bearer <token>`

### 3. Inscrire un client

```bash
POST /users/register
{
  "first_name": "Jean",
  "last_name": "Dupont",
  "email": "jean@email.com",
  "password": "MonMotDePasse123!",
  "bank_id": "uuid-de-la-banque"
}
```

### 4. Ouvrir un compte supplémentaire

```bash
POST /accounts/
Authorization: Bearer <token>
{
  "bank_id": "uuid-de-la-banque",
  "initial_deposit": 50000
}
```

### 5. Effectuer un transfert

```bash
# Voir les frais avant
GET /transactions/transfer/preview?sender_account_id=...&receiver_account_id=...&amount=10000

# Effectuer le transfert
POST /transactions/transfer
{
  "sender_account_id": "...",
  "receiver_account_id": "...",
  "amount": 10000,
  "description": "Paiement loyer"
}
```

---

## 📁 Structure du projet

```
banking-api/
├── main.py              # Point d'entrée FastAPI + configuration Swagger
├── config.py            # Variables d'environnement (pydantic-settings)
├── database.py          # Connexion Neon/PostgreSQL
├── models.py            # Modèles SQLAlchemy (Bank, User, Account, Transaction)
├── schemas.py           # Schémas Pydantic (validation entrées/sorties)
├── auth.py              # JWT + hashage des mots de passe
├── utils.py             # Helpers (numéro de compte, calcul des frais)
├── routers/
│   ├── auth_router.py   # POST /auth/login, GET /auth/me
│   ├── banks.py         # CRUD /banks/
│   ├── users.py         # CRUD /users/
│   ├── accounts.py      # CRUD /accounts/
│   └── transactions.py  # POST /transactions/deposit|withdraw|transfer
├── requirements.txt
├── render.yaml          # Configuration déploiement Render
├── Procfile
└── .env.example
```

---

## 🔐 Sécurité

- Les mots de passe sont hashés avec **bcrypt**
- Chaque endpoint vérifie que le client **ne peut accéder qu'à ses propres données**
- Un admin ne peut gérer que **les clients de sa propre banque**
- Les tokens JWT expirent après **60 minutes** (configurable)
