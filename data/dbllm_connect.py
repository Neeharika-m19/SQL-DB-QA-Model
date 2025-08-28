import sqlite3

# Connect to your SQLite database
con = sqlite3.connect('db_llm.sqlite3')

# Create a cursor
cur = con.cursor()

# Create User table
cur.execute("""
    CREATE TABLE IF NOT EXISTS User (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        password TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

# Create Connection table
cur.execute("""
    CREATE TABLE IF NOT EXISTS Connection (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        db_user TEXT,
        db_password TEXT,
        db_host TEXT,
        db_port INTEGER,
        db_type TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        connection_name TEXT,
        FOREIGN KEY (user_id) REFERENCES User(id)
    )
    """)

# Create Queries table
cur.execute("""
    CREATE TABLE IF NOT EXISTS Queries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        connection_id INTEGER,
        query_key TEXT,
        FOREIGN KEY (user_id) REFERENCES User(id),
        FOREIGN KEY (connection_id) REFERENCES Connection(id)
    )
    """)

# Commit changes
con.commit()

print("Tables created inside 'db_llm.sqlite3'")

# Optionally: insert Admin user
cur.execute("""
    INSERT INTO User (name, email, password)
    VALUES ('Admin', 'admin932@gmail.com', 'password')
    """)

con.commit()
print("Admin user inserted into 'User' table.")

# Close the connection
con.close()