"""Direct SQLite migration — adds new columns/tables for NGO/alerts features."""
import sqlite3
import sys

DB_PATH = "ghostnet_demo.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# --- Detections: add incident columns ---
cur.execute("PRAGMA table_info(detections)")
existing_cols = {row[1] for row in cur.fetchall()}
print(f"Existing detection columns: {existing_cols}")

incident_cols = {
    "incident_status": "TEXT DEFAULT NULL",
    "assigned_to": "TEXT DEFAULT NULL",
    "assigned_team": "TEXT DEFAULT NULL",
    "verification_notes": "TEXT DEFAULT NULL",
    "verified_by": "TEXT DEFAULT NULL",
    "verified_at": "TIMESTAMP DEFAULT NULL",
}
for col, defn in incident_cols.items():
    if col not in existing_cols:
        cur.execute(f"ALTER TABLE detections ADD COLUMN {col} {defn}")
        print(f"  [ADD] detections.{col}")

# --- Users table ---
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
if not cur.fetchone():
    cur.execute("""
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            full_name TEXT DEFAULT '',
            organization TEXT DEFAULT '',
            role TEXT DEFAULT 'responder',
            phone TEXT DEFAULT '',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("[CREATE] users")

# --- Incident actions table ---
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='incident_actions'")
if not cur.fetchone():
    cur.execute("""
        CREATE TABLE incident_actions (
            id TEXT PRIMARY KEY,
            detection_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            user_name TEXT DEFAULT '',
            organization TEXT DEFAULT '',
            action TEXT NOT NULL,
            previous_status TEXT DEFAULT '',
            new_status TEXT DEFAULT '',
            assigned_team TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("[CREATE] incident_actions")

# --- Ecological alerts table ---
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ecological_alerts'")
if not cur.fetchone():
    cur.execute("""
        CREATE TABLE ecological_alerts (
            id TEXT PRIMARY KEY,
            detection_id TEXT NOT NULL,
            external_id TEXT DEFAULT '',
            alert_type TEXT DEFAULT 'protected_area',
            severity TEXT DEFAULT 'MEDIUM',
            status TEXT DEFAULT 'active',
            headline TEXT DEFAULT '',
            details TEXT DEFAULT '',
            region_name TEXT DEFAULT '',
            feature_type TEXT DEFAULT '',
            species_at_risk TEXT DEFAULT '[]',
            distance_km REAL DEFAULT 0.0,
            estimated_impact_hours REAL DEFAULT 0.0,
            impact_point_geometry TEXT DEFAULT '{}',
            recommended_action TEXT DEFAULT '',
            source_citation TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("[CREATE] ecological_alerts")

conn.commit()
conn.close()
print("\nMigration complete!")
