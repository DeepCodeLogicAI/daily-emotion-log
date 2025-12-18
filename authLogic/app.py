from flask import Flask, render_template, request, redirect
from db import get_connection

app = Flask(__name__)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_connection()
        cur = conn.cursor()

        sql = "SELECT * FROM users WHERE username=%s AND password=%s"
        cur.execute(sql, (username, password))
        user = cur.fetchone()

        conn.close()

        if user:
            return "로그인 성공"
        else:
            return "로그인 실패"

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_connection()
        cur = conn.cursor()

        sql = "INSERT INTO users (username, password) VALUES (%s, %s)"
        cur.execute(sql, (username, password))

        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("register.html")

@app.route("/")
def home():
    return render_template("home.html")

if __name__ == "__main__":
    app.run(debug=True)
