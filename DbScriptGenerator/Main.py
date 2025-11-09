import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import re
import os

# --- Configuration: Common GaussDB Data Types ---
GAUSSDB_DATATYPES = [
    "nvarchar2", "varchar", "char", "text", "clob",
    "numeric", "decimal", "integer", "bigint", "smallint",
    "real", "double precision", "boolean",
    "date", "time", "timestamp", "datea"
]

NULLABILITY_OPTIONS = ["NULL", "NOT NULL"]

# --- Global variable to track editing state ---
editing_item_id = None


# --- Core Functions ---

def handle_comment_tab(event):
    """Inserts 4 spaces instead of a tab character."""
    event.widget.insert("insert", "    ")
    return "break"  # Prevents default tab behavior


def browse_output_location():
    """Opens a dialog to select the output project directory."""
    directory = filedialog.askdirectory()
    if directory:
        output_location_entry.delete(0, "end")
        output_location_entry.insert(0, directory)


def reset_to_add_mode():
    """Resets the input fields and buttons to 'Add' mode."""
    global editing_item_id
    editing_item_id = None

    # Clear input fields
    col_name_entry.delete(0, "end")
    datatype_combo.set("")
    size_entry.delete(0, "end")
    nullability_combo.set("NULL")  # Reset to default
    comment_text.delete("1.0", "end")

    # Reset buttons
    add_button.config(text="Add Column(s) to List", command=add_columns_to_list)
    cancel_edit_button.grid_remove()  # Hide the cancel button
    col_name_entry.focus()


def add_columns_to_list():
    """Adds one or more columns from the input fields to the treeview."""
    col_name_str = col_name_entry.get().strip()
    col_type_str = datatype_combo.get().strip()
    col_size_str = size_entry.get().strip()
    col_null_str = nullability_combo.get().strip()
    col_comment_str = comment_text.get("1.0", "end-1c").strip()

    if not col_name_str:
        messagebox.showwarning("Input Error", "Column Name(s) are required.")
        return
    if not col_type_str:
        messagebox.showwarning("Input Error", "Data Type(s) are required.")
        return
    if not col_null_str:
        messagebox.showwarning("Input Error", "Nullability is required.")
        return

    # Split all inputs by comma
    col_names = [name.strip() for name in col_name_str.split(',') if name.strip()]
    data_types = [dt.strip() for dt in col_type_str.split(',')]
    sizes = [s.strip() for s in col_size_str.split(',')]
    nullabilities = [n.strip().upper() for n in col_null_str.split(',')]
    comments = [c.strip() for c in col_comment_str.split(',')]

    n = len(col_names)
    if n == 0:
        messagebox.showwarning("Input Error", "Please enter at least one valid column name.")
        return

    # --- Helper function to validate and broadcast/map lists ---
    def get_attribute_list(attr_list, attr_name):
        """Validates list length and returns a final list of size 'n'."""
        if len(attr_list) == 1:
            return [attr_list[0]] * n
        elif len(attr_list) == n:
            return attr_list
        else:
            messagebox.showwarning("Input Error",
                                   f"List mismatch: You provided {n} column names, but {len(attr_list)} {attr_name}. "
                                   f"Attribute lists must have 1 element (to apply to all) or {n} elements (for 1-to-1 mapping).")
            return None

    # --- Validate and get final lists ---
    final_data_types = get_attribute_list(data_types, "Data Types")
    if final_data_types is None: return

    final_sizes = get_attribute_list(sizes, "Sizes")
    if final_sizes is None: return

    final_nullabilities = get_attribute_list(nullabilities, "Nullabilities")
    if final_nullabilities is None: return

    final_comments = get_attribute_list(comments, "Comments")
    if final_comments is None: return

    # --- Add items to tree ---
    for i in range(n):
        col_name = col_names[i]
        col_type = final_data_types[i]
        col_size = final_sizes[i]
        col_null = final_nullabilities[i]
        col_comment = final_comments[i]

        if not col_type:
            messagebox.showwarning("Input Error",
                                   f"Data Type for column '{col_name}' (item {i + 1}) is empty.")
            return
        if col_null not in NULLABILITY_OPTIONS:
            messagebox.showwarning("Input Error",
                                   f"Nullability for column '{col_name}' (item {i + 1}) must be 'NULL' or 'NOT NULL'.")
            return

        columns_tree.insert("", "end", values=(col_name, col_type, col_size, col_null, col_comment))

    # --- Don't reset fields ---


def update_selected_column():
    """Updates the currently selected treeview item with data from the inputs."""
    global editing_item_id
    if not editing_item_id:
        return

    col_name = col_name_entry.get().strip().split(',')[0]
    col_type = datatype_combo.get().strip().split(',')[0]
    col_size = size_entry.get().strip().split(',')[0]
    col_null = nullability_combo.get().strip().split(',')[0].upper()
    col_comment = comment_text.get("1.0", "end-1c").strip().split(',')[0]

    if not col_name or not col_type:
        messagebox.showwarning("Input Error", "Column Name and Data Type are required.")
        return
    if col_null not in NULLABILITY_OPTIONS:
        messagebox.showwarning("Input Error", "Nullability must be 'NULL' or 'NOT NULL'.")
        return

    columns_tree.item(editing_item_id, values=(col_name, col_type, col_size, col_null, col_comment))
    reset_to_add_mode()  # Update still resets to add mode


def load_selected_for_editing(event):
    """Loads a double-clicked item's data into the input fields for editing."""
    global editing_item_id
    selected_items = columns_tree.selection()
    if not selected_items:
        return

    item_id = selected_items[0]
    editing_item_id = item_id

    col_name, col_type, col_size, col_null, col_comment = columns_tree.item(item_id, 'values')

    col_name_entry.delete(0, "end")
    col_name_entry.insert(0, col_name)
    datatype_combo.set(col_type)
    size_entry.delete(0, "end")
    size_entry.insert(0, col_size)
    nullability_combo.set(col_null)
    comment_text.delete("1.0", "end")
    comment_text.insert("1.0", col_comment)

    add_button.config(text="Update Selected Column", command=update_selected_column)
    cancel_edit_button.grid(row=5, column=0, sticky="w", padx=5, pady=5)


def remove_selected_column():
    """Removes the selected column from the treeview list."""
    selected_items = columns_tree.selection()
    if not selected_items:
        messagebox.showinfo("Selection", "Please select a column to remove from the list.")
        return

    for item in selected_items:
        columns_tree.delete(item)

    if editing_item_id in selected_items:
        reset_to_add_mode()


# --- SQL Generation Helpers (Refactored for J-Table) ---

def build_alter_statements(target_table_name):
    """Builds the ADD, COMMENT, and DROP statements for a given table name."""
    add_clauses, comment_sqls, drop_clauses = [], [], []
    sql_script_parts = []

    # 1. Get Columns to ADD
    all_add_columns = columns_tree.get_children()
    for item_id in all_add_columns:
        col_name, col_type, col_size, col_null, col_comment = columns_tree.item(item_id, 'values')
        full_type = col_type
        if col_size:
            full_type += col_size
        add_clauses.append(f"ADD {col_name} {full_type} {col_null}")

        if col_comment:
            safe_comment = col_comment.replace("\t", "    ")
            escaped_comment = safe_comment.replace("'", "''")
            comment_sqls.append(f"COMMENT ON COLUMN {target_table_name}.{col_name} IS '{escaped_comment}';")

    # 2. Get Columns to DROP
    drop_cols_str = drop_columns_entry.get().strip()
    if drop_cols_str:
        drop_names = [name.strip() for name in drop_cols_str.split(',') if name.strip()]
        for name in drop_names:
            drop_clauses.append(f"DROP COLUMN {name}")

    # 3. Assemble
    if add_clauses:
        add_sql = f"ALTER TABLE {target_table_name}\n"
        add_sql += ",\n".join(add_clauses)
        add_sql += ";"
        sql_script_parts.append(add_sql)

    if comment_sqls:
        comment_sql_block = "\n".join(comment_sqls)
        sql_script_parts.append(comment_sql_block)

    if drop_clauses:
        drop_sql = f"ALTER TABLE {target_table_name}\n"
        drop_sql += ",\n".join(drop_clauses)
        drop_sql += ";"
        sql_script_parts.append(drop_sql)

    return sql_script_parts


def build_rollback_statements(target_table_name):
    """Builds the inverse (rollback) statements for a given table name."""
    sql_script_parts = []

    # 1. Rollback for "Columns to ADD" -> DROP COLUMN
    all_add_columns = columns_tree.get_children()
    drop_clauses = []
    if all_add_columns:
        for item_id in all_add_columns:
            col_name = columns_tree.item(item_id, 'values')[0]
            drop_clauses.append(f"DROP COLUMN {col_name}")

        if drop_clauses:
            drop_sql = f"ALTER TABLE {target_table_name}\n"
            drop_sql += ",\n".join(drop_clauses)
            drop_sql += ";"
            sql_script_parts.append(drop_sql)

    # 2. Rollback for "Columns to DROP" -> ADD COLUMN (with placeholders)
    drop_cols_str = drop_columns_entry.get().strip()
    add_clauses = []
    if drop_cols_str:
        drop_names = [name.strip() for name in drop_cols_str.split(',') if name.strip()]
        for name in drop_names:
            add_clauses.append(f"ADD {name} /*<data_type>*/ /*<NULL|NOT NULL>*/")

        if add_clauses:
            add_sql = f"-- NOTE: You must fill in the <data_type> and <nullability> for these columns.\n"
            add_sql += f"ALTER TABLE {target_table_name}\n"
            add_sql += ",\n".join(add_clauses)
            add_sql += ";"
            sql_script_parts.append(add_sql)

    return sql_script_parts


def modify_trigger_code(code, trigger_type, table_name, cols_to_add, cols_to_drop, indent="    "):
    """
    Modifies trigger code to add or remove columns.
    Returns a tuple: (modified_sql, drop_trigger_sql)
    """
    if not code.strip():
        return ("", "")  # Return empty tuple if no code

    modified_code = code

    # --- 1. Handle Dropped Columns ---
    for col in cols_to_drop:
        # Regex for column list: optional comma, whitespace, column name, optional comma, whitespace, end-of-line
        col_list_regex = re.compile(r'^\s*,\s*' + re.escape(col) + r'\b\s*$', flags=re.IGNORECASE | re.MULTILINE)
        modified_code = col_list_regex.sub('', modified_code)
        col_list_regex_2 = re.compile(r'^\s*' + re.escape(col) + r'\b,?\s*$\n', flags=re.IGNORECASE | re.MULTILINE)
        modified_code = col_list_regex_2.sub('', modified_code)

        # Regex for values list: same, but with (old|new)
        val_list_regex = re.compile(r'^\s*,\s*(old|new)\.' + re.escape(col) + r'\b\s*$',
                                    flags=re.IGNORECASE | re.MULTILINE)
        modified_code = val_list_regex.sub('', modified_code)
        val_list_regex_2 = re.compile(r'^\s*(old|new)\.' + re.escape(col) + r'\b,?\s*$\n',
                                      flags=re.IGNORECASE | re.MULTILINE)
        modified_code = val_list_regex_2.sub('', modified_code)

    # --- 2. Handle Added Columns ---
    if cols_to_add:
        col_list_add = '\n' + '\n'.join([f'{indent}{indent}{c},' for c in cols_to_add])
        val_list_add_i = '\n' + '\n'.join([f'{indent}{indent}new.{c},' for c in cols_to_add])
        val_list_add_d = '\n' + '\n'.join([f'{indent}{indent}old.{c},' for c in cols_to_add])
        val_list_add_u_b = '\n' + '\n'.join([f'{indent}{indent}old.{c},' for c in cols_to_add])
        val_list_add_u_a = '\n' + '\n'.join([f'{indent}{indent}new.{c},' for c in cols_to_add])

        col_list_anchor = re.compile(r'(^\s*BA_IND,\s*$)', flags=re.IGNORECASE | re.MULTILINE)

        if trigger_type == 'i':  # Insert
            val_list_anchor = re.compile(r"(^\s*'I',\s*$)", flags=re.IGNORECASE | re.MULTILINE)
            modified_code = col_list_anchor.sub(r'\1' + col_list_add, modified_code)
            modified_code = val_list_anchor.sub(r'\1' + val_list_add_i, modified_code)
        elif trigger_type == 'd':  # Delete
            val_list_anchor = re.compile(r"(^\s*'D',\s*$)", flags=re.IGNORECASE | re.MULTILINE)
            modified_code = col_list_anchor.sub(r'\1' + col_list_add, modified_code)
            modified_code = val_list_anchor.sub(r'\1' + val_list_add_d, modified_code)
        elif trigger_type == 'u':  # Update
            val_list_anchor_b = re.compile(r"(^\s*'B',\s*$)", flags=re.IGNORECASE | re.MULTILINE)
            val_list_anchor_a = re.compile(r"(^\s*'A',\s*$)", flags=re.IGNORECASE | re.MULTILINE)
            modified_code = col_list_anchor.sub(r'\1' + col_list_add, modified_code)
            modified_code = val_list_anchor_b.sub(r'\1' + val_list_add_u_b, modified_code, count=1)
            modified_code = val_list_anchor_a.sub(r'\1' + val_list_add_u_a, modified_code, count=1)

    # --- 3. Generate DROP statement ---
    drop_statement = ""
    # Look for CREATE TRIGGER "tji_tfs_cf_scheme" or CREATE TRIGGER tji_tfs_cf_scheme
    match = re.search(r'CREATE TRIGGER\s+["\']?(\w+)["\']?', code, re.IGNORECASE)
    if match:
        trigger_name = match.group(1)
        drop_statement = f'DROP TRIGGER IF EXISTS {trigger_name} on {table_name};'

    return (modified_code, drop_statement)


# --- File I/O Helper ---
def write_sql_file(file_path, content_parts):
    """Joins content parts and writes to a file."""
    # Filter out empty strings
    non_empty_parts = [part for part in content_parts if part and part.strip()]
    if not non_empty_parts:
        # Write an empty file if no content
        content = "-- No SQL content generated for this file. --"
    else:
        content = "\n\n".join(non_empty_parts)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


# --- NEW: Main "Generate All Files" Function ---
def generate_all_sql_files():
    """Generates all four SQL files based on the user's input."""

    # 1. Get Table and Path
    table_name = table_name_entry.get().strip().upper()
    base_output_path = output_location_entry.get().strip()

    if not table_name:
        messagebox.showwarning("Input Error", "Please enter a Table Name.")
        return
    if not base_output_path:
        messagebox.showwarning("Input Error", "Please select an Output Project Location.")
        return

    try:
        # --- MODIFICATION: Create the new directory structure ---
        ddl_path = os.path.join(base_output_path, "pics3_database", "deployment", "next_sit_release", "ddl")
        rollback_ddl_path = os.path.join(base_output_path, "pics3_database", "deployment", "next_sit_release",
                                         "rollback", "ddl")

        os.makedirs(ddl_path, exist_ok=True)
        os.makedirs(rollback_ddl_path, exist_ok=True)
    except Exception as e:
        messagebox.showerror("File Error", f"Could not create directories:\n{e}")
        return

    # 2. Get columns to add/drop
    cols_to_add = [columns_tree.item(item_id, 'values')[0] for item_id in columns_tree.get_children()]
    drop_cols_str = drop_columns_entry.get().strip()
    cols_to_drop = [name.strip() for name in drop_cols_str.split(',') if name.strip()]

    # 3. Get original trigger code
    original_tji = tji_text.get("1.0", "end-1c")
    original_tju = tju_text.get("1.0", "end-1c")
    original_tjd = tjd_text.get("1.0", "end-1c")

    # 4. Process triggers
    (mod_tji, drop_tji) = modify_trigger_code(original_tji, 'i', table_name, cols_to_add, cols_to_drop)
    (mod_tju, drop_tju) = modify_trigger_code(original_tju, 'u', table_name, cols_to_add, cols_to_drop)
    (mod_tjd, drop_tjd) = modify_trigger_code(original_tjd, 'd', table_name, cols_to_add, cols_to_drop)

    # --- 5. Build and Write Files ---
    try:
        # --- File 1: [table_name].sql (in .../ddl) ---
        file_1_path = os.path.join(ddl_path, f"{table_name}.sql")
        alter_parts = build_alter_statements(table_name)
        trigger_parts = [drop_tji, mod_tji, drop_tju, mod_tju, drop_tjd, mod_tjd]
        write_sql_file(file_1_path, alter_parts + trigger_parts)

        # --- File 2: [table_name]_rollback.sql (in .../rollback/ddl) ---
        file_2_path = os.path.join(rollback_ddl_path, f"{table_name}_rollback.sql")
        rollback_parts = build_rollback_statements(table_name)
        original_trigger_parts = [original_tji, original_tju, original_tjd]
        write_sql_file(file_2_path, rollback_parts + original_trigger_parts)

        # --- File 3: J_[table_name].sql (in .../ddl) ---
        file_3_path = os.path.join(ddl_path, f"J_{table_name}.sql")
        j_alter_parts = []
        if alter_j_table_var.get():
            j_alter_parts = build_alter_statements(f"J_{table_name}")
        write_sql_file(file_3_path, j_alter_parts)  # "no triggers"

        # --- File 4: J_[table_name]_rollback.sql (in .../rollback/ddl) ---
        file_4_path = os.path.join(rollback_ddl_path, f"J_{table_name}_rollback.sql")
        j_rollback_parts = []
        if alter_j_table_var.get():
            j_rollback_parts = build_rollback_statements(f"J_{table_name}")
        write_sql_file(file_4_path, j_rollback_parts)  # "no triggers"

    except Exception as e:
        messagebox.showerror("File Error", f"Could not write files:\n{e}")
        return

    messagebox.showinfo("Success", f"Successfully generated 4 files in:\n{ddl_path}\nand:\n{rollback_ddl_path}")


# --- GUI Setup ---
root = tk.Tk()
root.title("GaussDB ALTER TABLE Generator")
root.geometry("900x950")

alter_j_table_var = tk.BooleanVar(value=True)

# --- Top Frame: Table Name ---
table_frame = ttk.Frame(root, padding="10")
table_frame.pack(fill="x")
ttk.Label(table_frame, text="Table Name:", width=15).pack(side="left")
table_name_entry = ttk.Entry(table_frame)
table_name_entry.pack(fill="x", expand=True, side="left")

j_table_check = ttk.Checkbutton(table_frame, text="Alter J-Table (J_...)", variable=alter_j_table_var, onvalue=True,
                                offvalue=False)
j_table_check.pack(side="left", padx=10)

# --- Input Frame: Column Details ---
input_frame = ttk.LabelFrame(root, text="Add / Edit Column", padding="10")
input_frame.pack(fill="x", padx=10)
# (Input fields: col_name, datatype, size, nullability, comment)
ttk.Label(input_frame, text="Column Name(s) (comma-separated):").grid(row=0, column=0, sticky="w", padx=5, pady=2)
col_name_entry = ttk.Entry(input_frame)
col_name_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
ttk.Label(input_frame, text="Data Type(s) (comma-separated):").grid(row=1, column=0, sticky="w", padx=5, pady=2)
datatype_combo = ttk.Combobox(input_frame, values=GAUSSDB_DATATYPES)
datatype_combo.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
ttk.Label(input_frame, text="Size(s) (e.g., (5),,(10)):").grid(row=2, column=0, sticky="w", padx=5, pady=2)
size_entry = ttk.Entry(input_frame)
size_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=2)
ttk.Label(input_frame, text="Nullability (comma-separated):").grid(row=3, column=0, sticky="w", padx=5, pady=2)
nullability_combo = ttk.Combobox(input_frame, values=NULLABILITY_OPTIONS)
nullability_combo.grid(row=3, column=1, sticky="ew", padx=5, pady=2)
nullability_combo.set("NULL")
ttk.Label(input_frame, text="Comment(s) (comma-separated):").grid(row=4, column=0, sticky="nw", padx=5, pady=2)
comment_text = tk.Text(input_frame, height=3, width=40)
comment_text.grid(row=4, column=1, sticky="ew", padx=5, pady=2)
comment_text.bind("<Tab>", handle_comment_tab)
button_frame = ttk.Frame(input_frame)
button_frame.grid(row=5, column=1, sticky="e", pady=5)
cancel_edit_button = ttk.Button(button_frame, text="Cancel Edit", command=reset_to_add_mode)
cancel_edit_button.pack(side="left", padx=5)
cancel_edit_button.pack_forget()
add_button = ttk.Button(button_frame, text="Add Column(s) to List", command=add_columns_to_list)
add_button.pack(side="left")
input_frame.columnconfigure(1, weight=1)

# --- Treeview Frame: List of Columns to Add ---
tree_frame = ttk.LabelFrame(root, text="Columns to ADD (Double-click to edit)", padding=10)
tree_frame.pack(fill="both", expand=True, padx=10)
tree_columns = ("Column Name", "Data Type", "Size", "Nullability", "Comment")
columns_tree = ttk.Treeview(tree_frame, columns=tree_columns, show="headings")
for col in tree_columns:
    columns_tree.heading(col, text=col)
columns_tree.column("Column Name", width=150)
columns_tree.column("Data Type", width=100)
columns_tree.column("Size", width=50)
columns_tree.column("Nullability", width=70)
columns_tree.column("Comment", width=300)
scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=columns_tree.yview)
columns_tree.configure(yscrollcommand=scrollbar.set)
scrollbar.pack(side="right", fill="y")
columns_tree.pack(side="left", fill="both", expand=True)
columns_tree.bind("<Double-1>", load_selected_for_editing)
remove_button = ttk.Button(tree_frame, text="Remove Selected (from list)", command=remove_selected_column)
remove_button.pack(side="right", fill="y", padx=5)

# --- Drop Columns Frame ---
drop_frame = ttk.LabelFrame(root, text="Columns to DROP", padding="10")
drop_frame.pack(fill="x", padx=10, pady=5)
ttk.Label(drop_frame, text="Columns to drop (comma-separated):").pack(side="left", padx=5)
drop_columns_entry = ttk.Entry(drop_frame)
drop_columns_entry.pack(fill="x", expand=True, side="left")

# --- Trigger Code Frame ---
trigger_frame = ttk.LabelFrame(root, text="Trigger Code (Optional)", padding="10")
trigger_frame.pack(fill="x", padx=10, pady=5)
trigger_paned_window = ttk.PanedWindow(trigger_frame, orient="horizontal")
trigger_paned_window.pack(fill="x", expand=True)
# TJI
tji_frame = ttk.Frame(trigger_paned_window, padding=5)
ttk.Label(tji_frame, text="TJI Code:").pack(anchor="w")
tji_text = scrolledtext.ScrolledText(tji_frame, wrap="word", height=10, width=30)
tji_text.pack(fill="both", expand=True)
trigger_paned_window.add(tji_frame, weight=1)
# TJU
tju_frame = ttk.Frame(trigger_paned_window, padding=5)
ttk.Label(tju_frame, text="TJU Code:").pack(anchor="w")
tju_text = scrolledtext.ScrolledText(tju_frame, wrap="word", height=10, width=30)
tju_text.pack(fill="both", expand=True)
trigger_paned_window.add(tju_frame, weight=1)
# TJD
tjd_frame = ttk.Frame(trigger_paned_window, padding=5)
ttk.Label(tjd_frame, text="TJD Code:").pack(anchor="w")
tjd_text = scrolledtext.ScrolledText(tjd_frame, wrap="word", height=10, width=30)
tjd_text.pack(fill="both", expand=True)
trigger_paned_window.add(tjd_frame, weight=1)

# --- Output & Generate Frame ---
output_frame = ttk.LabelFrame(root, text="Output", padding="10")
output_frame.pack(fill="x", padx=10, pady=5)

ttk.Label(output_frame, text="Output Project Location:").pack(side="left", padx=5)
output_location_entry = ttk.Entry(output_frame)
output_location_entry.pack(fill="x", expand=True, side="left", padx=5)
browse_button = ttk.Button(output_frame, text="Browse", command=browse_output_location)
browse_button.pack(side="left", padx=5)

# --- Single Generate Button ---
generate_button_frame = ttk.Frame(root, padding="10")
generate_button_frame.pack()

generate_all_button = ttk.Button(generate_button_frame, text="Generate All SQL Files", command=generate_all_sql_files,
                                 style="Accent.TButton")
generate_all_button.pack(pady=10)

# Add a style for the accent button
style = ttk.Style()
style.configure("Accent.TButton", font=("Arial", 10, "bold"))

# --- Start GUI ---
root.mainloop()