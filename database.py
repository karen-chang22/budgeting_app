# connecting to DB
import sqlite3
connection = sqlite3.connect("users.db")
cursor = connection.cursor()


# users' tables
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
    ) """
)
# transactions tables
cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    type TEXT CHECK (type IN('income', 'expense')) NOT NULL, 
    amount REAL NOT NULL,
    date TEXT NOT NULL,
    category TEXT,
    recurring TEXT CHECK (recurring IN ('none', 'daily', 'weekly', 'biweekly', 'monthly', 'yearly')) DEFAULT 'none',
    notes TEXT, 
    FOREIGN KEY(user_id) REFERENCES users(id) 
    ) """
)
# goals tables
cursor.execute("""
CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    title TEXT NOT NULL,
    target_amount REAL NOT NULL,
    target_date TEXT,
    created_date TEXT,
    notes TEXT,
    current_amount REAL DEFAULT 0, 
    FOREIGN KEY (user_id) REFERENCES users(id)
)
""")


connection.commit()
connection.close()


