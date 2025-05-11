from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_sqlalchemy import SQLAlchemy
import os
import secrets
from datetime import timedelta
import mysql.connector
from mysql.connector import Error
from datetime import datetime

# App-Instanz erstellen
app = Flask(__name__)
CORS(app)  # CORS aktivieren, um Anfragen vom Frontend zu erlauben

# Sicherer JWT-Schlüssel (in der Produktion als Umgebungsvariable setzen)
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', secrets.token_hex(32))
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=10)  # Ablaufzeit des Tokens (30 Minuten)

# SQLAlchemy konfigurieren

# SQLite Konfiguration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# SQLAlchemy-Datenbankinstanz erstellen
db = SQLAlchemy(app)

# JWTManager initialisieren
jwt = JWTManager(app)


def get_db_connection():
    connection = mysql.connector.connect(
        host='localhost',
        user='root',  # Dein MySQL-Benutzername
        password='Xiaomiao1',  # Dein MySQL-Passwort
        database='phase1_mydb'  # Dein Datenbankname
    )
    return connection


# SQLAlchemy-Klassen definieren (mit englischen Attributen)

class User(db.Model):
    __tablename__ = 'Benutzer'  # Originaltabellenname in der DB
    id = db.Column('BenutzerID', db.Integer, primary_key=True, autoincrement=True)
    username = db.Column('username', db.String(255), nullable=False)
    password = db.Column('passwort', db.String(225), nullable=False)
    reservations = db.relationship("Reservation", back_populates="user")


class Location(db.Model):
    __tablename__ = 'Standort'
    id = db.Column('StandortID', db.Integer, primary_key=True, autoincrement=True)
    city = db.Column('Ort', db.String(255), nullable=False)
    rooms = db.relationship("Room", back_populates="location")


class Room(db.Model):
    __tablename__ = 'Raum'
    id = db.Column('RaumID', db.Integer, primary_key=True, autoincrement=True)
    name = db.Column('Raumbezeichnung', db.String(255), nullable=False)
    capacity = db.Column('Kapazität', db.Integer)
    location_id = db.Column('StandortID', db.Integer, db.ForeignKey('Standort.StandortID'))
    location = db.relationship("Location", back_populates="rooms")
    reservations = db.relationship("Reservation", back_populates="room")


class Reservation(db.Model):
    __tablename__ = 'Reservierung'
    id = db.Column('id', db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column('BenutzerID', db.Integer, db.ForeignKey('Benutzer.BenutzerID'))
    room_id = db.Column('RaumID', db.Integer, db.ForeignKey('Raum.RaumID'))
    purpose = db.Column('Zweck', db.String(50))
    start_time = db.Column('Startzeit', db.DateTime)
    end_time = db.Column('Endzeit', db.DateTime)
    user = db.relationship("User", back_populates="reservations")
    room = db.relationship("Room", back_populates="reservations")


# Beispiel-Benutzerdatenbank (in der Praxis: richtige Datenbank verwenden)
users = {
    "testuser": "testpassword"
}


# Offene Route: Einfacher API-Endpunkt ohne Authentifizierung
@app.route("/api/home", methods=['GET'])
def return_home():
    return jsonify({
        'message': "Hi, what's up?!",
        'people': ['kevin', 'kaize', 'wu']
    })


# Route zum Abrufen aller Zimmer
@app.route("/api/rooms", methods=['GET'])
def get_all_rooms():
    # Alle Räume abfragen
    rooms = Room.query.all()

    # Liste der Räume erstellen
    room_list = [
        {
            "id": room.id,
            "name": room.name,
            "capacity": room.capacity,
            "location": room.location.city  # Wenn du den Standort des Raumes einfügen möchtest
        }
        for room in rooms
    ]

    return jsonify(rooms=room_list), 200


# Login-Route: Erzeugt einen neuen JWT bei erfolgreichem Login
@app.route("/api/login", methods=['POST'])
def login():
    data = request.get_json()
    username = data['username']
    password = data['password']

    # Benutzer in der SQLAlchemy-Datenbank suchen
    user = User.query.filter_by(username=username, password=password).first()

    if user:
        access_token = create_access_token(identity=user.username)
        return jsonify(access_token=access_token), 200
    else:
        return jsonify({"msg": "Invalid credentials"}), 401


# Geschützte Route: Nur mit gültigem JWT-Token aufrufbar
@app.route("/api/protected", methods=['GET'])
@jwt_required()
def protected():
    # Der aktuelle Benutzer wird aus dem Token abgerufen
    current_user = get_jwt_identity()

    return jsonify(logged_in_as=current_user, msg="Welcome to the protected route!"), 200


# Geschützte Route zum Abrufen der Reservierungen eines Benutzers
@app.route("/api/reservations", methods=['GET'])
@jwt_required()
def get_user_reservations():
    # Der aktuelle Benutzer wird aus dem Token abgerufen
    current_user = get_jwt_identity()

    user = User.query.filter_by(username=current_user).first()
    if not user:
        return jsonify({"msg": "User not found"}), 404

    # Reservierungen für den aktuellen Benutzer über SQLAlchemy abfragen
    reservations = Reservation.query.filter_by(user_id=user.id).all()
    reservation_list = [
        {
            "id": r.id,
            "Zweck": r.purpose,
            "Startzeit": r.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            "Endzeit": r.end_time.strftime('%Y-%m-%d %H:%M:%S'),
            "room_name": r.room.name,

        }
        for r in reservations
    ]

    return jsonify(reservations=reservation_list), 200


@app.route("/api/reservations_withoutAuth", methods=['GET'])
def get_all_reservations():
    # Alle Reservierungen abfragen
    reservations = Reservation.query.all()

    # Liste der Reservierungen erstellen
    reservation_list = [
        {
            "id": r.id,
            "Zweck": r.purpose,
            "Startzeit": r.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            "Endzeit": r.end_time.strftime('%Y-%m-%d %H:%M:%S'),
            "room_id": r.room.id,
            "room_name": r.room.name,
            "location": r.room.location.city  # Optional: Standort des Raumes hinzufügen
        }
        for r in reservations
    ]

    return jsonify(reservations=reservation_list), 200


@app.route("/api/reserve", methods=['POST'])
@jwt_required()  # Stelle sicher, dass ein JWT-Token benötigt wird
def reserve_room():
    current_user = get_jwt_identity()  # Hole den aktuellen Benutzer
    user = User.query.filter_by(username=current_user).first()  # Hole den Benutzer aus der DB

    if not user:
        return jsonify({"msg": "User not found"}), 404

    data = request.get_json()  # Lese die JSON-Daten von der Anfrage
    start = data.get("start")  # Lese Startzeit
    end = data.get("end")  # Lese Endzeit
    room_id = data.get("room_id")  # Lese die Raum-ID
    purpose = data.get("purpose")  # Lese den Zweck der Buchung

    # Konvertiere das Datum in das richtige Format
    try:
        start_time = datetime.fromisoformat(start.replace("Z", "+00:00"))  # Ersetze 'Z' mit '+00:00' für UTC
        end_time = datetime.fromisoformat(end.replace("Z", "+00:00"))
    except ValueError as e:
        return jsonify({"msg": "Fehler beim Konvertieren des Datums: " + str(e)}), 400

    # Drucken der Reservierungsdetails in die Konsole
    print(
        f"Reservierung erhalten: Benutzer-ID: {user.id}, Start: {start_time}, End: {end_time}, Raum-ID: {room_id}, Zweck: {purpose}")

    # Neue Reservierung erstellen
    new_reservation = Reservation(
        user_id=user.id,
        room_id=room_id,
        purpose=purpose,
        start_time=start_time,
        end_time=end_time
    )

    try:
        # Reservierung zur Datenbank hinzufügen und speichern
        db.session.add(new_reservation)
        db.session.commit()
        return jsonify({"msg": "Reservierung erfolgreich!"}), 201
    except Exception as e:
        # Fehlerbehandlung bei der Speicherung
        db.session.rollback()  # Rollback bei Fehler
        print(f"Fehler beim Speichern der Reservierung: {e}")
        return jsonify({"msg": "Fehler bei der Reservierung. Bitte versuchen Sie es erneut."}), 500


@app.route("/api/signup", methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    # Prüfen ob Benutzer bereits existiert
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return jsonify({"msg": "Benutzername bereits vergeben"}), 409

    # Neuen Benutzer erstellen
    new_user = User(username=username, password=password)

    try:
        db.session.add(new_user)
        db.session.commit()

        # Direkt einen Token erstellen für Auto-Login
        access_token = create_access_token(identity=username)
        return jsonify({
            "msg": "Registrierung erfolgreich",
            "access_token": access_token
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Fehler bei der Registrierung"}), 500

# Neue Route zum Löschen von Reservierungen
@app.route("/api/reservations/<int:reservation_id>", methods=['DELETE'])
@jwt_required()
def delete_reservation(reservation_id):
    current_user = get_jwt_identity()
    user = User.query.filter_by(username=current_user).first()
    
    if not user:
        return jsonify({"msg": "User not found"}), 404

    reservation = Reservation.query.get(reservation_id)
    
    if not reservation:
        return jsonify({"msg": "Reservierung nicht gefunden"}), 404
        
    if reservation.user_id != user.id:
        return jsonify({"msg": "Nicht autorisiert"}), 403

    try:
        db.session.delete(reservation)
        db.session.commit()
        return jsonify({"msg": "Reservierung erfolgreich gelöscht"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e)}), 500

# Neue Route zum Aktualisieren von Reservierungen
@app.route("/api/reservations/<int:reservation_id>", methods=['PUT'])
@jwt_required()
def update_reservation(reservation_id):
    current_user = get_jwt_identity()
    user = User.query.filter_by(username=current_user).first()
    
    if not user:
        return jsonify({"msg": "User not found"}), 404

    reservation = Reservation.query.get(reservation_id)
    
    if not reservation:
        return jsonify({"msg": "Reservierung nicht gefunden"}), 404
        
    if reservation.user_id != user.id:
        return jsonify({"msg": "Nicht autorisiert"}), 403

    data = request.get_json()
    try:
        if 'start' in data:
            reservation.start_time = datetime.fromisoformat(data['start'].replace("Z", "+00:00"))
        if 'end' in data:
            reservation.end_time = datetime.fromisoformat(data['end'].replace("Z", "+00:00"))
        if 'purpose' in data:
            reservation.purpose = data['purpose']
            
        db.session.commit()
        return jsonify({
            "msg": "Reservierung aktualisiert",
            "reservation": {
                "id": reservation.id,
                "Zweck": reservation.purpose,
                "Startzeit": reservation.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                "Endzeit": reservation.end_time.strftime('%Y-%m-%d %H:%M:%S'),
                "room_name": reservation.room.name
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e)}), 500

# Am Ende der Datei vor dem Serverstart Datenbanktabellen erstellen
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        if not User.query.first():
            # Moderne Standortbezeichnungen
            locations = [
                Location(city="Innovation Campus"),
                Location(city="Downtown Hub"),
                Location(city="Urban Oasis"),
                Location(city="Tech Tower")
            ]
            db.session.add_all(locations)
            
            # Vielfältige Raumtypen
            rooms = [
                Room(name="Brainstorm Lounge", capacity=8, location=locations[0]),
                Room(name="Executive Suite", capacity=12, location=locations[1]),
                Room(name="Creative Lab", capacity=15, location=locations[2]),
                Room(name="Sky Conference", capacity=20, location=locations[3])
            ]
            db.session.add_all(rooms)
            
            # Normale Benutzernamen
            users = [
                User(username="max.mustermann", password="S1cher#2024"),
                User(username="lina.hoffmann", password="Passwort!123"),
                User(username="felix.bauer", password="Meet1ngRoom"),
                User(username="sophie.becker", password="Event$pace")
            ]
            db.session.add_all(users)
            
            # Typische Buchungsszenarien
            reservations = [
                Reservation(
                    user=users[0],
                    room=rooms[0],
                    purpose="Startup Pitch Training",
                    start_time=datetime(2025, 5, 10, 9, 0),
                    end_time=datetime(2025, 5, 10, 12, 0)
                ),
                Reservation(
                    user=users[1],
                    room=rooms[1],
                    purpose="Kundengespräch ACME Corp",
                    start_time=datetime(2025, 5, 11, 14, 30),
                    end_time=datetime(2025, 5, 11, 16, 0)
                ),
                Reservation(
                    user=users[2],
                    room=rooms[2],
                    purpose="Design Thinking Workshop",
                    start_time=datetime(2025, 5, 12, 10, 0),
                    end_time=datetime(2025, 5, 12, 17, 0)
                ),
                Reservation(
                    user=users[3],
                    room=rooms[3],
                    purpose="Jahresversammlung",
                    start_time=datetime(2025, 5, 13, 8, 0),
                    end_time=datetime(2025, 5, 13, 18, 0)
                )
            ]
            db.session.add_all(reservations)
            
            db.session.commit()
            print("✅ Universelle Testdaten für Raumverwaltung initialisiert")

    app.run(debug=True, port=8080)
