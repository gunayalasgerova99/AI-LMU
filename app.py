from flask import Flask, render_template, request, redirect, session, jsonify
import os
import psycopg2

app = Flask(__name__)
app.secret_key = "secret123"

DATABASE_URL = os.environ.get("DATABASE_URL")

users = {
    "P001": "lmu001",
    "P002": "lmu002",
    "P003": "lmu003",
    "P004": "lmu004",
    "P005": "lmu005",
    "P006": "lmu006",
    "P007": "lmu007",
    "P008": "lmu008",
    "P009": "lmu009",
    "P010": "lmu010"
}

QUESTIONS = [
    "1. Going to a theme park",
    "2. Experiencing a car crash",
    "3. Going to a swimming pool and that your swimming trunks fell off",
    "4. Being hospitalized and undergoing surgery",
    "5. Having extracted a tooth by a dentist",
    "6. Building camps with friends",
    "7. Going ice skating on natural ice in the winter",
    "8. Going camping with your family in tents",
    "9. Falling off your bike as a child and wounded yourself",
    "10. Having a verbal fight with your friends at school",
    "11. Going on a hot air balloon ride",
    "12. Going to Disneyland Paris and meeting your favorite figure",
    "13. Breaking something valuable in a store",
    "14. Going to the doctor to suture a wound",
    "15. Falling of the trampoline and broke something",
    "16. A plaster of a broken arm of leg written full by classmates, family, etc.",
    "17. Going on skiing holiday",
    "18. Experiencing a move to another place",
    "19. Going to a fair and going into an attraction",
    "20. Going to a national themepark"
]

SUPPORT_PHRASES = [
    "Thank you, let’s continue.",
    "Got it, we’ll go to the next one.",
    "Thanks, you’re doing well.",
    "Thank you for your answer.",
    "Okay, let’s continue with the next item.",
    "Thanks, we can move on.",
    "Got it, thank you.",
    "Thank you, let’s keep going.",
    "Thanks, next one.",
    "Okay, thank you for responding.",
    "Got it, we’ll continue.",
    "Thank you, you’re doing fine.",
    "Thanks, let’s move to the next item.",
    "Okay, we’ll go on.",
    "Thank you, next question.",
    "Got it, let’s continue.",
    "Thanks, we’re moving along well.",
    "Okay, thank you.",
    "Thank you, almost there.",
    "Thanks for your answer."
]

ANSWER_MAP = {
    "A": "0 times",
    "B": "1 time",
    "C": "2 times",
    "D": "3 or more times"
}

user_progress = {}
user_started = {}


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS responses (
            id SERIAL PRIMARY KEY,
            participant_id TEXT,
            question TEXT,
            answer_letter TEXT,
            answer_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    cur.close()
    conn.close()


def save_response(user, question, answer):
    conn = get_connection()
    cur = conn.cursor()

    answer_upper = answer.strip().upper()
    answer_text = ANSWER_MAP.get(answer_upper, answer_upper)

    cur.execute("""
        INSERT INTO responses (participant_id, question, answer_letter, answer_text)
        VALUES (%s, %s, %s, %s);
    """, (user, question, answer_upper, answer_text))

    conn.commit()
    cur.close()
    conn.close()


def question_text(question):
    return (
        "Please indicate how many times this happened:\n"
        + question
        + "\n\nA = 0 times\nB = 1 time\nC = 2 times\nD = 3 or more times"
    )


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form["user"].strip()
        pw = request.form["pw"].strip()

        if user in users and users[user] == pw:
            session["user"] = user
            user_progress[user] = 0
            user_started[user] = False
            return redirect("/chat")
        else:
            return "Wrong login"

    return render_template("login.html")


@app.route("/chat")
def chat():
    if "user" not in session:
        return redirect("/")
    return render_template("chat.html", user=session["user"])


@app.route("/start")
def start():
    if "user" not in session:
        return jsonify({"reply": "Please log in first."})

    user = session["user"]
    user_progress[user] = 0
    user_started[user] = False

    intro = """Hi, and welcome to this first part of the study 🙂

I’ll guide you through a short set of questions about events that may have happened during your childhood.

There are no right or wrong answers — just go with what feels accurate to you.

For each event, please answer with one letter:
A = 0 times
B = 1 time
C = 2 times
D = 3 or more times

Take your time, and feel free to stop at any point if you wish.

Whenever you're ready, type “ready” and we’ll begin."""

    return jsonify({"reply": intro})


@app.route("/send", methods=["POST"])
def send():
    if "user" not in session:
        return jsonify({"reply": "Please log in first."})

    user = session["user"]
    user_message = request.json["message"].strip()

    if user not in user_progress:
        user_progress[user] = 0

    if user not in user_started:
        user_started[user] = False

    if user_started[user] is False:
        user_started[user] = True
        first_question = QUESTIONS[0]

        return jsonify({
            "reply": "Great, thank you — we’ll start now.\n\n" + question_text(first_question)
        })

    current_q = user_progress[user]
    answer_upper = user_message.upper()

    if answer_upper not in ANSWER_MAP:
        return jsonify({
            "reply": "Please answer with one letter only: A, B, C, or D."
        })

    if current_q < len(QUESTIONS):
        save_response(user, QUESTIONS[current_q], answer_upper)

    user_progress[user] += 1
    next_q = user_progress[user]

    if next_q < len(QUESTIONS):
        next_question = QUESTIONS[next_q]
        support = SUPPORT_PHRASES[current_q]

        full_reply = support + "\n\n" + question_text(next_question)
    else:
        full_reply = """Thank you very much for taking part in this first part of the study.

We really appreciate your time and responses.

Please remember not to discuss these events with others, as it may influence the study.

Thank you again."""

    return jsonify({"reply": full_reply})


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

    
    @app.route("/download")
def download():
    import csv
    from flask import Response

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT participant_id, question, answer_letter, answer_text FROM responses")
    rows = cur.fetchall()

    def generate():
        yield "participant_id,question,answer_letter,answer_text\n"
        for row in rows:
            yield ",".join([str(x).replace(",", " ") for x in row]) + "\n"

    cur.close()
    conn.close()

    return Response(generate(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment;filename=data.csv"})
                    
                    if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=10000)