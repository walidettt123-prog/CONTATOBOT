import json
import random
from pathlib import Path
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ========================= CONFIG =========================
TOKEN = ""  # ← Cambia esto

DATA_DIR = Path("data")
STATS_FILE = DATA_DIR / "stats.json"
CONFIG_FILE = DATA_DIR / "config.json"
PHRASES_FILE = DATA_DIR / "phrases.json"
MISSIONS_FILE = DATA_DIR / "missions.json"
TEAMS_FILE = DATA_DIR / "teams.json"
HISTORY_FILE = DATA_DIR / "history.json"

# ========================= HELPERS =========================
def load_json(path, default=None):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"Error cargando {path}: {e}")
    return default or {} if isinstance(default, dict) else default or []


def save_json(path, data):
    path.parent.mkdir(exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def save_event(text):
    history = load_json(HISTORY_FILE, [])
    history.insert(0, text)
    save_json(HISTORY_FILE, history[:100])


# ========================= USER =========================
def get_user(stats, user_id, username):
    if user_id not in stats:
        teams = load_json(TEAMS_FILE, {})
        team = teams.get(username, "Sin equipo")
        stats[user_id] = {
            "name": username,
            "xp": 0,
            "lights": 0,
            "bells": 0,
            "team": team,
            "missions_completed": []
        }
    return stats[user_id]


# ========================= RANKING =========================
def get_ranking(stats):
    return sorted(stats.values(), key=lambda x: x.get("xp", 0), reverse=True)


# ========================= MISIONES =========================
def check_missions(user):
    missions = load_json(MISSIONS_FILE, [])
    rewards = []
    for mission in missions:
        mission_name = mission.get("name")
        if mission_name in user.get("missions_completed", []):
            continue

        mission_type = mission.get("type")
        goal = mission.get("goal", 0)
        completed = False

        if mission_type == "daily" or mission_type == "light":
            completed = user.get("lights", 0) >= goal
        elif mission_type == "weekly" or mission_type == "bell":
            completed = user.get("bells", 0) >= goal

        if completed:
            reward = mission.get("reward", 0)
            user["xp"] = user.get("xp", 0) + reward
            user.setdefault("missions_completed", []).append(mission_name)
            rewards.append((mission_name, reward))
            save_event(f"🎯 {user['name']} completó '{mission_name}' (+{reward} XP)")
    return rewards


# ========================= COMANDOS =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚡ <b>ContratoBot Activo</b>\n\n"
        "Comandos disponibles:\n"
        "/perfil - Ver tu progreso\n"
        "/ranking - Top usuarios\n"
        "/equipos - Guerra de equipos\n"
        "/misiones - Ver misiones activas\n"
        "/help - Ayuda",
        parse_mode="HTML"
    )


async def perfil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = load_json(STATS_FILE, {})
    user_id = str(update.effective_user.id)
    user = get_user(stats, user_id, update.effective_user.first_name)

    text = (
        f"👤 <b>{user['name']}</b>\n\n"
        f"🏆 XP: <b>{user['xp']}</b>\n"
        f"👥 Equipo: {user['team']}\n"
        f"💡 Luces: {user['lights']}\n"
        f"🔔 Campanas: {user['bells']}\n"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = load_json(STATS_FILE, {})
    ranking_data = get_ranking(stats)
    text = "🏆 <b>RANKING GENERAL</b>\n\n"
    medals = ["🥇", "🥈", "🥉"]

    for i, user in enumerate(ranking_data[:15]):
        medal = medals[i] if i < 3 else f"{i+1}."
        text += f"{medal} {user['name']} — <b>{user['xp']}</b> XP\n"

    await update.message.reply_text(text, parse_mode="HTML")


async def equipos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = load_json(STATS_FILE, {})
    teams = {}
    for user in stats.values():
        team = user.get("team", "Sin equipo")
        teams[team] = teams.get(team, 0) + user.get("xp", 0)

    ranking_teams = sorted(teams.items(), key=lambda x: x[1], reverse=True)

    text = "⚔️ <b>GUERRA DE EQUIPOS</b>\n\n"
    for pos, (team, xp) in enumerate(ranking_teams, 1):
        text += f"{pos}. {team} → <b>{xp}</b> XP\n"

    await update.message.reply_text(text, parse_mode="HTML")


async def misiones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    missions = load_json(MISSIONS_FILE, [])
    if not missions:
        await update.message.reply_text("No hay misiones configuradas.")
        return

    text = "🎯 <b>MISIONES ACTIVAS</b>\n\n"
    for m in missions:
        text += f"• <b>{m['name']}</b>\n"
        text += f"   Meta: {m['goal']} {m['type']}\n"
        text += f"   Recompensa: +{m['reward']} XP\n\n"

    await update.message.reply_text(text, parse_mode="HTML")


# ========================= MANEJO DE MENSAJES =========================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    lights = text.count("💡")
    bells = text.count("🔔")

    if lights == 0 and bells == 0:
        return

    config = load_json(CONFIG_FILE, {})
    xp_light = config.get("xp_light", 1)
    xp_bell = config.get("xp_bell", 2)

    xp = lights * xp_light + bells * xp_bell

    stats = load_json(STATS_FILE, {})
    user_id = str(update.effective_user.id)
    username = update.effective_user.first_name

    user = get_user(stats, user_id, username)

    user["xp"] = user.get("xp", 0) + xp
    user["lights"] = user.get("lights", 0) + lights
    user["bells"] = user.get("bells", 0) + bells

    save_event(f"⚡ {user['name']} ganó {xp} XP")

    rewards = check_missions(user)

    save_json(STATS_FILE, stats)

    reply = f"⚡ +{xp} XP\n🏆 Total: <b>{user['xp']}</b> XP"

    for mission_name, reward in rewards:
        reply += f"\n\n🎉 <b>MISIÓN COMPLETADA!</b>\n{mission_name}\n+{reward} XP"

    # Frase motivacional aleatoria
    phrases = load_json(PHRASES_FILE, {"motivation": []})
    motivation = phrases.get("motivation", [])
    if motivation and random.randint(1, 3) == 1:
        reply += f"\n\n💬 {random.choice(motivation)}"

    await update.message.reply_text(reply, parse_mode="HTML")


# ========================= MAIN =========================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("perfil", perfil))
    app.add_handler(CommandHandler("ranking", ranking))
    app.add_handler(CommandHandler("equipos", equipos))
    app.add_handler(CommandHandler("misiones", misiones))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 CONTRATOBOT V2 INICIADO - Dashboard conectado")
    app.run_polling()


if __name__ == "__main__":
    DATA_DIR.mkdir(exist_ok=True)
    main()
