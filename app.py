
from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import date, timedelta

app = Flask(__name__)
DATABASE = "fitness.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            sex TEXT NOT NULL,
            height REAL NOT NULL,
            weight REAL NOT NULL,
            goal TEXT NOT NULL,
            activity TEXT NOT NULL,
            diet TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_date TEXT NOT NULL,
            food TEXT DEFAULT '',
            calories INTEGER DEFAULT 0,
            workout TEXT DEFAULT '',
            workout_minutes INTEGER DEFAULT 0,
            water REAL DEFAULT 0,
            weight REAL DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


def get_recommendations(profile):
    height_m = profile["height"] / 100
    bmi = profile["weight"] / (height_m * height_m)

    if profile["sex"].lower() == "male":
        bmr = (10 * profile["weight"]) + (6.25 * profile["height"]) - (5 * profile["age"]) + 5
    else:
        bmr = (10 * profile["weight"]) + (6.25 * profile["height"]) - (5 * profile["age"]) - 161

    activity_factors = {
        "low": 1.2,
        "moderate": 1.55,
        "high": 1.725
    }

    calories = round(bmr * activity_factors.get(profile["activity"], 1.2))

    if profile["goal"] == "lose":
        calories -= 300
    elif profile["goal"] == "gain":
        calories += 300

    if profile["diet"] == "vegetarian":
        meals = [
            "Breakfast: Oats, milk and fruit",
            "Lunch: Rice or roti, dal and vegetables",
            "Snack: Fruit or a handful of nuts",
            "Dinner: Paneer or beans with roti"
        ]
    elif profile["diet"] == "vegan":
        meals = [
            "Breakfast: Oats with soy milk and fruit",
            "Lunch: Rice, dal and vegetables",
            "Snack: Fruit and roasted chickpeas",
            "Dinner: Tofu, beans and roti"
        ]
    else:
        meals = [
            "Breakfast: Eggs and whole-grain toast",
            "Lunch: Rice or roti with chicken or dal",
            "Snack: Fruit or yogurt",
            "Dinner: Protein source, vegetables and roti"
        ]

    workouts = {
        "lose": ["Brisk walking: 25–30 minutes", "Strength training: 15 minutes"],
        "maintain": ["Walking or cycling: 20–30 minutes", "Full-body strength training"],
        "gain": ["Strength training: 30 minutes", "Recovery and adequate sleep"]
    }

    return {
        "bmi": round(bmi, 1),
        "calories": max(1200, calories),
        "water": round(max(1.5, profile["weight"] * 0.033), 1),
        "meals": meals,
        "workouts": workouts.get(profile["goal"], workouts["maintain"])
    }


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/profile", methods=["GET", "POST"])
def profile_api():
    conn = get_db()

    if request.method == "POST":
        data = request.get_json(silent=True) or {}

        try:
            name = str(data["name"]).strip()
            age = int(data["age"])
            sex = str(data["sex"]).lower()
            height = float(data["height"])
            weight = float(data["weight"])
            goal = str(data["goal"]).lower()
            activity = str(data["activity"]).lower()
            diet = str(data["diet"]).lower()

            if not name or not 13 <= age <= 100:
                raise ValueError("Enter a name and a valid age.")
            if not 100 <= height <= 250 or not 25 <= weight <= 350:
                raise ValueError("Check your height and weight.")
            if sex not in ("male", "female"):
                raise ValueError("Choose male or female.")
            if goal not in ("lose", "maintain", "gain"):
                raise ValueError("Choose a valid goal.")
            if activity not in ("low", "moderate", "high"):
                raise ValueError("Choose an activity level.")
            if diet not in ("vegetarian", "non-vegetarian", "vegan"):
                raise ValueError("Choose a valid diet.")

            conn.execute("""
                INSERT OR REPLACE INTO profile
                (id, name, age, sex, height, weight, goal, activity, diet)
                VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, age, sex, height, weight, goal, activity, diet))

            conn.commit()
            profile = dict(conn.execute(
                "SELECT * FROM profile WHERE id = 1"
            ).fetchone())

            return jsonify({
                "profile": profile,
                "recommendations": get_recommendations(profile)
            })

        except (KeyError, ValueError, TypeError) as error:
            return jsonify({"error": str(error) or "Check your details."}), 400
        finally:
            conn.close()

    row = conn.execute("SELECT * FROM profile WHERE id = 1").fetchone()
    conn.close()

    if not row:
        return jsonify({"profile": None})

    profile = dict(row)
    return jsonify({
        "profile": profile,
        "recommendations": get_recommendations(profile)
    })


@app.route("/api/logs", methods=["GET", "POST"])
def logs_api():
    conn = get_db()

    if request.method == "POST":
        data = request.get_json(silent=True) or {}

        try:
            log_date = str(data.get("log_date", date.today().isoformat()))
            date.fromisoformat(log_date)

            food = str(data.get("food", "")).strip()[:100]
            calories = int(data.get("calories", 0))
            workout = str(data.get("workout", "")).strip()[:100]
            minutes = int(data.get("workout_minutes", 0))
            water = float(data.get("water", 0))
            weight = float(data.get("weight", 0))

            if calories < 0 or minutes < 0 or water < 0 or weight < 0:
                raise ValueError("Values cannot be negative.")
            if calories > 10000 or minutes > 1440 or water > 20:
                raise ValueError("Please check the values you entered.")

            conn.execute("""
                INSERT INTO daily_logs
                (log_date, food, calories, workout, workout_minutes, water, weight)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (log_date, food, calories, workout, minutes, water, weight))

            conn.commit()
        except (ValueError, TypeError) as error:
            conn.close()
            return jsonify({"error": str(error)}), 400

    today = date.today().isoformat()

    today_logs = conn.execute("""
        SELECT * FROM daily_logs
        WHERE log_date = ?
        ORDER BY id DESC
    """, (today,)).fetchall()

    totals = conn.execute("""
        SELECT
            COALESCE(SUM(calories), 0) AS calories,
            COALESCE(SUM(workout_minutes), 0) AS workout_minutes,
            COALESCE(SUM(water), 0) AS water
        FROM daily_logs WHERE log_date = ?
    """, (today,)).fetchone()

    weekly = []
    for offset in range(6, -1, -1):
        day = (date.today() - timedelta(days=offset)).isoformat()
        result = conn.execute("""
            SELECT COALESCE(SUM(calories), 0) AS calories
            FROM daily_logs WHERE log_date = ?
        """, (day,)).fetchone()

        weekly.append({
            "date": day,
            "day": date.fromisoformat(day).strftime("%a"),
            "calories": result["calories"]
        })

    conn.close()

    return jsonify({
        "logs": [dict(row) for row in today_logs],
        "totals": dict(totals),
        "weekly": weekly
    })


initialize_db()

if __name__ == "__main__":
    app.run(debug=True)
