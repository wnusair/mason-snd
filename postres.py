import os
import psycopg2
import sqlite3

# Get the database URL from the environment variable
database_url = os.environ['DATABASE_URL']

# Change the URL to use Neon's connection pooler if necessary
database_url = database_url.replace('.us-east-2', '-pooler.us-east-2')

try:
    # Connect to the Neon PostgreSQL database
    conn = psycopg2.connect(database_url)
    cur = conn.cursor()

    # Connect to a new SQLite database file
    sqlite_conn = sqlite3.connect("exported_database.db")
    sqlite_cursor = sqlite_conn.cursor()

    # Fetch all table names from the PostgreSQL database
    cur.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='public';"
    )
    tables = cur.fetchall()

    # Loop through each table and export the data to the SQLite database
    for table in tables:
        table_name = table[0]

        # Fetch the column names for the table
        cur.execute(f"SELECT * FROM {table_name} LIMIT 0")
        column_names = [desc[0] for desc in cur.description]

        # Quote column names to handle reserved keywords
        column_names_quoted = [f'"{name}"' for name in column_names]
        create_table_query = f'CREATE TABLE "{table_name}" ({", ".join(column_names_quoted)});'
        sqlite_cursor.execute(create_table_query)

        # Fetch all data from the current table
        cur.execute(f"SELECT * FROM {table_name}")
        rows = cur.fetchall()

        # Insert the data into the SQLite table
        placeholders = ", ".join(["?"] * len(column_names))
        insert_query = f'INSERT INTO "{table_name}" VALUES ({placeholders});'
        sqlite_cursor.executemany(insert_query, rows)

    # Commit the changes and close the SQLite connection
    sqlite_conn.commit()
    sqlite_conn.close()

finally:
    # Close the PostgreSQL connection
    cur.close()
    conn.close()

print("Database exported successfully to exported_database.db")
