import os
import sqlite3
from datetime import datetime

DB_FILE = "advisory_platform.db"

def get_connection():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Company Profile Settings Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            company_name TEXT NOT NULL,
            industry TEXT NOT NULL,
            capital REAL NOT NULL,
            employees INTEGER NOT NULL,
            region TEXT NOT NULL
        )
    """)
    
    # Insert default settings if not exists
    cursor.execute("SELECT COUNT(*) FROM settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO settings (id, company_name, industry, capital, employees, region)
            VALUES (1, 'MChJ Yangi Biznes', 'Manufacturing', 50000000.0, 5, 'Tashkent City')
        """)
    
    # 2. Chat History Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 3. Statutory Fund (Ustav Fondi) Tracker Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ustav_fondi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            founder_name TEXT NOT NULL,
            share_percentage REAL NOT NULL,
            contribution_amount REAL NOT NULL,
            date_logged DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def get_settings():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM settings WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {
        "company_name": "MChJ Yangi Biznes",
        "industry": "Manufacturing",
        "capital": 50000000.0,
        "employees": 5,
        "region": "Tashkent City"
    }

def save_settings(company_name, industry, capital, employees, region):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO settings (id, company_name, industry, capital, employees, region)
        VALUES (1, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            company_name=excluded.company_name,
            industry=excluded.industry,
            capital=excluded.capital,
            employees=excluded.employees,
            region=excluded.region
    """, (company_name, industry, capital, employees, region))
    conn.commit()
    conn.close()

def add_chat_message(session_id, role, content):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO chat_history (session_id, role, content)
        VALUES (?, ?, ?)
    """, (session_id, role, content))
    conn.commit()
    conn.close()

def get_chat_history(session_id):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT role, content, timestamp 
        FROM chat_history 
        WHERE session_id = ? 
        ORDER BY id ASC
    """, (session_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def clear_chat_history(session_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_history WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()

def get_all_chat_sessions():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT session_id FROM chat_history ORDER BY id DESC")
    sessions = [row[0] for row in cursor.fetchall()]
    conn.close()
    return sessions

def add_ustav_entry(founder_name, share_percentage, contribution_amount):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ustav_fondi (founder_name, share_percentage, contribution_amount)
        VALUES (?, ?, ?)
    """, (founder_name, share_percentage, contribution_amount))
    conn.commit()
    conn.close()

def get_ustav_entries():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ustav_fondi ORDER BY date_logged ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def clear_ustav_entries():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ustav_fondi")
    conn.commit()
    conn.close()
