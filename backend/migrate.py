import sqlite3

def upgrade():
    print("Connecting to evodoc.db...")
    conn = sqlite3.connect('evodoc.db')
    cursor = conn.cursor()
    
    try:
        print("Adding 'interactions' column...")
        cursor.execute("ALTER TABLE checks ADD COLUMN interactions TEXT DEFAULT '[]';")
    except sqlite3.OperationalError as e:
        print(f"Skipped adding interactions: {e}")
        
    try:
        print("Adding 'allergy_alerts' column...")
        cursor.execute("ALTER TABLE checks ADD COLUMN allergy_alerts TEXT DEFAULT '[]';")
    except sqlite3.OperationalError as e:
        print(f"Skipped adding allergy_alerts: {e}")

    conn.commit()
    conn.close()
    print("Database upgrade completed successfully.")

if __name__ == "__main__":
    upgrade()
