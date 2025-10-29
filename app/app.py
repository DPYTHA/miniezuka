import os
from datetime import datetime, timedelta
from functools import wraps
from flask import (
    Flask, request, redirect, url_for, session,
    jsonify, send_from_directory, make_response,render_template,
)
import threading
from time import sleep
from datetime import datetime, timezone, timedelta
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, request, jsonify, session, send_from_directory, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import requests
import json
from datetime import datetime
# -------------------- Configuration --------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(APP_DIR, "templates")
STATIC_DIR = os.path.join(APP_DIR, "static")

app = Flask(__name__, static_folder=STATIC_DIR)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-please")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")  # Pas de valeur par défaut en prod


# Configuration de la base de données avec validation
database_url = os.environ.get('DATABASE_URL', '')

if database_url:
    # Correction pour PostgreSQL sur Railway
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Fallback vers SQLite si DATABASE_URL n'est pas définie
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
db = SQLAlchemy(app)

# -------------------- Models --------------------
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(50), unique=True, nullable=False)
    country = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    pin_hash = db.Column(db.String(256), nullable=True)  # hashed PIN (4 digits)
    balance = db.Column(db.Float, default=0.0, nullable=False)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_admin = db.Column(db.Boolean, default=False)  # <-- nouveau champ pour admin

    deposits = db.relationship("Deposit", backref="user", lazy=True)
    transfers = db.relationship("Transfer", backref="user", lazy=True)
    withdraws = db.relationship("Withdraw", backref="user", lazy=True)  
    cashback_withdrawals = db.relationship("CashbackWithdrawal", backref="user", lazy=True)  

def create_admin():
    admin_phone = "+79879040719"
    existing_admin = User.query.filter_by(phone=admin_phone).first()

    if existing_admin:
        print("✅ Admin déjà existant :", existing_admin.phone)
    else:
        admin = User(
            first_name="Admin",
            last_name="Principal",
            phone=admin_phone,
            country="Russie",
            password_hash=generate_password_hash("admin123"),
            pin_hash=generate_password_hash("3008"),
            balance=0.0,
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print("🎉 Admin créé avec succès :", admin.phone)




from datetime import datetime

class Deposit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default="€")
    method = db.Column(db.String(50))
    country = db.Column(db.String(50))
    status = db.Column(db.String(20), default="pending")  # pending / approved / rejected
    note = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class Transfer(db.Model):
    __tablename__ = "transfers"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)  # sender
    recipient_phone = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), nullable=False)
    method = db.Column(db.String(50), nullable=True)  # ✅ NOUVEAU CHAMP POUR LA MÉTHODE
    status = db.Column(db.String(20), default="pending")  # pending, completed, rejected
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    note = db.Column(db.String(300), nullable=True)

# -------------------- Models --------------------

class Withdraw(db.Model):
    __tablename__ = "withdraws"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    net_amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(50))
    currency = db.Column(db.String(10))
    country = db.Column(db.String(50))
    status = db.Column(db.String(20), default="pending")  # pending / approved / rejected
    note = db.Column(db.String(255))  # <-- ajouté
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class CashbackWithdrawal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

# -------------------- Fees & Exchange Rates Models --------------------

class CurrencyConfig(db.Model):
    __tablename__ = "currency_configs"
    id = db.Column(db.Integer, primary_key=True)
    currency_code = db.Column(db.String(10), unique=True, nullable=False)  # XOF, EUR, USD, etc.
    currency_name = db.Column(db.String(50), nullable=False)
    transfer_fee_percent = db.Column(db.Float, default=2.5)  # Frais de transfert en %
    withdrawal_fee_percent = db.Column(db.Float, default=1.5)  # Frais de retrait en %
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class ExchangeRate(db.Model):
    __tablename__ = "exchange_rates"
    id = db.Column(db.Integer, primary_key=True)
    from_currency = db.Column(db.String(10), nullable=False)  # Devise source
    to_currency = db.Column(db.String(10), nullable=False)    # Devise cible
    rate = db.Column(db.Float, nullable=False)                # Taux de change
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Contrainte d'unicité pour la paire de devises
    __table_args__ = (db.UniqueConstraint('from_currency', 'to_currency', name='unique_currency_pair'),)

class CountryCurrency(db.Model):
    __tablename__ = "country_currencies"
    id = db.Column(db.Integer, primary_key=True)
    country_name = db.Column(db.String(100), unique=True, nullable=False)
    country_code = db.Column(db.String(5), unique=True, nullable=False)  # CI, ML, SN, etc.
    currency_code = db.Column(db.String(10), nullable=False)  # XOF, EUR, USD, etc.
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

# Fonction pour initialiser les données par défaut
def init_default_fees_and_rates():
    """Initialise les frais et taux de change par défaut"""
    with app.app_context():
        # Devises par pays par défaut
        default_countries = [
            {"name": "Côte d'Ivoire", "code": "CI", "currency": "XOF"},
            {"name": "Mali", "code": "ML", "currency": "XOF"},
            {"name": "Burkina Faso", "code": "BF", "currency": "XOF"},
            {"name": "Sénégal", "code": "SN", "currency": "XOF"},
            {"name": "Guinée", "code": "GN", "currency": "GNF"},
            {"name": "Russie", "code": "RU", "currency": "RUB"},
            {"name": "Canada", "code": "CA", "currency": "CAD"},
            {"name": "Cameroun", "code": "CM", "currency": "XAF"},
            {"name": "Niger", "code": "NE", "currency": "XOF"},
            {"name": "Togo", "code": "TG", "currency": "XOF"},
            {"name": "Bénin", "code": "BJ", "currency": "XOF"},
            {"name": "Ghana", "code": "GH", "currency": "GHS"},
            {"name": "Nigéria", "code": "NG", "currency": "NGN"},
            {"name": "Gabon", "code": "GA", "currency": "XAF"},
        ]
        
        for country in default_countries:
            if not CountryCurrency.query.filter_by(country_code=country["code"]).first():
                country_currency = CountryCurrency(
                    country_name=country["name"],
                    country_code=country["code"],
                    currency_code=country["currency"]
                )
                db.session.add(country_currency)

        # Frais par devise par défaut
        default_fees = [
            {"currency": "XOF", "name": "Franc CFA", "transfer_fee": 2.5, "withdrawal_fee": 1.5},
            {"currency": "GNF", "name": "Franc Guinéen", "transfer_fee": 2.5, "withdrawal_fee": 1.5},
            {"currency": "RUB", "name": "Rouble Russe", "transfer_fee": 3.0, "withdrawal_fee": 2.0},
            {"currency": "CAD", "name": "Dollar Canadien", "transfer_fee": 3.5, "withdrawal_fee": 2.5},
            {"currency": "XAF", "name": "Franc CFA", "transfer_fee": 2.5, "withdrawal_fee": 1.5},
            {"currency": "GHS", "name": "Cedi Ghanéen", "transfer_fee": 3.0, "withdrawal_fee": 2.0},
            {"currency": "NGN", "name": "Naira Nigérian", "transfer_fee": 3.0, "withdrawal_fee": 2.0},
            {"currency": "EUR", "name": "Euro", "transfer_fee": 2.0, "withdrawal_fee": 1.0},
            {"currency": "USD", "name": "Dollar US", "transfer_fee": 2.5, "withdrawal_fee": 1.5},
        ]
        
        for fee in default_fees:
            if not CurrencyConfig.query.filter_by(currency_code=fee["currency"]).first():
                currency_config = CurrencyConfig(
                    currency_code=fee["currency"],
                    currency_name=fee["name"],
                    transfer_fee_percent=fee["transfer_fee"],
                    withdrawal_fee_percent=fee["withdrawal_fee"]
                )
                db.session.add(currency_config)

        # Taux de change par défaut
        default_rates = [
            {"from": "XOF", "to": "XAF", "rate": 1.0},
            {"from": "XOF", "to": "GNF", "rate": 13.0},
            {"from": "XOF", "to": "RUB", "rate": 0.133},
            {"from": "XOF", "to": "CAD", "rate": 0.0022},
            {"from": "XAF", "to": "XOF", "rate": 1.0},
            {"from": "XAF", "to": "GNF", "rate": 12.0},
            {"from": "XAF", "to": "RUB", "rate": 0.129},
            {"from": "GNF", "to": "XOF", "rate": 0.077},
            {"from": "GNF", "to": "RUB", "rate": 0.011},
            {"from": "RUB", "to": "XOF", "rate": 6.6},
            {"from": "RUB", "to": "GNF", "rate": 90.0},
            {"from": "CAD", "to": "XOF", "rate": 450.0},
            {"from": "CAD", "to": "GNF", "rate": 6000.0},
            {"from": "CAD", "to": "RUB", "rate": 67.0},
        ]
        
        for rate in default_rates:
            if not ExchangeRate.query.filter_by(from_currency=rate["from"], to_currency=rate["to"]).first():
                exchange_rate = ExchangeRate(
                    from_currency=rate["from"],
                    to_currency=rate["to"],
                    rate=rate["rate"]
                )
                db.session.add(exchange_rate)

        db.session.commit()
        print("✅ Configuration des frais et taux de change initialisée")




# -------------------- Updated Helpers --------------------

def get_currency_for_country(country: str) -> str:
    """Récupère la devise d'un pays depuis la base de données"""
    country_currency = CountryCurrency.query.filter_by(country_name=country, is_active=True).first()
    if country_currency:
        return country_currency.currency_code
    
    # Fallback vers le mapping original si pas trouvé en base
    mapping = {
        "Côte d'Ivoire": "XOF", "Mali": "XOF", "Burkina Faso": "XOF", "Sénégal": "XOF",
        "Guinee": "GNF", "Ghana": "GHS", "Togo": "XOF", "Bénin": "XOF", "Nigéria": "NGN",
        "Russie": "RUB", "Cameroun": "XAF", "Canada": "CAD", "Gabon": "XAF"
    }
    return mapping.get(country, "XOF")

def get_transfer_fee(sender_currency: str) -> float:
    """Récupère les frais de transfert depuis la base de données"""
    config = CurrencyConfig.query.filter_by(currency_code=sender_currency, is_active=True).first()
    return config.transfer_fee_percent if config else 3.5  # Default

def get_withdrawal_fee(currency: str) -> float:
    """Récupère les frais de retrait depuis la base de données"""
    config = CurrencyConfig.query.filter_by(currency_code=currency, is_active=True).first()
    return config.withdrawal_fee_percent if config else 1.5  # Default

def get_exchange_rate(from_currency: str, to_currency: str) -> float:
    """Récupère le taux de change depuis la base de données"""
    if from_currency == to_currency:
        return 1.0
    
    rate = ExchangeRate.query.filter_by(
        from_currency=from_currency, 
        to_currency=to_currency,
        is_active=True
    ).first()
    
    return rate.rate if rate else 1.0  # Default

# -------------------- Helpers --------------------
def get_currency_for_country(country: str) -> str:
    """Simple currency mapping by country (extend as needed)."""
    mapping = {
        "Côte d'Ivoire": "XOF",
        "Mali": "XOF",
        "Burkina Faso": "XOF",
        "Sénégal": "XOF",
        "Guinee": "GNF",
        "Ghana": "GHS",
        "Togo": "XOF",
        "Bénin": "XOF",
        "Nigéria": "NGN",
        "Russie": "RUB",
        "Cameroun": "XAF",
        "Canada":"CAD",
        "Gabon":"XAF"
        # default
    }
    return mapping.get(country, "XOF")

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_authenticated"):
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated

def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return User.query.get(uid)


def send_notification_email(subject, message):
    from flask_mail import Message
    msg = Message(subject=subject, sender="noreply@miniezuka.com", recipients=["pythacademy@gmail.com"])
    msg.body = message
    Mail.send(msg)

# -------------------- Create DB (first run) --------------------
with app.app_context():
    db.create_all()

# -------------------- Static HTML serving (no Jinja) --------------------
@app.route("/")
def splash():
    # serve splash.html from templates folder
    return send_from_directory(TEMPLATES_DIR, "splash.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return send_from_directory(TEMPLATES_DIR, "register.html")

    # POST -> create user
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    phone = request.form.get("phone", "").strip()
    country = request.form.get("country", "").strip()
    password = request.form.get("password", "")

    if not (first_name and last_name and phone and country and password):
        return "Champs manquants", 400

    if User.query.filter_by(phone=phone).first():
        return "Utilisateur existant", 400

    user = User(
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        country=country,
        password_hash=generate_password_hash(password),
        balance=0.0
    )
    db.session.add(user)
    db.session.commit()

    # redirect to login_standard
    return redirect("/login")
from flask import request, redirect, session, make_response, send_from_directory
from werkzeug.security import check_password_hash




@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return send_from_directory(TEMPLATES_DIR, "login_standard.html")

    phone = request.form.get("phone", "").strip()
    password = request.form.get("password", "").strip()
    pin = request.form.get("pin", "").strip()

    if not phone:
        return "Numéro requis", 400

    user = User.query.filter_by(phone=phone).first()
    if not user:
        return "Numéro non reconnu", 404

    # --- Authentification via mot de passe ---
    if password:
        if not check_password_hash(user.password_hash, password):
            return "Mot de passe invalide", 401

        session.clear()
        session["user_id"] = user.id
        session["user_authenticated"] = True

        if user.is_admin:
            session["admin_authenticated"] = True
            return redirect("/admin/advanced")
        else:
            resp = make_response(redirect("/setup_pin"))
            resp.set_cookie("standard_used", str(user.id), max_age=365*24*3600, httponly=True)
            return resp

    # --- Authentification via PIN ---
    if pin:
        if not user.pin_hash:
            return "Aucun PIN enregistré", 400
        if not check_password_hash(user.pin_hash, pin):
            return "PIN invalide", 401

        session.clear()
        session["user_id"] = user.id
        session["user_authenticated"] = True

        if user.is_admin:
            session["admin_authenticated"] = True
            return redirect("/admin/advanced")
        else:
            return redirect("/dashboard")

    return "Veuillez entrer un mot de passe ou un PIN", 400




from werkzeug.security import generate_password_hash

@app.route("/setup_pin", methods=["GET", "POST"])
def setup_pin():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    if request.method == "POST":
        pin = request.form.get("pin", "").strip()
        if len(pin) != 4:
            return "PIN invalide", 400

        user = User.query.get(user_id)
        user.pin_hash = generate_password_hash(pin)
        db.session.commit()

        # Création du cookie pour login futur avec PIN
        resp = make_response(redirect("/dashboard"))
        resp.set_cookie("user_id", str(user.id), max_age=365*24*3600, httponly=True, samesite="Lax")
        return resp

    # GET → afficher la page setup_pin.html
    return send_from_directory(TEMPLATES_DIR, "setup_pin.html")

# Simple login_pin page (we didn't receive template from toi; serve a minimal HTML inline)
# This avoids using Jinja and keeps everything in one file.
@app.route("/login_pin", methods=["GET", "POST"])
def login_pin():
    if request.method == "GET":
        return render_template("login_pin.html")

    # Récupération du user_id depuis le cookie
    user_id = request.cookies.get("user_id")
    if not user_id:
        return redirect("/login")  # pas de cookie → redirection vers login classique

    pin = request.form.get("pin", "").strip()
    if not pin or len(pin) != 4:
        return "PIN invalide", 400

    user = User.query.get(user_id)
    if not user or not user.pin_hash:
        return redirect("/login")

    if not check_password_hash(user.pin_hash, pin):
        return "PIN incorrect", 401

    # Création de session
    session.clear()
    session["user_authenticated"] = True
    session["user_id"] = user.id

    return redirect("/dashboard")
@app.route("/dashboard")
@login_required
def dashboard():
    # serve dashboard.html
    return send_from_directory(TEMPLATES_DIR, "dashboard.html")

@app.route("/depot")
@login_required
def depot():
    # serve depot.html
    return send_from_directory(TEMPLATES_DIR, "depot.html")

@app.route("/send")
@login_required
def send():
    # serve dashboard.html
    return send_from_directory(TEMPLATES_DIR, "send.html")

@app.route("/setting")
@login_required
def setting():
    # serve dashboard.html
    return send_from_directory(TEMPLATES_DIR, "set.html")

@app.route("/rewards")
@login_required
def rewards():
    # serve dashboard.html
    return send_from_directory(TEMPLATES_DIR, "reward.html")

@app.route("/withdraw")
@login_required
def withdraw():
    # serve dashboard.html
    return send_from_directory(TEMPLATES_DIR, "retrait.html")

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin_authenticated"):
        return redirect("/login")
    return send_from_directory(TEMPLATES_DIR, "admin_dashboard_advanced.html")





# API endpoint used by dashboard.js to fetch user info & transactions
@app.route("/api/user_info", methods=["GET"])
@login_required
def api_user_info():
    user = current_user()
    if not user:
        return jsonify({"error": "Utilisateur non connecté"}), 401

    # --- Devise de l'utilisateur ---
    country_currencies = {
        "Côte d'Ivoire": "XOF",
        "Mali": "XOF",
        "Burkina Faso": "XOF",
        "Sénégal": "XOF",
        "Guinee": "GNF",
        "Russie": "RUB",
        "Canada": "CAD",
        "Cameroun": "XAF",
        "Niger": "XOF",
        "Togo": "XOF",
        "Benin": "XOF",
    }

    currency = country_currencies.get(user.country, "XOF")

    # --- Transactions récentes ---
    deposits = Deposit.query.filter_by(user_id=user.id).order_by(Deposit.created_at.desc()).limit(10).all()
    transfers = Transfer.query.filter_by(user_id=user.id).order_by(Transfer.created_at.desc()).limit(10).all()
    withdraws = Withdraw.query.filter_by(user_id=user.id).order_by(Withdraw.created_at.desc()).limit(10).all()

    transactions = []

    # --- Dépôts ---
    for d in deposits:
        transactions.append({
            "type": "deposit",
            "amount": d.amount,
            "currency": d.currency,
            "status": d.status,
            "date": d.created_at.strftime("%Y-%m-%d %H:%M"),
            "description": d.note or "Dépôt effectué",
            "symbol": "+",
        })

    # --- Transferts ---
    for t in transfers:
        transactions.append({
            "type": "transfer",
            "amount": -t.amount,
            "currency": t.currency,
            "status": t.status,
            "date": t.created_at.strftime("%Y-%m-%d %H:%M"),
            "description": t.note or f"Transfert vers {t.recipient_phone}",
            "symbol": "−",
        })

    # --- Retraits ---
    for w in withdraws:
        transactions.append({
            "type": "withdraw",
            "amount": -w.net_amount,
            "currency": w.currency,
            "status": w.status,
            "date": w.created_at.strftime("%Y-%m-%d %H:%M"),
            "description": w.method or "Retrait bancaire",
            "symbol": "−",
        })

    # --- Tri global des transactions par date (descendante) ---
    transactions_sorted = sorted(transactions, key=lambda x: x["date"], reverse=True)

    # --- Solde net (roundé à 2 décimales) ---
    net_balance = round(user.balance, 2)

    # --- Résultat final ---
    return jsonify({
        "ok": True,
        "success": True,
        "user": {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "country": user.country,
            "currency": currency,
            "balance": net_balance,
        },
        "transactions": transactions_sorted[:10]
    })

@app.route("/api/depot_request", methods=["POST"])
def api_depot_request():
    data = request.get_json()
    phone = data.get("user_phone")
    amount = data.get("amount")
    method = data.get("payment_method")
    country = data.get("country")
    currency = data.get("currency")  # Devise envoyée depuis le frontend

    if not phone or not amount or not method or not currency:
        return jsonify({"error": "Champs manquants"}), 400

    user = User.query.filter_by(phone=phone).first()
    if not user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    depot = Deposit(
        user_id=user.id,
        amount=amount,
        method=method,
        currency=currency,  # ✅ Devise correcte
        country=country,
        status="pending"
    )
    db.session.add(depot)
    db.session.commit()

   # 🔔 NOTIFICATION TELEGRAM
    notification_data = {
        "user_phone": user.phone,
        "amount": amount,
        "currency": currency,
        "method": method,
        "country": country,
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "transaction_id": depot.id
    }
    
    notify_immediate("deposit", notification_data)
    
    return jsonify({"success": True})

#pour faire des retraits

@app.route("/api/withdraw_request", methods=["POST"])
def api_withdraw_request():
    data = request.get_json()
    phone = data.get("user_phone")
    amount = data.get("amount")
    method = data.get("withdraw_method")
    country = data.get("country")
    currency = data.get("currency")

    if not phone or not amount or not method:
        return jsonify({"error": "Champs manquants"}), 400

    user = User.query.filter_by(phone=phone).first()
    if not user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    fee_percent = get_withdrawal_fee(currency) 
    fee_amount = amount * fee_percent / 100
    net_amount = amount - fee_amount

    if amount > user.balance:  # comparer le montant total
       return jsonify({"error": "Solde insuffisant"}), 400

    user.balance -= amount  # déduire le montant total du solde


    withdraw = Withdraw(
        user_id=user.id,
        amount=amount,
        net_amount=net_amount,
        method=method,
        currency=currency,
        country=country,
        status="pending"
    )
    db.session.add(withdraw)
    db.session.commit()

     # 🔔 NOTIFICATION IMMÉDIATE
    notification_data = {
        "user_phone": user.phone,
        "amount": amount,
        "currency": currency,
        "net_amount": net_amount,
        "method": method,
        "country": country,
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "transaction_id": withdraw.id
    }
    
    notify_immediate("withdrawal", notification_data)
    print(f"🎯 NOUVEAU RETRAIT ENREGISTRÉ - ID: {withdraw.id}")

    return jsonify({"success": True, "net_amount": net_amount, "user_balance": user.balance, "currency": currency})


# Manual transfer request: recorded as pending (does not modify balance until approved manually)
@app.route("/api/transfer", methods=["POST"])
@login_required
def api_transfer():
    user = current_user()
    data = request.get_json() or {}

    recipient_phone = data.get("recipient_phone")
    recipient_country = data.get("recipient_country")
    note = data.get("note", "")
    payment_method = data.get("payment_method", "")  # Récupérer la méthode de paiement
    
    try:
        amount = float(data.get("amount"))
    except Exception:
        return jsonify({"error": "Montant invalide"}), 400

    if not recipient_phone or not recipient_country:
        return jsonify({"error": "Numéro du destinataire et pays requis"}), 400
    if amount <= 0:
        return jsonify({"error": "Montant doit être > 0"}), 400

    if user.balance < amount:
        return jsonify({"error": "Solde insuffisant"}), 400

    # --- Table des devises ---
    country_currencies = {
        "Côte d'Ivoire": "XOF",
        "Mali": "XOF",
        "Burkina Faso": "XOF",
        "Sénégal": "XOF",
        "Guinee": "GNF",
        "Russie": "RUB",
        "Canada": "CAD",
        "Cameroun": "XAF",
        "Niger": "XOF",
        "Togo": "XOF",
        "Benin": "XOF",
    }

    # --- Frais selon la devise de l'expéditeur ---
    fees_by_currency = {
        "XOF": 2.5,
        "GNF": 2.5,
        "RUB": 3.0,
        "CAD": 3.5,
        "XAF": 2.5,
    }

    # --- Taux de change simplifiés ---
    exchange_rates = {
        ("XOF", "XAF"): 0.9,
        ("XOF", "GNF"): 13.0,
        ("XOF", "RUB"): 0.133,
        ("XOF", "CAD"): 0.0022,
        ("XOF", "XOF"): 1.0,

        ("XAF", "XOF"): 1.1,
        ("XAF", "GNF"): 12.0,
        ("XAF", "RUB"): 0.129,
        ("XAF", "CAD"): 0.0020,
        ("XAF", "XAF"): 1.0,

        ("GNF", "XOF"): 0.077,
        ("GNF", "RUB"): 0.011,
        ("GNF", "CAD"): 0.00017,
        ("GNF", "GNF"): 1.0,

        ("RUB", "XOF"): 6.6,
        ("RUB", "GNF"): 90.0,
        ("RUB", "CAD"): 0.015,
        ("RUB", "RUB"): 1.0,

        ("CAD", "XOF"): 450.0,
        ("CAD", "GNF"): 6000.0,
        ("CAD", "RUB"): 67.0,
        ("CAD", "CAD"): 1.0,
    }

    # --- Déterminer les devises ---
    sender_currency = country_currencies.get(user.country, "XOF")
    recipient_currency = country_currencies.get(recipient_country, "XOF")

    # --- Calcul des frais et conversion ---
    fee_percent = get_transfer_fee(sender_currency)  # ✅ Utilise la base de données
    fee_amount = amount * fee_percent / 100
    conversion_rate = get_exchange_rate(sender_currency, recipient_currency)  # ✅ Utilise la base de données
    received_amount = (amount - fee_amount) * conversion_rate

    # --- Mise à jour du solde ---
    user.balance -= amount
    db.session.commit()

    # --- Construire la note avec la méthode de paiement ---
    # Si une méthode de paiement est fournie, l'ajouter à la note
    final_note = note
    if payment_method:
        final_note = f"Vers {recipient_country} - {payment_method}"
    else:
        final_note = f"Vers {recipient_country}"

    # --- Enregistrer le transfert ---
    transfer = Transfer(
        user_id=user.id,
        recipient_phone=recipient_phone,
        amount=received_amount,  # IMPORTANT: Enregistrer le montant reçu, pas le montant envoyé
        currency=recipient_currency,
        status="pending",
        note=final_note,  # Note incluant la méthode de paiement
    )
    db.session.add(transfer)
    db.session.commit()

    # 🔔 NOTIFICATION IMMÉDIATE - AJOUT DE LA MÉTHODE DE PAIEMENT
    notification_data = {
        "user_phone": user.phone,
        "recipient_phone": recipient_phone,
        "amount_sent": amount,
        "sender_currency": sender_currency,
        "amount_received": received_amount,
        "recipient_currency": recipient_currency,
        "fee": fee_amount,
        "method": payment_method,  # ✅ AJOUT DE LA MÉTHODE DANS LA NOTIFICATION
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "transaction_id": transfer.id
    }
    
    notify_immediate("transfer", notification_data)
    print(f"🎯 NOUVEAU TRANSFERT ENREGISTRÉ - ID: {transfer.id}")
    return jsonify({
        "ok": True,
        "transfer_id": transfer.id,
        "amount_sent": round(amount, 2),
        "fee": round(fee_amount, 2),
        "net_received": round(received_amount, 2),  # Montant qui sera affiché dans le modal
        "sender_balance": round(user.balance, 2),
        "sender_currency": sender_currency,
        "recipient_currency": recipient_currency,
        "payment_method": payment_method  # ✅ RETOURNER LA MÉTHODE AU FRONTEND
    }), 201

@app.route("/logout")
def logout():
    session.clear()
    resp = make_response(redirect("/login_pin"))
    # optional: remove cookie that indicates standard login used on device
    # resp.set_cookie("standard_used", "", expires=0)
    return resp




# Serve other static files (JS/CSS) from static folder automatically handled by Flask's static_folder
# But if you want to directly map template names to raw HTML from templates/ just like above,
# use send_from_directory(TEMPLATES_DIR, "<name>.html").

# -------------------- Helpful debug route (optional) --------------------
@app.route("/_whoami")
def whoami():
    user = current_user()
    if not user:
        return jsonify({"logged_in": False})
    return jsonify({
        "logged_in": True,
        "user_id": user.id,
        "phone": user.phone,
        "authenticated": session.get("user_authenticated", False),
        "session": dict(session)
    })
@app.route("/api/history", methods=["GET"])
@login_required
def api_history():
    user = current_user()
    if not user:
        return jsonify({"error": "Utilisateur non connecté"}), 401

    currency = get_currency_for_country(user.country)

    # Récupérer les dépôts, transferts et retraits
    deposits = Deposit.query.filter_by(user_id=user.id).order_by(Deposit.created_at.desc()).all()
    transfers = Transfer.query.filter_by(user_id=user.id).order_by(Transfer.created_at.desc()).all()
    withdraws = Withdraw.query.filter_by(user_id=user.id).order_by(Withdraw.created_at.desc()).all()

    txs = []

    for d in deposits:
        txs.append({
            "type": "deposit",
            "amount": d.amount,
            "currency": d.currency,
            "status": d.status,
            "date": d.created_at.strftime("%Y-%m-%d %H:%M"),
            "note": d.note or "Dépôt",
        })

    for t in transfers:
        txs.append({
            "type": "transfer",
            "amount": -t.amount,  # négatif car argent envoyé
            "currency": t.currency,
            "status": t.status,
            "date": t.created_at.strftime("%Y-%m-%d %H:%M"),
            "note": t.note or f"Transfert vers {t.recipient_phone}",
        })

    for w in withdraws:
        txs.append({
            "type": "withdraw",
            "amount": -w.amount,  # négatif car argent retiré
            "currency": w.currency,
            "status": w.status,
            "date": w.created_at.strftime("%Y-%m-%d %H:%M"),
            "note": w.note or "Retrait",
        })

    # Trier par date décroissante
    txs_sorted = sorted(txs, key=lambda x: x["date"], reverse=True)

    return jsonify(txs_sorted)


#recompense des utilisateur permanent

# ========================
# 🧩 REWARD SYSTEM ROUTES
# ========================

@app.route('/api/user_rewards')
def user_rewards():
    phone = request.args.get('phone')
    if not phone:
        return jsonify({'error': 'Numéro manquant'}), 400

    user = User.query.filter_by(phone=phone).first()
    if not user:
        return jsonify({'error': 'Utilisateur non trouvé'}), 404

    # On compte les transferts approuvés
    approved_transfers = Transfer.query.filter_by(user_id=user.id, status='approved').count()

    # 1 unité par 5 transferts approuvés
    cashback = (approved_transfers // 5) * 1
    currency = user.currency if hasattr(user, 'currency') else "EUR"

    return jsonify({
        'approved_transfers': approved_transfers,
        'cashback': cashback,
        'currency': currency
    })



@app.route('/api/withdraw_cashback', methods=['POST'])
def withdraw_cashback():
    data = request.get_json()
    phone = data.get('phone')

    if not phone:
        return jsonify({'error': 'Numéro requis'}), 400

    user = User.query.filter_by(phone=phone).first()
    if not user:
        return jsonify({'error': 'Utilisateur non trouvé'}), 404

    approved_transfers = Transfer.query.filter_by(user_id=user.id, status='approved').count()
    cashback = (approved_transfers // 5) * 1

    if cashback < 100:
        return jsonify({'error': 'Montant minimum pour retrait : 100'}), 400

    # Création du retrait
    withdrawal = CashbackWithdrawal(
        user_id=user.id,
        amount=100,
        currency=user.currency if hasattr(user, 'currency') else "EUR"
    )
    db.session.add(withdrawal)
    db.session.commit()

    # Envoi notification admin
    try:
        send_notification_email(
            subject="Demande de retrait de cashback",
            message=f"L'utilisateur {user.phone} a demandé un retrait de 100 {withdrawal.currency} de son cashback."
        )
    except Exception as e:
        print("Erreur email cashback:", e)

    return jsonify({'message': f'Retrait de 100 {withdrawal.currency} effectué avec succès.'})


#Dashboard admin

# -------------------- Admin Section --------------------
def admin_login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_authenticated"):
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated

@app.route("/admin/dashboard")
@admin_login_required
def admin_dashboard2():
    users = User.query.all()
    deposits = Deposit.query.all()
    transfers = Transfer.query.all()
    withdraws = Withdraw.query.all()
    return render_template("admin_dashboard.html", users=users, deposits=deposits,
                           transfers=transfers, withdraws=withdraws)

@app.route("/admin/approve_deposit/<int:deposit_id>", methods=["POST"])
@admin_login_required
def approve_deposit(deposit_id):
    dep = Deposit.query.get(deposit_id)
    if not dep:
        return jsonify({"error": "Dépôt introuvable"}), 404
    dep.status = "approved"
    dep.user.balance += dep.amount
    db.session.commit()
    return jsonify({"success": True})

@app.route("/admin/reject_deposit/<int:deposit_id>", methods=["POST"])
@admin_login_required
def reject_deposit(deposit_id):
    dep = Deposit.query.get(deposit_id)
    if not dep:
        return jsonify({"error": "Dépôt introuvable"}), 404
    dep.status = "rejected"
    db.session.commit()
    return jsonify({"success": True})

@app.route("/admin/approve_withdraw/<int:withdraw_id>", methods=["POST"])
@admin_login_required
def approve_withdraw(withdraw_id):
    wd = Withdraw.query.get(withdraw_id)
    if not wd:
        return jsonify({"error": "Retrait introuvable"}), 404
    wd.status = "approved"
    db.session.commit()
    return jsonify({"success": True})

@app.route("/admin/reject_withdraw/<int:withdraw_id>", methods=["POST"])
@admin_login_required
def reject_withdraw(withdraw_id):
    wd = Withdraw.query.get(withdraw_id)
    if not wd:
        return jsonify({"error": "Retrait introuvable"}), 404
    wd.status = "rejected"
    db.session.commit()
    return jsonify({"success": True})




# -------------------- Advanced Admin API Routes --------------------

@app.route("/admin/api/stats")
@admin_login_required
def admin_api_stats():
    """Statistiques globales pour le dashboard"""
    total_users = User.query.count()
    total_deposits = Deposit.query.count()
    total_withdrawals = Withdraw.query.count()
    total_transfers = Transfer.query.count()
    
    # Solde total de tous les utilisateurs
    total_balance = db.session.query(db.func.sum(User.balance)).scalar() or 0
    
    # Transactions en attente
    pending_deposits = Deposit.query.filter_by(status="pending").count()
    pending_withdrawals = Withdraw.query.filter_by(status="pending").count()
    pending_transfers = Transfer.query.filter_by(status="pending").count()
    
    # Statistiques des dernières 24h
    last_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    new_users_24h = User.query.filter(User.created_at >= last_24h).count()
    new_deposits_24h = Deposit.query.filter(Deposit.created_at >= last_24h).count()
    
    return jsonify({
        "total_users": total_users,
        "total_balance": round(total_balance, 2),
        "total_deposits": total_deposits,
        "total_withdrawals": total_withdrawals,
        "total_transfers": total_transfers,
        "pending_deposits": pending_deposits,
        "pending_withdrawals": pending_withdrawals,
        "pending_transfers": pending_transfers,
        "new_users_24h": new_users_24h,
        "new_deposits_24h": new_deposits_24h
    })

@app.route("/admin/api/pending_transactions")
@admin_login_required
def admin_api_pending_transactions():
    """Toutes les transactions en attente"""
    pending_deposits = Deposit.query.filter_by(status="pending").order_by(Deposit.created_at.desc()).all()
    pending_withdrawals = Withdraw.query.filter_by(status="pending").order_by(Withdraw.created_at.desc()).all()
    pending_transfers = Transfer.query.filter_by(status="pending").order_by(Transfer.created_at.desc()).all()
    
    deposits_data = []
    for dep in pending_deposits:
        deposits_data.append({
            "id": dep.id,
            "type": "deposit",
            "user_phone": dep.user.phone,
            "user_name": f"{dep.user.first_name} {dep.user.last_name}",
            "amount": dep.amount,
            "currency": dep.currency,
            "method": dep.method,
            "country": dep.country,
            "created_at": dep.created_at.strftime("%Y-%m-%d %H:%M"),
            "note": dep.note
        })
    
    withdrawals_data = []
    for wd in pending_withdrawals:
        withdrawals_data.append({
            "id": wd.id,
            "type": "withdrawal",
           "user_phone": wd.user.phone if wd.user else "N/A",
            "user_name": f"{wd.user.first_name} {wd.user.last_name}",
            "amount": wd.amount,
            "net_amount": wd.net_amount,
            "currency": wd.currency,
            "method": wd.method,
            "country": wd.country,
            "created_at": wd.created_at.strftime("%Y-%m-%d %H:%M"),
            "note": wd.note
        })
    
    transfers_data = []
    for tf in pending_transfers:
        transfers_data.append({
            "id": tf.id,
            "type": "transfer",
            "user_phone": tf.user.phone if tf.user else "N/A",
            "user_name": f"{tf.user.first_name} {tf.user.last_name}",
            "recipient_phone": tf.recipient_phone,
            "amount": tf.amount,
            "currency": tf.currency,
            "country": tf.user.country,
            "created_at": tf.created_at.strftime("%Y-%m-%d %H:%M"),
            "note": tf.note
        })
    
    return jsonify({
        "deposits": deposits_data,
        "withdrawals": withdrawals_data,
        "transfers": transfers_data
    })

@app.route("/admin/api/users")
@admin_login_required
def admin_api_users():
    """Liste de tous les utilisateurs avec pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    users = User.query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    users_data = []
    for user in users.items:
        users_data.append({
            "id": user.id,
            "phone": user.phone,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "country": user.country,
            "balance": user.balance,
            "created_at": user.created_at.strftime("%Y-%m-%d %H:%M"),
            "is_admin": user.is_admin
        })
    
    return jsonify({
        "users": users_data,
        "total_pages": users.pages,
        "current_page": users.page,
        "total_users": users.total
    })

@app.route("/admin/api/transactions")
@admin_login_required
def admin_api_transactions():
    """Toutes les transactions avec filtres"""
    transaction_type = request.args.get('type', 'all')
    status = request.args.get('status', 'all')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Base queries
    deposits_query = Deposit.query
    withdrawals_query = Withdraw.query
    transfers_query = Transfer.query
    
    # Filtres par statut
    if status != 'all':
        deposits_query = deposits_query.filter_by(status=status)
        withdrawals_query = withdrawals_query.filter_by(status=status)
        transfers_query = transfers_query.filter_by(status=status)
    
    all_transactions = []
    
    if transaction_type in ['all', 'deposits']:
        for dep in deposits_query.order_by(Deposit.created_at.desc()).all():
            all_transactions.append({
                "id": dep.id,
                "type": "deposit",
                "user_phone": dep.user.phone if dep.user else "N/A",
                "amount": dep.amount,
                "currency": dep.currency,
                "status": dep.status,
                "method": dep.method,
                "created_at": dep.created_at.strftime("%Y-%m-%d %H:%M"),
                "note": dep.note
            })
    
    if transaction_type in ['all', 'withdrawals']:
        for wd in withdrawals_query.order_by(Withdraw.created_at.desc()).all():
            all_transactions.append({
                "id": wd.id,
                "type": "withdrawal",
                "user_phone": wd.user.phone if wd.user else "N/A",
                "amount": wd.amount,
                "net_amount": wd.net_amount,
                "currency": wd.currency,
                "status": wd.status,
                "method": wd.method,
                "created_at": wd.created_at.strftime("%Y-%m-%d %H:%M"),
                "note": wd.note
            })
    
    if transaction_type in ['all', 'transfers']:
        for tf in transfers_query.order_by(Transfer.created_at.desc()).all():
            all_transactions.append({
                "id": tf.id,
                "type": "transfer",
                "user_phone": tf.user.phone if tf.user else "N/A",
                "recipient_phone": tf.recipient_phone,
                "amount": tf.amount,
                "currency": tf.currency,
                "status": tf.status,
                "created_at": tf.created_at.strftime("%Y-%m-%d %H:%M"),
                "note": tf.note
            })
    
    # Trier par date et paginer
    all_transactions.sort(key=lambda x: x['created_at'], reverse=True)
    start_idx = (page - 1) * per_page
    paginated_transactions = all_transactions[start_idx:start_idx + per_page]
    
    return jsonify({
        "transactions": paginated_transactions,
        "total_count": len(all_transactions),
        "current_page": page,
        "total_pages": (len(all_transactions) + per_page - 1) // per_page
    })

@app.route("/admin/api/user/<int:user_id>")
@admin_login_required
def admin_api_user_detail(user_id):
    """Détails d'un utilisateur spécifique"""
    user = User.query.get_or_404(user_id)
    
    # Transactions de l'utilisateur
    deposits = Deposit.query.filter_by(user_id=user_id).order_by(Deposit.created_at.desc()).limit(10).all()
    withdrawals = Withdraw.query.filter_by(user_id=user_id).order_by(Withdraw.created_at.desc()).limit(10).all()
    transfers = Transfer.query.filter_by(user_id=user_id).order_by(Transfer.created_at.desc()).limit(10).all()
    
    user_data = {
        "id": user.id,
        "phone": user.phone,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "country": user.country,
        "balance": user.balance,
        "created_at": user.created_at.strftime("%Y-%m-%d %H:%M"),
        "is_admin": user.is_admin,
        "deposits": [{
            "id": d.id,
            "amount": d.amount,
            "currency": d.currency,
            "status": d.status,
            "method": d.method,
            "created_at": d.created_at.strftime("%Y-%m-%d %H:%M")
        } for d in deposits],
        "withdrawals": [{
            "id": w.id,
            "amount": w.amount,
            "net_amount": w.net_amount,
            "currency": w.currency,
            "status": w.status,
            "method": w.method,
            "created_at": w.created_at.strftime("%Y-%m-%d %H:%M")
        } for w in withdrawals],
        "transfers": [{
            "id": t.id,
            "recipient_phone": t.recipient_phone,
            "amount": t.amount,
            "currency": t.currency,
            "status": t.status,
            "created_at": t.created_at.strftime("%Y-%m-%d %H:%M")
        } for t in transfers]
    }
    
    return jsonify(user_data)

@app.route("/admin/api/update_balance/<int:user_id>", methods=["POST"])
@admin_login_required
def admin_api_update_balance(user_id):
    """Mettre à jour manuellement le solde d'un utilisateur"""
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    new_balance = data.get('balance')
    if new_balance is None or new_balance < 0:
        return jsonify({"error": "Solde invalide"}), 400
    
    user.balance = new_balance
    db.session.commit()
    
    return jsonify({"success": True, "new_balance": user.balance})

# Route pour servir le dashboard admin avancé
@app.route("/admin/advanced")
@admin_login_required
def admin_advanced_dashboard():
    return send_from_directory(TEMPLATES_DIR, "admin_dashboard_advanced.html")

@app.route("/admin/approve_transfer/<int:transfer_id>", methods=["POST"])
@admin_login_required
def approve_transfer(transfer_id):
    transfer = Transfer.query.get(transfer_id)
    if not transfer:
        return jsonify({"error": "Transfert introuvable"}), 404
    transfer.status = "approved"
    db.session.commit()
    return jsonify({"success": True})

@app.route("/admin/reject_transfer/<int:transfer_id>", methods=["POST"])
@admin_login_required
def reject_transfer(transfer_id):
    transfer = Transfer.query.get(transfer_id)
    if not transfer:
        return jsonify({"error": "Transfert introuvable"}), 404
    transfer.status = "rejected"
    db.session.commit()
    return jsonify({"success": True})




# -------------------- WhatsApp Notification Service --------------------
import requests
import json
from datetime import datetime
import threading
from time import sleep

# -------------------- Advanced Notification System --------------------

# -------------------- Monitoring en Temps Réel (CORRIGÉ) --------------------

class TransactionMonitor:
    def __init__(self, app):
        self.app = app
        self.last_check = datetime.now(timezone.utc)  # ✅ Corrigé
        self.running = False
        
    def start_monitoring(self):
        """Démarre la surveillance en temps réel"""
        self.running = True
        monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        monitor_thread.start()
        print("🔍 Surveillance des transactions démarrée...")
    
    def _monitor_loop(self):
        """Boucle de surveillance principale avec contexte d'application"""
        while self.running:
            try:
                # ✅ Utiliser le contexte d'application
                with self.app.app_context():
                    self.check_pending_transactions()
                sleep(30)  # Vérifier toutes les 30 secondes
            except Exception as e:
                print(f"❌ Erreur surveillance: {e}")
                sleep(60)
    
    def check_pending_transactions(self):
        """Vérifie les nouvelles transactions en attente"""
        try:
            # Dépôts en attente
            pending_deposits = Deposit.query.filter_by(status="pending").all()
            for deposit in pending_deposits:
                # Vérifier si c'est une nouvelle transaction
                if deposit.created_at.replace(tzinfo=timezone.utc) > self.last_check:
                    self._notify_new_deposit(deposit)
            
            # Retraits en attente
            pending_withdrawals = Withdraw.query.filter_by(status="pending").all()
            for withdrawal in pending_withdrawals:
                if withdrawal.created_at.replace(tzinfo=timezone.utc) > self.last_check:
                    self._notify_new_withdrawal(withdrawal)
            
            # Transferts en attente
            pending_transfers = Transfer.query.filter_by(status="pending").all()
            for transfer in pending_transfers:
                if transfer.created_at.replace(tzinfo=timezone.utc) > self.last_check:
                    self._notify_new_transfer(transfer)
            
            # Mettre à jour le dernier check (✅ Corrigé)
            self.last_check = datetime.now(timezone.utc)
            
            print(f"🔍 Vérification terminée à {self.last_check.strftime('%H:%M:%S')}")
            
        except Exception as e:
            print(f"❌ Erreur vérification transactions: {e}")
    
    def _notify_new_deposit(self, deposit):
        user = User.query.get(deposit.user_id)
        data = {
            "user_phone": user.phone,
            "amount": deposit.amount,
            "currency": deposit.currency,
            "method": deposit.method,
            "country": deposit.country,
            "timestamp": deposit.created_at.strftime("%d/%m/%Y %H:%M"),
            "transaction_id": deposit.id
        }
        notify_immediate("deposit", data)
    
    def _notify_new_withdrawal(self, withdrawal):
        user = User.query.get(withdrawal.user_id)
        data = {
            "user_phone": user.phone,
            "amount": withdrawal.amount,
            "currency": withdrawal.currency,
            "net_amount": withdrawal.net_amount,
            "method": withdrawal.method,
            "country": withdrawal.country,
            "timestamp": withdrawal.created_at.strftime("%d/%m/%Y %H:%M"),
            "transaction_id": withdrawal.id
        }
        notify_immediate("withdrawal", data)
    
    def _notify_new_transfer(self, transfer):
        user = User.query.get(transfer.user_id)
        data = {
            "user_phone": user.phone,
            "recipient_phone": transfer.recipient_phone,
            "amount_sent": transfer.amount,
            "sender_currency": transfer.currency,
            "amount_received": transfer.amount,
            "recipient_currency": transfer.currency,
            "fee": 0,
            "timestamp": transfer.created_at.strftime("%d/%m/%Y %H:%M"),
            "transaction_id": transfer.id
        }
        notify_immediate("transfer", data)

# Initialisation du moniteur 
transaction_monitor = TransactionMonitor(app)  


#100% telegram notification 

import requests
import json
from datetime import datetime
import threading
from time import sleep

@app.route("/admin/force_telegram_setup")
@admin_login_required
def force_telegram_setup():
    """Force la configuration Telegram"""
    try:
        # Réinitialiser le chat ID
        advanced_notifier.telegram.chat_id = None
        if os.path.exists("telegram_chat_id.txt"):
            os.remove("telegram_chat_id.txt")
        
        # Relancer la configuration
        advanced_notifier.telegram.setup_bot()
        
        return jsonify({
            "status": "success",
            "message": "Configuration Telegram relancée. Envoyez un message à @EzukaTransfBot sur Telegram."
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# -------------------- TELEGRAM NOTIFICATION SYSTEM --------------------

class TelegramNotifier:
    def __init__(self):
        # Récupérer le token depuis les variables d'environnement
        self.bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not self.bot_token:
            raise ValueError("❌ TELEGRAM_BOT_TOKEN non configuré dans les variables d'environnement")
        
        self.chat_id = None
        self.setup_bot()
        
    def setup_bot(self):  # ✅ CORRIGER L'INDENTATION - même niveau que __init__
        """Configure le bot et récupère le chat ID"""
        try:
            print("🤖 Configuration du bot Telegram...")
            
            # Essayer de charger le chat ID sauvegardé d'abord
            if self.load_saved_chat_id():
                print("✅ Chat ID déjà configuré")
                return
                
            # Test de connexion avec le bot
            url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                bot_info = response.json()
                print(f"✅ Bot configuré: {bot_info['result']['first_name']}")
                print(f"   Username: @{bot_info['result']['username']}")
                
                # Récupérer les updates pour obtenir le chat ID
                self.get_chat_id()
            else:
                print(f"❌ Erreur configuration bot: {response.text}")
                
        except Exception as e:
            print(f"❌ Erreur setup bot: {e}")
    
    def get_chat_id(self):  # ✅ CORRIGER L'INDENTATION - même niveau que setup_bot
        """Récupère automatiquement le chat ID avec meilleure gestion"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data['result']:
                    # Prendre le dernier chat qui a envoyé un message
                    last_update = data['result'][-1]
                    self.chat_id = last_update['message']['chat']['id']
                    print(f"✅ Chat ID récupéré: {self.chat_id}")
                    
                    # Sauvegarder le chat ID pour éviter de le redemander
                    try:
                        with open("telegram_chat_id.txt", "w") as f:
                            f.write(str(self.chat_id))
                    except:
                        pass
                    
                    # Envoyer un message de bienvenue
                    welcome_msg = """
🔔 <b>Système Miniezuka Activé!</b>

✅ Votre système de notification Telegram est maintenant opérationnel!

Vous recevrez des alertes en temps réel pour :
💰 Nouveaux dépôts
💸 Demandes de retrait  
🔄 Transferts d'argent

<b>Prochaine étape :</b>
1. Allez sur http://127.0.0.1:5000/admin/test_telegram
2. Vous recevrez des notifications de test
                    """
                    self.send_message(welcome_msg)
                else:
                    print("❌ Aucun message reçu par le bot")
                    print("📝 INSTRUCTION : Ouvrez Telegram, cherchez @EzukaTransfBot et envoyez 'Start'")
            else:
                print(f"❌ Erreur API Telegram: {response.text}")
                
        except Exception as e:
            print(f"❌ Erreur récupération chat ID: {e}")
    
    def send_message(self, message):  # ✅ CORRIGER L'INDENTATION - même niveau que get_chat_id
        """Envoie un message via Telegram Bot"""
        try:
            if not self.chat_id:
                print("⚠️ Chat ID non configuré - tentative de récupération...")
                self.get_chat_id()
                if not self.chat_id:
                    return False
            
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
            
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                print("✅ Notification Telegram envoyée")
                return True
            else:
                print(f"❌ Erreur Telegram: {response.status_code} - {response.text}")
                # Tentative de récupération du chat ID en cas d'erreur
                if "chat not found" in response.text.lower():
                    self.get_chat_id()
                return False
                
        except Exception as e:
            print(f"❌ Erreur envoi Telegram: {e}")
            return False
    
    def load_saved_chat_id(self):  # ✅ CORRIGER L'INDENTATION - même niveau que send_message
        """Charge le chat ID sauvegardé"""
        try:
            if os.path.exists("telegram_chat_id.txt"):
                with open("telegram_chat_id.txt", "r") as f:
                    self.chat_id = int(f.read().strip())
                    print(f"✅ Chat ID chargé depuis sauvegarde: {self.chat_id}")
                    return True
        except:
            pass
        return False
# -------------------- COMPLETE NOTIFICATION SYSTEM --------------------

class AdvancedNotifier:
    def __init__(self):
        self.telegram = TelegramNotifier()
        self.console = ConsoleNotifier()
        self.file_logger = FileLogger()
        self.last_notification = {}
        
    def notify_transaction(self, transaction_type, data):
        """Notifie une transaction sur tous les canaux"""
        try:
            user_phone = data['user_phone']
            transaction_key = f"{transaction_type}_{user_phone}"
            
            # Anti-spam (1 notification par minute par utilisateur)
            now = datetime.now(timezone.utc)
            if transaction_key in self.last_notification:
                time_diff = (now - self.last_notification[transaction_key]).total_seconds()
                if time_diff < 60:
                    print(f"⏳ Notification ignorée (anti-spam) pour {user_phone}")
                    return
            
            self.last_notification[transaction_key] = now
            
            # Formater les messages
            telegram_message = self._format_telegram_message(transaction_type, data)
            
            print(f"🎯 Notification: {transaction_type.upper()} - {user_phone}")
            
            # 1. Notification console (toujours active)
            self.console.notify(transaction_type, data)
            
            # 2. Log fichier (toujours actif)
            self.file_logger.log_transaction(transaction_type, data)
            
            # 3. Telegram
            telegram_success = self.telegram.send_message(telegram_message)
            
            # 4. Affichage statut
            print(f"   📊 Statut - Console: ✅, Fichier: ✅, Telegram: {'✅' if telegram_success else '❌'}")
            
        except Exception as e:
            print(f"❌ Erreur système notification: {e}")
    
    def _format_telegram_message(self, transaction_type, data):
        """Formate le message pour Telegram avec un beau format"""
        emojis = {
            "deposit": "💰",
            "withdrawal": "💸", 
            "transfer": "🔄"
        }
        
        emoji = emojis.get(transaction_type, "📢")
        is_urgent = data.get('amount', 0) > 50000
        
        if is_urgent:
            message = f"🚨 <b>TRANSACTION URGENTE</b> 🚨\n\n"
        else:
            message = f"{emoji} <b>NOUVELLE TRANSACTION</b> {emoji}\n\n"
        
        # Informations générales
        message += f"<b>Type:</b> {transaction_type.upper()}\n"
        message += f"<b>Utilisateur:</b> {data['user_phone']}\n"
        message += f"<b>Date:</b> {data['timestamp']}\n"
        message += f"<b>ID:</b> #{data['transaction_id']}\n\n"
        
        # Détails spécifiques
        if transaction_type == "deposit":
            message += f"<b>Montant:</b> {data['amount']} {data['currency']}\n"
            message += f"<b>Méthode:</b> {data['method']}\n"
            message += f"<b>Pays:</b> {data['country']}\n"
            message += f"\n📥 <b>Action:</b> Vérifier et approuver le dépôt"
        
        elif transaction_type == "withdrawal":
            message += f"<b>Montant demandé:</b> {data['amount']} {data['currency']}\n"
            message += f"<b>Net après frais:</b> {data['net_amount']} {data['currency']}\n"
            message += f"<b>Méthode:</b> {data['method']}\n"
            message += f"\n📤 <b>Action:</b> Effectuer le paiement"
        
        elif transaction_type == "transfer":
            message += f"<b>De:</b> {data['user_phone']}\n"
            message += f"<b>Vers:</b> {data['recipient_phone']}\n"
            message += f"<b>Montant envoyé:</b> {data['amount_sent']} {data['sender_currency']}\n"
            message += f"<b>Montant reçu:</b> {data['amount_received']} {data['recipient_currency']}\n"
            message += f"<b>Méthode:</b> {data['method']}\n"

            message += f"<b>Frais:</b> {data['fee']} {data['sender_currency']}\n"
            message += f"\n🔄 <b>Action:</b> Vérifier le transfert"
        
        if is_urgent:
            message += f"\n\n⚠️ <b>TRANSACTION IMPORTANTE - TRAITEMENT IMMÉDIAT REQUIS!</b> ⚠️"
        
        # Bouton d'action
        message += f"\n\n🔗 <a href='http://127.0.0.1:5000/admin/advanced'>📊 ACCÉDER AU TABLEAU DE BORD</a>"
        
        return message

# -------------------- CONSOLE NOTIFIER --------------------

class ConsoleNotifier:
    def __init__(self):
        self.colors = {
            'deposit': '💰',
            'withdrawal': '💸', 
            'transfer': '🔄',
            'urgent': '🚨'
        }
    
    def notify(self, transaction_type, data):
        """Notification colorée dans la console"""
        try:
            emoji = self.colors.get(transaction_type, '📢')
            is_urgent = data.get('amount', 0) > 50000
            
            print("\n" + "="*70)
            if is_urgent:
                print(f"🚨🚨🚨  TRANSACTION URGENTE  🚨🚨🚨")
                print("="*70)
            else:
                print(f"{emoji}  NOUVELLE TRANSACTION  {emoji}")
                print("="*70)
            
            print(f"📋 Type: {transaction_type.upper()}")
            print(f"👤 Utilisateur: {data['user_phone']}")
            
            if transaction_type == "deposit":
                print(f"💳 Montant: {data['amount']} {data['currency']}")
                print(f"📱 Méthode: {data['method']}")
                print(f"🌍 Pays: {data['country']}")
                print(f"📥 Action: Vérifier et approuver le dépôt")
            
            elif transaction_type == "withdrawal":
                print(f"💸 Montant demandé: {data['amount']} {data['currency']}")
                print(f"📤 Net après frais: {data['net_amount']} {data['currency']}")
                print(f"📱 Méthode: {data['method']}")
                print(f"📤 Action: Effectuer le paiement")
            
            elif transaction_type == "transfer":
                print(f"📞 De: {data['user_phone']}")
                print(f"📞 Vers: {data['recipient_phone']}")
                print(f"💳 Montant envoyé: {data['amount_sent']} {data['sender_currency']}")
                print(f"💰 Montant reçu: {data['amount_received']} {data['recipient_currency']}")
                print(f"📊 Frais: {data['fee']} {data['sender_currency']}")
                print(f"📱 Méthode: {data['method']}")
                print(f"🔄 Action: Vérifier le transfert")
            
            print(f"🆔 ID: #{data['transaction_id']}")
            print(f"🕒 Heure: {data['timestamp']}")
            
            if is_urgent:
                print(f"\n🚨🚨 ATTENTION: TRANSACTION IMPORTANTE - TRAITEMENT IMMÉDIAT! 🚨🚨")
            
            print("="*70 + "\n")
            
            # Bip sonore d'alerte
            self._play_alert_sound(is_urgent)
                
        except Exception as e:
            print(f"❌ Erreur notification console: {e}")
    
    def _play_alert_sound(self, is_urgent):
        """Joue un son d'alerte"""
        try:
            import winsound
            if is_urgent:
                # Bip urgent (plus long et répété)
                for _ in range(3):
                    winsound.Beep(1000, 300)
                    sleep(0.1)
            else:
                # Bip normal
                winsound.Beep(800, 200)
        except:
            pass  # Ignorer si winsound n'est pas disponible

# -------------------- FILE LOGGER --------------------

class FileLogger:
    def __init__(self):
        self.log_file = "transactions.log"
        self.alert_file = "urgent_transactions.log"
        
    def log_transaction(self, transaction_type, data):
        """Log dans un fichier avec horodatage"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            log_entry = {
                "timestamp": timestamp,
                "type": transaction_type,
                "data": data
            }
            
            # Écrire dans le fichier principal
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            
            # Écrire dans le fichier d'alertes urgentes
            if data.get('amount', 0) > 50000:
                alert_msg = f"[URGENT] {timestamp} - {transaction_type.upper()} - {data['user_phone']} - {data['amount']} {data.get('currency', '')}\n"
                with open(self.alert_file, "a", encoding="utf-8") as f:
                    f.write(alert_msg)
            
            print(f"📝 Transaction loggée dans {self.log_file}")
            
        except Exception as e:
            print(f"❌ Erreur log fichier: {e}")

# -------------------- INITIALISATION --------------------

# Créer l'instance principale
advanced_notifier = AdvancedNotifier()

# Fonction simple pour les notifications
def notify_immediate(transaction_type, data):
    """Fonction simple à appeler dans vos routes"""
    import threading
    thread = threading.Thread(
        target=advanced_notifier.notify_transaction, 
        args=(transaction_type, data),
        daemon=True
    )
    thread.start()


#test

@app.route("/admin/test_telegram")
@admin_login_required
def test_telegram():
    """Test complet du système Telegram"""
    
    test_data = {
        "user_phone": "+2250700000000",
        "amount": 75000,  # Montant urgent
        "currency": "XOF", 
        "method": "Wave",
        "country": "Côte d'Ivoire",
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "transaction_id": 999
    }
    
    print("🧪 Test des notifications...")
    
    # Test dépôt urgent
    notify_immediate("deposit", test_data)
    
    # Test retrait
    test_data.update({
        "amount": 25000,
        "net_amount": 24625,
        "method": "Orange Money"
    })
    notify_immediate("withdrawal", test_data)
    
    # Test transfert
    test_data.update({
        "recipient_phone": "+2250700000001",
        "amount_sent": 10000,
        "sender_currency": "XOF",
        "amount_received": 9750,
        "recipient_currency": "XOF", 
        "fee": 250
    })
    notify_immediate("transfer", test_data)
    
    return jsonify({
        "status": "success", 
        "message": "Tests de notification envoyés à Telegram"
    })



# -------------------- Fees & Exchange Management API --------------------

@app.route("/admin/api/currency_configs")
@admin_login_required
def admin_api_currency_configs():
    """Liste toutes les configurations de devises"""
    configs = CurrencyConfig.query.order_by(CurrencyConfig.currency_code).all()
    
    configs_data = []
    for config in configs:
        configs_data.append({
            "id": config.id,
            "currency_code": config.currency_code,
            "currency_name": config.currency_name,
            "transfer_fee_percent": config.transfer_fee_percent,
            "withdrawal_fee_percent": config.withdrawal_fee_percent,
            "is_active": config.is_active,
            "updated_at": config.updated_at.strftime("%Y-%m-%d %H:%M")
        })
    
    return jsonify({"configs": configs_data})

@app.route("/admin/api/exchange_rates")
@admin_login_required
def admin_api_exchange_rates():
    """Liste tous les taux de change"""
    rates = ExchangeRate.query.order_by(ExchangeRate.from_currency, ExchangeRate.to_currency).all()
    
    rates_data = []
    for rate in rates:
        rates_data.append({
            "id": rate.id,
            "from_currency": rate.from_currency,
            "to_currency": rate.to_currency,
            "rate": rate.rate,
            "is_active": rate.is_active,
            "updated_at": rate.updated_at.strftime("%Y-%m-%d %H:%M")
        })
    
    return jsonify({"rates": rates_data})

@app.route("/admin/api/country_currencies")
@admin_login_required
def admin_api_country_currencies():
    """Liste toutes les associations pays-devise"""
    countries = CountryCurrency.query.order_by(CountryCurrency.country_name).all()
    
    countries_data = []
    for country in countries:
        countries_data.append({
            "id": country.id,
            "country_name": country.country_name,
            "country_code": country.country_code,
            "currency_code": country.currency_code,
            "is_active": country.is_active
        })
    
    return jsonify({"countries": countries_data})

@app.route("/admin/api/update_currency_config", methods=["POST"])
@admin_login_required
def admin_api_update_currency_config():
    """Met à jour une configuration de devise"""
    data = request.get_json()
    
    config = CurrencyConfig.query.get(data.get('id'))
    if not config:
        return jsonify({"error": "Configuration non trouvée"}), 404
    
    config.transfer_fee_percent = data.get('transfer_fee_percent', config.transfer_fee_percent)
    config.withdrawal_fee_percent = data.get('withdrawal_fee_percent', config.withdrawal_fee_percent)
    config.is_active = data.get('is_active', config.is_active)
    config.updated_at = datetime.now(timezone.utc)
    
    db.session.commit()
    
    return jsonify({"success": True, "message": "Configuration mise à jour"})

@app.route("/admin/api/update_exchange_rate", methods=["POST"])
@admin_login_required
def admin_api_update_exchange_rate():
    """Met à jour un taux de change"""
    data = request.get_json()
    
    rate = ExchangeRate.query.get(data.get('id'))
    if not rate:
        return jsonify({"error": "Taux de change non trouvé"}), 404
    
    rate.rate = data.get('rate', rate.rate)
    rate.is_active = data.get('is_active', rate.is_active)
    rate.updated_at = datetime.now(timezone.utc)
    
    db.session.commit()
    
    return jsonify({"success": True, "message": "Taux de change mis à jour"})

@app.route("/admin/api/update_country_currency", methods=["POST"])
@admin_login_required
def admin_api_update_country_currency():
    """Met à jour une association pays-devise"""
    data = request.get_json()
    
    country = CountryCurrency.query.get(data.get('id'))
    if not country:
        return jsonify({"error": "Pays non trouvé"}), 404
    
    country.currency_code = data.get('currency_code', country.currency_code)
    country.is_active = data.get('is_active', country.is_active)
    
    db.session.commit()
    
    return jsonify({"success": True, "message": "Pays mis à jour"})

@app.route("/admin/api/add_exchange_rate", methods=["POST"])
@admin_login_required
def admin_api_add_exchange_rate():
    """Ajoute un nouveau taux de change"""
    data = request.get_json()
    
    # Vérifier si la paire existe déjà
    existing = ExchangeRate.query.filter_by(
        from_currency=data.get('from_currency'),
        to_currency=data.get('to_currency')
    ).first()
    
    if existing:
        return jsonify({"error": "Cette paire de devises existe déjà"}), 400
    
    new_rate = ExchangeRate(
        from_currency=data.get('from_currency'),
        to_currency=data.get('to_currency'),
        rate=data.get('rate', 1.0)
    )
    
    db.session.add(new_rate)
    db.session.commit()
    
    return jsonify({"success": True, "message": "Taux de change ajouté"})

@app.route("/admin/api/add_currency_config", methods=["POST"])
@admin_login_required
def admin_api_add_currency_config():
    """Ajoute une nouvelle configuration de devise"""
    data = request.get_json()
    
    # Vérifier si la devise existe déjà
    existing = CurrencyConfig.query.filter_by(currency_code=data.get('currency_code')).first()
    
    if existing:
        return jsonify({"error": "Cette devise existe déjà"}), 400
    
    new_config = CurrencyConfig(
        currency_code=data.get('currency_code'),
        currency_name=data.get('currency_name'),
        transfer_fee_percent=data.get('transfer_fee_percent', 2.5),
        withdrawal_fee_percent=data.get('withdrawal_fee_percent', 1.5)
    )
    
    db.session.add(new_config)
    db.session.commit()
    
    return jsonify({"success": True, "message": "Configuration de devise ajoutée"})

@app.route("/admin/fees-management")
@admin_login_required
def admin_fees_management():
    """Dashboard de gestion des frais et taux de change"""
    return send_from_directory(TEMPLATES_DIR, "fees_dashboard.html")


# -------------------- Run --------------------

# -------------------- Initialisation automatique --------------------
with app.app_context():
    create_admin()
    init_default_fees_and_rates()
    print("✅ Application initialisée avec succès.")

# ✅ Exposition pour Gunicorn
# (Très important : Gunicorn cherche cette variable globale)
application = app


