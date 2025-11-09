import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import psycopg2  # Make sure to install with: pip install psycopg2-binary
import datetime


# --- Helper Functions ---

def format_value(val):
    """
    Properly formats a Python value for inclusion in a SQL INSERT statement.
    """
    if val is None:
        return "NULL"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, datetime.datetime):
        # Format as 'YYYY-MM-DD HH:MI:SS.mmm'
        return f"'{val.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}'"
    if isinstance(val, str):
        # Escape single quotes by doubling them up
        return f"'{val.replace("'", "''")}'"
    # Fallback for other types (like bool)
    return f"'{str(val)}'"


def format_identifier(col_name):
    """
    Wraps column names in double quotes to handle reserved words (like "read").
    """
    return f'"{col_name}"'


def fetch_and_format_inserts(cursor, table_name, func_id_list):
    """
    Fetches data for the given IDs and formats it as a SQL INSERT script.
    """
    script_lines = []

    try:
        # Use = ANY(%s) which is an efficient way to handle an IN clause
        query = f"SELECT * FROM {table_name} WHERE func_id = ANY(%s) ORDER BY func_id"
        cursor.execute(query, (func_id_list,))

        rows = cursor.fetchall()
        if not rows:
            script_lines.append(f"-- No data found in {table_name} for the given IDs.\n")
            return "".join(script_lines)

        # Get column names from the cursor description
        col_names = [format_identifier(desc[0]) for desc in cursor.description]

        # Start the INSERT statement
        script_lines.append(f"INSERT INTO {table_name}\n({', '.join(col_names)})\nVALUES\n")

        # Process each row
        for i, row in enumerate(rows):
            formatted_values = [format_value(val) for val in row]
            line_end = ");\n" if (i == len(rows) - 1) else "),\n"
            script_lines.append(f"({', '.join(formatted_values)}{line_end}")

    except (Exception, psycopg2.DatabaseError) as error:
        messagebox.showerror(f"Database Error ({table_name})", f"Error: {error}")
        return None  # Indicate failure

    return "".join(script_lines)


# --- Main Application Logic ---

def generate_scripts():
    """
    Main function triggered by the 'Generate' button.
    """
    # 1. Get all inputs from the GUI
    db_host = entry_host.get()
    db_port = entry_port.get()
    db_name = entry_db.get()
    db_user = entry_user.get()
    db_pass = entry_pass.get()
    id_text = text_ids.get("1.0", "end-1c")

    # 2. Validate inputs
    if not all([db_host, db_port, db_name, db_user, db_pass, id_text]):
        messagebox.showwarning("Input Error",
                               "Please fill in all database fields and provide at least one Function ID.")
        return

    # 3. Process the function IDs
    # Split by lines, strip whitespace, and filter out empty lines
    func_ids = [fid.strip().upper() for fid in id_text.splitlines() if fid.strip()]

    if not func_ids:
        messagebox.showwarning("Input Error", "No valid Function IDs entered.")
        return

    # Format for SQL 'IN' clause (e.g., 'ID1', 'ID2')
    formatted_id_list = ', '.join([f"'{fid}'" for fid in func_ids])

    # 4. Generate the DELETE script (this can be done without a DB connection)
    delete_script = f"""-- Delete data from func
DELETE FROM func WHERE func_id IN ({formatted_id_list});

-- Delete data from func_role_priv
DELETE FROM func_role_priv WHERE func_id IN ({formatted_id_list});
"""

    # 5. Generate the BACKUP script (requires DB connection)
    backup_script_parts = [f"-- Backup script for {len(func_ids)} function ID(s)\n\n"]
    conn = None
    try:
        # Connect to the database
        # This call correctly takes the values from the GUI fields
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_pass,
            gssencmode = 'disable',
            sslmode='prefer'
        )
        cursor = conn.cursor()

        # Fetch and format data for 'func' table
        func_inserts = fetch_and_format_inserts(cursor, 'func', func_ids)
        if func_inserts is None: return  # Error was already shown
        backup_script_parts.append(func_inserts)
        backup_script_parts.append("\n")

        # Fetch and format data for 'func_role_priv' table
        frp_inserts = fetch_and_format_inserts(cursor, 'func_role_priv', func_ids)
        if frp_inserts is None: return  # Error was already shown
        backup_script_parts.append(frp_inserts)

        # Close connection
        cursor.close()

    except (Exception, psycopg2.DatabaseError) as error:
        messagebox.showerror("Connection Error", f"Could not connect to database.\nError: {error}")
        return
    finally:
        if conn:
            conn.close()

    backup_script = "".join(backup_script_parts)

    # 6. Prompt user to save the files
    file_path = filedialog.asksaveasfilename(
        title="Save SQL Scripts As...",
        defaultextension=".sql",
        filetypes=[("SQL Script", "*.sql"), ("All Files", "*.*")]
    )

    if not file_path:
        # User cancelled the save dialog
        return

    # Determine the two filenames
    # (e.g., if user chose 'my_backup', files will be 'my_backup_delete.sql' and 'my_backup_backup.sql')
    if file_path.endswith('.sql'):
        base_name = file_path[:-4]
    else:
        base_name = file_path

    delete_file = f"{base_name}_delete.sql"
    backup_file = f"{base_name}_backup.sql"

    try:
        # Write the DELETE script
        with open(delete_file, "w", encoding="utf-8") as f:
            f.write(delete_script)

        # Write the BACKUP script
        with open(backup_file, "w", encoding="utf-8") as f:
            f.write(backup_script)

        messagebox.showinfo("Success!", f"Scripts generated successfully:\n\n1. {delete_file}\n2. {backup_file}")

    except Exception as e:
        messagebox.showerror("File Error", f"Could not write files.\nError: {e}")


# --- GUI Setup ---
root = tk.Tk()
root.title("SQL Script Generator")

frame = ttk.Frame(root, padding="10")
frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

# --- Database Connection Frame ---
db_frame = ttk.LabelFrame(frame, text="Database Connection (PostgreSQL/GaussDB)", padding="10")
db_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

# Host
ttk.Label(db_frame, text="Host:").grid(row=0, column=0, sticky=tk.W, padx=5)
entry_host = ttk.Entry(db_frame, width=20)
entry_host.insert(0, "localhost")
entry_host.grid(row=0, column=1, padx=5)

# Port
ttk.Label(db_frame, text="Port:").grid(row=0, column=2, sticky=tk.W, padx=5)
entry_port = ttk.Entry(db_frame, width=8)
entry_port.insert(0, "8000")  # <-- UPDATED from 5432
entry_port.grid(row=0, column=3, padx=5)

# Database
ttk.Label(db_frame, text="Database:").grid(row=1, column=0, sticky=tk.W, padx=5)
entry_db = ttk.Entry(db_frame, width=20)
entry_db.grid(row=1, column=1, padx=5, pady=5)
entry_db.insert(0, "pics_test_merge")  # <-- ADDED this line

# User
ttk.Label(db_frame, text="User:").grid(row=2, column=0, sticky=tk.W, padx=5)
entry_user = ttk.Entry(db_frame, width=20)
entry_user.grid(row=2, column=1, padx=5, pady=5)

# Password
ttk.Label(db_frame, text="Password:").grid(row=2, column=2, sticky=tk.W, padx=5)
entry_pass = ttk.Entry(db_frame, width=20, show="*")
entry_pass.grid(row=2, column=3, padx=5, pady=5)

# --- Function IDs Frame ---
id_frame = ttk.LabelFrame(frame, text="Function IDs", padding="10")
id_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

ttk.Label(id_frame, text="Enter Function IDs (one per line):").grid(row=0, column=0, sticky=tk.W)
text_ids = scrolledtext.ScrolledText(id_frame, width=60, height=10, wrap=tk.WORD)
text_ids.grid(row=1, column=0, pady=5)

# --- Generate Button ---
generate_button = ttk.Button(frame, text="Generate SQL Scripts", command=generate_scripts)
generate_button.grid(row=2, column=0, columnspan=2, pady=10)

# Configure resizing
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)
frame.columnconfigure(0, weight=1)

root.mainloop()