from flask import Flask, render_template, request, redirect, url_for, flash, session
import json
from pathlib import Path
import functools
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

DATA_DIR = Path("data")
STATS_FILE = DATA_DIR / "stats.json"
CONFIG_FILE = DATA_DIR / "config.json"
PHRASES_FILE = DATA_DIR / "phrases.json"
MISSIONS_FILE = DATA_DIR / "missions.json"

ADMIN_USER = "admin"
ADMIN_PASS = "walidcrooks21"   # ¡Cámbiala por seguridad!

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if "user" not in session:
            flash("Por favor inicia sesión", "warning")
            return redirect(url_for("login"))
        return view(**kwargs)
    return wrapped_view

def load_json(path, default=None):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"Error cargando {path}: {e}")
    return default or {}

def save_json(path, data):
    try:
        path.parent.mkdir(exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error guardando {path}: {e}")

# ====================== RUTAS ======================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("username") == ADMIN_USER and request.form.get("password") == ADMIN_PASS:
            session["user"] = ADMIN_USER
            flash("✅ Login correcto", "success")
            return redirect(url_for("dashboard"))
        flash("❌ Usuario o contraseña incorrecta", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Sesión cerrada", "info")
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    stats = load_json(STATS_FILE, {})
    config = load_json(CONFIG_FILE, {})
    users = sorted(stats.values(), key=lambda x: x.get("xp", 0), reverse=True)
    
    return render_template("dashboard.html",
                         users=users,
                         total_users=len(users),
                         total_xp=sum(u.get("xp", 0) for u in users),
                         daily_goal=config.get("daily_goal", 50),
                         weekly_goal=config.get("weekly_goal", 300))


@app.route("/ranking")
@login_required
def ranking():
    stats = load_json(STATS_FILE, {})
    users = sorted(stats.values(), key=lambda x: x.get("xp", 0), reverse=True)
    return render_template("ranking.html", users=users)


@app.route("/equipos")
@login_required
def equipos():
    return render_template("equipos.html")


@app.route("/objetivos")
@login_required
def objetivos():
    return render_template("objetivos.html")


@app.route("/misiones", methods=["GET", "POST"])
@login_required
def misiones():
    missions = load_json(MISSIONS_FILE, [])
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            try:
                new_mission = {
                    "name": request.form.get("name", "").strip(),
                    "type": request.form.get("type", "daily"),
                    "goal": int(request.form.get("goal", 1)),
                    "reward": int(request.form.get("reward", 10))
                }
                if new_mission["name"]:
                    missions.append(new_mission)
                    save_json(MISSIONS_FILE, missions)
                    flash("Misión añadida", "success")
            except:
                flash("Error en los datos de la misión", "danger")
        elif action == "delete":
            try:
                index = int(request.form.get("index"))
                if 0 <= index < len(missions):
                    missions.pop(index)
                    save_json(MISSIONS_FILE, missions)
                    flash("Misión eliminada", "danger")
            except:
                flash("Error al eliminar", "danger")
        return redirect(url_for("misiones"))
    return render_template("misiones.html", missions=missions)


@app.route("/frases", methods=["GET", "POST"])
@login_required
def frases():
    data = load_json(PHRASES_FILE, {"motivation": []})
    if isinstance(data, list):
        data = {"motivation": data}

    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            phrase = request.form.get("phrase", "").strip()
            if phrase:
                data["motivation"].append(phrase)
                save_json(PHRASES_FILE, data)
                flash("Frase añadida", "success")
        elif action == "delete":
            try:
                index = int(request.form.get("index"))
                if 0 <= index < len(data.get("motivation", [])):
                    data["motivation"].pop(index)
                    save_json(PHRASES_FILE, data)
                    flash("Frase eliminada", "danger")
            except:
                flash("Error al eliminar frase", "danger")
        return redirect(url_for("frases"))
    return render_template("frases.html", phrases=data.get("motivation", []))


@app.route("/config", methods=["GET", "POST"])
@login_required
def config():
    config = load_json(CONFIG_FILE, {"xp_light":1, "xp_bell":2, "daily_goal":50, "weekly_goal":300})
    if request.method == "POST":
        try:
            config.update({
                "xp_light": int(request.form.get("xp_light", 1)),
                "xp_bell": int(request.form.get("xp_bell", 2)),
                "daily_goal": int(request.form.get("daily_goal", 50)),
                "weekly_goal": int(request.form.get("weekly_goal", 300))
            })
            save_json(CONFIG_FILE, config)
            flash("Configuración guardada", "success")
            return redirect(url_for("config"))
        except:
            flash("Error: usa solo números", "danger")
    return render_template("config.html", config=config)


if __name__ == "__main__":
    DATA_DIR.mkdir(exist_ok=True)
    
    print("\n" + "="*70)
    print("🚀 CONTRATOBOT DASHBOARD INICIADO")
    print("="*70)

    # Iniciar ngrok para tener HTTPS público
    try:
        from pyngrok import ngrok
        # Cerrar túneles anteriores
        ngrok.kill()
        
        # Crear túnel HTTPS
        public_url = ngrok.connect(5000, "http")
        print(f"🌐 DASHBOARD CON HTTPS:")
        print(f"🔗 {public_url}")
        print("="*70)
        print("⚠️  Usa este enlace (es público)")
        print("Presiona Ctrl + C para detener")
        print("="*70)
        
    except Exception as e:
        print(f"⚠️ No se pudo iniciar ngrok: {e}")
        print("Ejecutando en modo local normal...")
        public_url = None

    # Iniciar Flask
    try:
        app.run(host="0.0.0.0", port=5000, debug=False)
    finally:
        # Cerrar ngrok al detener el servidor
        if 'ngrok' in globals():
            ngrok.kill()
