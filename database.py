import sqlite3
import datetime
import os
import shutil
from faker import Faker  # Import Faker for generating mock data
import random


def init_database():
    """
    Initialize or reuse the existing database.
    Weekly backups are made with a timestamped filename.
    """
    base_db = "client_database.db"

    # Create or reuse the main database
    is_new = not os.path.exists(base_db)
    conn = sqlite3.connect(base_db)
    cursor = conn.cursor()

    if is_new:
        print("🆕 Creating new main database...")
        create_tables(cursor)
        insert_mock_data(cursor)
        conn.commit()
    else:
        print("🟢 Reusing existing database...")

    # Weekly backup logic
    backup_folder = "db_backups"
    os.makedirs(backup_folder, exist_ok=True)

    today = datetime.date.today()
    current_week = today.isocalendar()[1]  # Get ISO week number
    year = today.year

    backup_name = f"client_database_{year}_W{current_week}.db"
    backup_path = os.path.join(backup_folder, backup_name)

    if not os.path.exists(backup_path):
        print(f"📦 Creating weekly backup: {backup_name}")
        shutil.copyfile(base_db, backup_path)
    else:
        print(f"✅ Weekly backup already exists: {backup_name}")

    print(f"✅ Database ready: {base_db}")
    return conn

def create_tables(cursor):
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        gender TEXT,
        birthdate DATE,
        phone TEXT,
        email TEXT,
        address1 TEXT,
        address2 TEXT,
        city TEXT,
        state TEXT,
        zip TEXT,
        referred_by TEXT,
        profile_picture TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS client_health_info (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL,
        allergies TEXT,
        health_conditions TEXT,
        medications TEXT,
        treatment_areas TEXT,
        current_products TEXT,
        skin_conditions TEXT,
        other_notes TEXT,
        desired_improvement TEXT,
        FOREIGN KEY (client_id) REFERENCES clients (id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL,
        date DATE NOT NULL,
        type TEXT NOT NULL,
        treatment TEXT,
        price TEXT,
        photos_taken TEXT DEFAULT 'No',
        treatment_notes TEXT,
        FOREIGN KEY (client_id) REFERENCES clients (id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS client_images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL,
        shift INTEGER DEFAULT NULL,
        zoom INTEGER DEFAULT NULL,
        FOREIGN KEY(client_id) REFERENCES clients (id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS photos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL,
        appointment_id INTEGER NOT NULL,
        appt_date DATE,
        file_path TEXT NOT NULL,
        type TEXT,
        description TEXT DEFAULT '',
        FOREIGN KEY (client_id) REFERENCES clients (id) ON DELETE CASCADE,
        FOREIGN KEY (appointment_id) REFERENCES appointments (id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS prescriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL,
        appointment_id INTEGER,
        form_type TEXT,
        file_path TEXT NOT NULL,
        notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients(id), ON DELETE CASCADE,
        FOREIGN KEY (appointment_id) REFERENCES appointments(id) ON DELETE CASCADE
    )
    """)


def format_fake_phone():
    """Generate a fake phone number in the format (XXX) XXX-XXXX."""
    area_code = random.randint(200, 999)  # Avoids 000 or invalid area codes
    first_three = random.randint(200, 999)  # Avoids 000
    last_four = random.randint(1000, 9999)
    return f"({area_code}) {first_three}-{last_four}"

def insert_mock_data(cursor):
    """Insert mock data into the database if it doesn't already exist."""
    fake = Faker()

    # Check if data already exists in the clients table
    cursor.execute("SELECT COUNT(*) FROM clients")
    if cursor.fetchone()[0] == 0:
        # Generate 100 mock clients
        mock_clients = []
        for _ in range(100):
            address = fake.address().split("\n")
            address1 = address[0]
            address2 = address[1] if len(address) > 1 else ""
            mock_clients.append((
                fake.name(),
                fake.random_element(["Male", "Female"]),
                fake.date_of_birth(minimum_age=18, maximum_age=80).strftime("%m/%d/%Y"),
                format_fake_phone(),
                fake.email(),
                address1,
                address2,
                fake.city(),
                fake.state(),
                fake.zipcode(),
                fake.name() if fake.boolean() else "",
                fake.name()
            ))
        cursor.executemany("""
        INSERT INTO clients (full_name, gender, birthdate, phone, email, address1, address2, city, state, zip, referred_by, profile_picture)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, mock_clients)


    # Check if data already exists in the client_health_info table
    cursor.execute("SELECT COUNT(*) FROM client_health_info")
    if cursor.fetchone()[0] == 0:
        # Generate 100 mock health records
        mock_health_info = [
            (
                fake.random_int(min=1, max=100),    # client_id
                ", ".join(fake.words(nb=3)),        # Allergies as a comma-separated string
                fake.sentence(nb_words=4),          # Health conditions
                ", ".join(fake.words(nb=2)),        # Medications as a comma-separated string
                ", ".join(fake.words(nb=3)),        # Treatment areas as a comma-separated string
                ", ".join(fake.words(nb=2)),        # Current products as a comma-separated string
                ", ".join(fake.words(nb=3)),        # Skin conditions as a comma-separated string
                fake.sentence(nb_words=6),          # Other notes
                fake.sentence(nb_words=4)           # Desired improvement
            )
            for _ in range(100)
        ]
        cursor.executemany("""
        INSERT INTO client_health_info (client_id, allergies, health_conditions, medications, treatment_areas, current_products, skin_conditions, other_notes, desired_improvement)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, mock_health_info)


    # Check if data already exists in the appointments table
    cursor.execute("SELECT COUNT(*) FROM appointments")
    if cursor.fetchone()[0] == 0:
        # Generate 100 mock appointments
        mock_appointments = [
            (
                fake.random_int(min=1, max=100),  # client_id (randomly assign to a client)
                fake.date_this_year().strftime("%m/%d/%Y"),  # Random date within this year
                fake.random_element(["Facial", "Electrolysis", "Waxing"]),
                fake.sentence(nb_words=5),  # Random treatment description
                f"${fake.random_int(min=30, max=500)}.00",  # Random price
                fake.random_element(["No"]),  # Photos taken
                fake.sentence(nb_words=10)  # Random treatment notes

            )
            for _ in range(1000)
        ]
        cursor.executemany("""
        INSERT INTO appointments (client_id, date, type, treatment, price, photos_taken, treatment_notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
                           
        """, mock_appointments)
