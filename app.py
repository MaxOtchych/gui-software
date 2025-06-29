from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import pyodbc
from config import Config
import logging
from datetime import datetime

# Initialisierung
app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

# Flask-Login Setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Admin Accounts
ADMIN_ACCOUNTS = {
    "emre.civelekoglu@finck-maier-consulting.de": {
        "name": "Emre Civelekoglu",
        "password": "admin123",
        "last_login": None
    },
    "joerg.finck@finck-maier-consulting.de": {
        "name": "Jörg Finck",
        "password": "admin123",
        "last_login": None
    },
    "olga.maier@finck-maier-consulting.de": {
        "name": "Olga Maier",
        "password": "admin123",
        "last_login": None
    }
}

class User(UserMixin):
    def __init__(self, user_id, name):
        self.id = user_id
        self.name = name

@login_manager.user_loader
def load_user(user_id):
    if user_id in ADMIN_ACCOUNTS:
        return User(user_id, ADMIN_ACCOUNTS[user_id]["name"])
    return None

def get_db_connection():
    try:
        conn = pyodbc.connect(
            f"DRIVER={Config.SQL_DRIVER};"
            f"SERVER={Config.SQL_SERVER};"
            f"DATABASE={Config.SQL_DATABASE};"
            f"UID={Config.SQL_USERNAME};"
            f"PWD={Config.SQL_PASSWORD}"
        )
        return conn
    except Exception as e:
        logging.error(f"Datenbankverbindungsfehler: {str(e)}")
        raise

# Routen
@app.route('/')
@login_required
def home():
    return redirect(url_for('dashboard'))  # Geändert zu Dashboard

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').lower()
        password = request.form.get('password', '')
        
        if email in ADMIN_ACCOUNTS and password == ADMIN_ACCOUNTS[email]["password"]:
            user = User(email, ADMIN_ACCOUNTS[email]["name"])
            login_user(user)
            ADMIN_ACCOUNTS[email]["last_login"] = datetime.now().strftime("%d.%m.%Y %H:%M")
            flash('Login erfolgreich!', 'success')
            return redirect(url_for('dashboard'))  # Weiterleitung zum Dashboard
        else:
            flash('Ungültige Anmeldedaten', 'error')

    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Statistikdaten abfragen
    cursor.execute("SELECT COUNT(*) FROM Mitarbeiter")
    total_employees = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM Abteilung")
    total_departments = cursor.fetchone()[0]
    
    # SQL Server verwendet TOP statt LIMIT
    cursor.execute("""
        SELECT TOP 5 a.Name, COUNT(m.MitarbeiterID) 
        FROM Abteilung a
        LEFT JOIN Mitarbeiter m ON a.AbteilungID = m.AbteilungID
        GROUP BY a.Name
        ORDER BY COUNT(m.MitarbeiterID) DESC
    """)
    department_stats = cursor.fetchall()
    
    # Letzte Aktivitäten
    cursor.execute("SELECT TOP 5 Vorname, Nachname, Email FROM Mitarbeiter ORDER BY MitarbeiterID DESC")
    recent_employees = cursor.fetchall()
    
    conn.close()
    
    return render_template('dashboard.html',
                         total_employees=total_employees,
                         total_departments=total_departments,
                         department_stats=department_stats,
                         recent_employees=recent_employees,
                         current_user=current_user,
                         last_login=ADMIN_ACCOUNTS[current_user.id]["last_login"])

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sie wurden abgemeldet.', 'info')
    return redirect(url_for('login'))

# Mitarbeiter Routen
@app.route('/mitarbeiter')
@login_required
def mitarbeiter():
    search_query = request.args.get('search', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if search_query:
        cursor.execute("""
            SELECT m.MitarbeiterID, m.Vorname, m.Nachname, m.Email, m.Telefon,
                   a.Name AS Abteilung, p.Bezeichnung AS Position
            FROM Mitarbeiter m
            JOIN Abteilung a ON m.AbteilungID = a.AbteilungID
            JOIN Position p ON m.PositionID = p.PositionID
            WHERE m.Vorname LIKE ? OR m.Nachname LIKE ? OR m.Email LIKE ?
            """, (f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'))
    else:
        cursor.execute("""
            SELECT m.MitarbeiterID, m.Vorname, m.Nachname, m.Email, m.Telefon,
                   a.Name AS Abteilung, p.Bezeichnung AS Position
            FROM Mitarbeiter m
            JOIN Abteilung a ON m.AbteilungID = a.AbteilungID
            JOIN Position p ON m.PositionID = p.PositionID
            """)
    
    mitarbeiter_liste = cursor.fetchall()
    conn.close()
    
    return render_template('mitarbeiter.html', 
                         mitarbeiter=mitarbeiter_liste,
                         search_query=search_query)

@app.route('/mitarbeiter/neu', methods=['GET', 'POST'])
@login_required
def mitarbeiter_neu():
    if request.method == 'POST':
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO Mitarbeiter (Vorname, Nachname, Email, Telefon, AbteilungID, PositionID)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                request.form['vorname'],
                request.form['nachname'],
                request.form['email'],
                request.form['telefon'],
                request.form['abteilung'],
                request.form['position']
            ))
            
            conn.commit()
            conn.close()
            flash('Mitarbeiter erfolgreich angelegt!', 'success')
            return redirect(url_for('mitarbeiter'))
        except Exception as e:
            flash(f'Fehler beim Anlegen: {str(e)}', 'error')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT AbteilungID, Name FROM Abteilung")
    abteilungen = cursor.fetchall()
    
    cursor.execute("SELECT PositionID, Bezeichnung FROM Position")
    positionen = cursor.fetchall()
    
    conn.close()
    
    return render_template('neu.html',
                         abteilungen=abteilungen,
                         positionen=positionen)

@app.route('/mitarbeiter/bearbeiten/<int:id>', methods=['GET', 'POST'])
@login_required
def mitarbeiter_bearbeiten(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        try:
            cursor.execute("""
                UPDATE Mitarbeiter SET
                    Vorname = ?,
                    Nachname = ?,
                    Email = ?,
                    Telefon = ?,
                    AbteilungID = ?,
                    PositionID = ?
                WHERE MitarbeiterID = ?
            """, (
                request.form['vorname'],
                request.form['nachname'],
                request.form['email'],
                request.form['telefon'],
                request.form['abteilung'],
                request.form['position'],
                id
            ))
            conn.commit()
            flash('Mitarbeiter erfolgreich aktualisiert!', 'success')
            return redirect(url_for('mitarbeiter'))
        except Exception as e:
            flash(f'Fehler beim Aktualisieren: {str(e)}', 'error')
    
    cursor.execute("SELECT * FROM Mitarbeiter WHERE MitarbeiterID = ?", id)
    mitarbeiter = cursor.fetchone()
    
    cursor.execute("SELECT AbteilungID, Name FROM Abteilung")
    abteilungen = cursor.fetchall()
    
    cursor.execute("SELECT PositionID, Bezeichnung FROM Position")
    positionen = cursor.fetchall()
    
    conn.close()
    
    return render_template('bearbeiten.html',
                         mitarbeiter=mitarbeiter,
                         abteilungen=abteilungen,
                         positionen=positionen)

@app.route('/mitarbeiter/löschen/<int:id>')
@login_required
def mitarbeiter_löschen(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM Mitarbeiter WHERE MitarbeiterID = ?", id)
        
        conn.commit()
        conn.close()
        flash('Mitarbeiter erfolgreich gelöscht!', 'success')
    except Exception as e:
        flash(f'Fehler beim Löschen: {str(e)}', 'error')
    
    return redirect(url_for('mitarbeiter'))

if __name__ == '__main__':
    app.run(debug=True)