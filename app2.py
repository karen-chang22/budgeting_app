import sqlite3
import bcrypt
import math
from flask import Flask, request, render_template, request, redirect, session, url_for, flash
from datetime import datetime
import os

app = Flask(__name__) # creates Flask app instance
app.secret_key = "secret-key" #required to see sessions

connection = None
@app.route("/") #route decorator - defines which URL this function will respond to 
# / for homepage
def home(): # defining function named home, Flask runs this function if smo visists
    return render_template("home.html")
    return "🌷 Welcome to Path2Save"

@app.route("/register", methods=["GET", "POST"]) #register page
def register(): 
    if request.method == "GET":
        return render_template("register.html")
    email = request.form.get("email") 
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")

    if password != confirm_password:
        flash("Passwords do not match!")
        return redirect(url_for("register"))

    # Hash the password
    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
     # Save to database
    connection = sqlite3.connect("users.db") 
    cursor = connection.cursor() 
    try: #pyton TRIES to run the code; if no error --> skips 'except' block
        cursor.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, hashed_pw))
        connection.commit()
        session["email"] = email
        return redirect(url_for("dashboard")) #runs ONLY if NO ERROR occurred
    except sqlite3.IntegrityError: #runs if the email already exists, bc emails must be unique!!!
        message = "⚠️ Email already registered."
        return render_template("register.html", message=message)
    finally:
        connection.close() #close the connection to database! #'finally always runs
 

# /login 
@app.route("/login", methods=["Get", "POST"])  # new webpage for login, only accepting POST
def login():
    if request.method == "GET":
        return render_template("login.html")
    email = request.form.get("email")
    password = request.form.get("password")
    connection = None  # fix: declare the variable before the try
    try:
        connection = sqlite3.connect("users.db")
        cursor = connection.cursor()
        # Look for the email
        cursor.execute("SELECT password FROM users WHERE email = ?", (email,))
        result = cursor.fetchone()
        if result:
            hashed_pw = result[0]
            # Compare hashed passwords
            if bcrypt.checkpw(password.encode("utf-8"), hashed_pw): #correct password! Logged in~
                session["email"] = email
                return redirect(url_for("dashboard"))
                # render_template help connect backend to frontend
            else:
                message = "❌ Incorrect password."
                return render_template("login.html", message=message)
        else:
            message = "❌ Email not found."
            return render_template("login.html", message=message)
    except Exception as e:
        message = f"⚠️ Error: {e}"
    finally:
        if connection:  # fix: only close if connection is not None
            connection.close()

    return render_template("login.html", message=message)

@app.route("/dashboard") #main dashboard page
def dashboard():
    if "email" not in session:
        return redirect(url_for("login"))

    email = session["email"]
    today = datetime.now().strftime("%B %d, %Y") #gets the date and turn into human-readable format
    #ex: Sep 05, 2025

    connection = sqlite3.connect("users.db")
    cursor = connection.cursor()

    current_month = datetime.now().strftime("%Y-%m") #get the current year and month, we are only
    #showing this current month's transactions here

    cursor.execute("""
        SELECT SUM(amount) FROM transactions
        WHERE user_id = (SELECT id FROM users WHERE email = ?)
        AND type = 'income' AND date LIKE ?
    """, (email, current_month + '%')) #search for ALL transactions types under 'income' where the date
    # starts with the current month (add all 'income' transactions) 
    income_total = cursor.fetchone()[0] or 0 #get the total sum, and if none, then shows 0

    cursor.execute("""
        SELECT SUM(amount) FROM transactions
        WHERE user_id = (SELECT id FROM users WHERE email = ?) 
        AND type = 'expense' AND date LIKE ?
    """, (email, current_month + '%')) #similar to income, we now have one for ALL transactions for
    #'expenses' in the current month (shows sum as well)
    # the user_id line just ensures that data is coming from only the rows that belong to the user
    # the % is to retrieve all data that ends in '2025-10'; note: current_month includes the year too!
    expense_total = cursor.fetchone()[0] or 0

    connection.close()

    return render_template("dashboard.html",
        email=email,
        today=today,
        income=income_total,
        expense=expense_total) # sends the data from Python to the HTML frontend & telling it what each variable contains

@app.route("/transactions", methods=["GET", "POST"]) #for adding transactions
def transactions():
    if "email" not in session:
        return redirect(url_for("login"))

    email = session["email"]
    connection = sqlite3.connect("users.db")
    connection.row_factory = sqlite3.Row  # <-- This enables named access
    cursor = connection.cursor()

    # Handle form submission
    if request.method == "POST":
        type_ = request.form.get("type")
        category = request.form.get("category")
        amount = request.form.get("amount")
        date = request.form.get("date")
        notes = request.form.get("notes")
        recurring = request.form.get("recurring")

        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO transactions (user_id, type, category, amount, date, notes, recurring)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, type_, category, amount, date, notes, recurring))

        connection.commit()
        connection.close()

    # Always retrieve updated list of transactions
    connection = sqlite3.connect("users.db")
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    cursor.execute("""
        SELECT * FROM transactions
        WHERE user_id = (SELECT id FROM users WHERE email = ?)
        ORDER BY date DESC
    """, (email,))
    transactions = cursor.fetchall()
    connection.close()
    return render_template("transactions.html", transactions=transactions)

@app.route("/delete_transaction/<int:transaction_id>", methods=["POST"]) #for deleting transactions
def delete_transaction(transaction_id):
    if "email" not in session:
        return redirect(url_for("login"))

    connection = sqlite3.connect("users.db")
    cursor = connection.cursor()
    cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
    connection.commit()
    connection.close()
    return redirect(url_for("transactions"))

@app.route("/goals", methods=["GET", "POST"]) # my goals page!!!
def goals():
    connection = sqlite3.connect("users.db")
    connection.row_factory = sqlite3.Row # --> crucial for dictionary-style access like t['goals'] in html
    cursor = connection.cursor()
    if request.method == "POST":
        created_date = datetime.now().strftime("%Y-%m-%d") # autofills the date they sumbitted the form
        title = request.form.get("title")
        target_amount = request.form.get("target_amount")
        target_date = request.form.get("target_date")
        notes = request.form.get("notes")
        current_amount = 0
        
        # Get user_id using session
        cursor.execute("SELECT id FROM users WHERE email = ?", (session["email"],))
        user_id = cursor.fetchone()[0]

        # Insert into goals table
        cursor.execute("""
            INSERT INTO goals (user_id, title, target_amount, target_date, created_date, notes, current_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, title, target_amount, target_date, created_date, notes, current_amount))
        connection.commit()
        connection.close()

        return redirect(url_for("goals"))

    # If GET, show current goals
    created_date = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT * FROM goals WHERE user_id = (SELECT id FROM users WHERE email = ?)", (session["email"],))
    rows = cursor.fetchall()
    goals = [] #creates an empty list to store the users' goal data (title, targeted amount, as well as progress) as dictionary
    for row in rows:
        progress = 0
        if row["target_amount"] > 0:
            progress = min((row["current_amount"] / row["target_amount"]) * 100, 100) #calculate percent done & ensure it doesn't exceed 100%
        goal = dict(row) # converts sqlite3.Row object into a dictionary so I can modify (include all fields)
        goal["progress"] = math.floor(progress) #adding a new field: progress to the dictionary round(, 2) rounds to 2 decimal places
        goals.append(goal) #adds the final goal dictionary (with progress) into the goals list
        goal["left_to_save"] = max(row["target_amount"] - row["current_amount"], 0)
    return render_template("newgoals.html", goals=goals, now=created_date)
    

@app.route('/goals/update/<int:goal_id>', methods=['POST']) # updating goal progress $$$ for each goal
def update_goal(goal_id):
    amount = float(request.form['amount'])

    connection = sqlite3.connect('users.db')
    cursor = connection.cursor()

    cursor.execute("UPDATE goals SET current_amount = current_amount + ? WHERE id = ?", (amount, goal_id,))

    connection.commit()
    connection.close()

    return redirect(url_for('goals'))

@app.route("/delete_goal/<int:goal_id>", methods=["POST"])
def delete_goal(goal_id):
    if "email" not in session:
        return redirect(url_for("login"))
    connection = sqlite3.connect("users.db")
    cursor = connection.cursor()
    cursor.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
    connection.commit()
    connection.close()
    return redirect(url_for("goals"))

@app.route('/ai', methods=['GET', 'POST'])
def ai_suggestions():
    if "email" not in session: #though users SHOULD be logged in already, better to add this in for security purposes; and prompts users to...
        return redirect(url_for('login')) #... login if they were given the url for example
    
    connection = sqlite3.connect('users.db')
    connection.row_factory = sqlite3.Row 
    cursor = connection.cursor()

    email = session['email'] #initialize first or else it doesnt know what 'email' holds (below)
    cursor.execute("SELECT id FROM users WHERE email = ?", (email,)) #gotta get it from db before assigning
    user_id = cursor.fetchone()[0] #get the specific id for that user (unique)
    session['user_id'] = user_id # creating a new session (numeric) bc the last one was for email

    # 1. get transactions
    cursor.execute("SELECT type, amount, date, category FROM transactions WHERE user_id = ?", (user_id,))
    transactions = [dict(row) for row in cursor.fetchall()] # was an issue as fetall() reuturns a list of tuples, not a dict; so we dict it
    # 2. get goals
    cursor.execute("SELECT title, target_amount, current_amount, target_date FROM goals WHERE user_id = ?", (user_id,))
    goals = [dict(row) for row in cursor.fetchall()] 

    connection.close()

    suggestions = []

    # BASIC - static suggestions (arithmetic) NOT THE BEST OPTION, this is just similar AI-logic here // Ex: watching food expenses
    food_spending = sum(t["amount"] for t in transactions if t["type"] == "expense" and t["category"].lower() == "food & drinks")
    if food_spending > 200:
        suggestions.append(f"🍔 You've spent ${food_spending:.2f} on food. Consider meal prepping or cutting back.")

    # static suggestions 2 // Ex: goal analysis
    for g in goals:
        title = g["title"]
        target = g["target_amount"]
        current = g["current_amount"]
        if current < target:
            percent = (current / target) * 100
            suggestions.append(f"🎯 For goal '{title}', you're {percent:.1f}% there. Keep going!")

    return render_template('ai.html', suggestions=suggestions)

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("home")) # users logout -> clear session


if __name__ == "__main__":
    app.run(debug=True)