import tkinter as tk
from tkinter import filedialog, Toplevel, Text, messagebox, ttk, simpledialog
import os
import re


class ConfirmationDialog(Toplevel):
    """Existing modal dialog for Bulk Translation mode."""

    def __init__(self, parent, file_key, eng_val, old_val, new_val):
        super().__init__(parent)
        self.title("Confirm Replacement")
        self.result = False
        self.transient(parent)
        self.grab_set()

        tk.Label(self, text=f"File: {file_key[0]}", wraplength=480, anchor="w").pack(pady=(5, 0), padx=10, fill="x")
        tk.Label(self, text=f"Key: {file_key[1]}").pack(padx=10)
        tk.Label(self, text=f"English: {eng_val}", font=("Arial", 10, "bold")).pack(pady=(5, 10), padx=10)

        diff_frame = tk.Frame(self)
        diff_frame.pack(fill="both", expand=True, padx=10)

        for title, val, bg, col in [("Current (Before)", old_val, "#FFF0F0", 0),
                                    ("New (After)", new_val, "#F0FFF0", 1)]:
            f = tk.Frame(diff_frame)
            tk.Label(f, text=title).pack(anchor="w")
            t = Text(f, height=5, width=30, bg=bg)
            t.pack(fill="both", expand=True)
            t.insert("1.0", val)
            t.config(state="disabled")
            f.grid(row=0, column=col, sticky="nsew", padx=5)

        diff_frame.columnconfigure(0, weight=1)
        diff_frame.columnconfigure(1, weight=1)

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Confirm", command=self.on_confirm, bg="#D4EDDA", width=15).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancel", command=self.on_cancel, width=10).pack(side="right", padx=5)

        self.update_idletasks()  # Update widgets to get correct size

        # Get window width and height
        window_width = self.winfo_reqwidth()
        window_height = self.winfo_reqheight()

        # Get screen width and height
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Calculate center position
        x_coord = (screen_width // 2) - (window_width // 2)
        y_coord = (screen_height // 2) - (window_height // 2)

        # Set the geometry
        self.geometry(f"{window_width}x{window_height}+{x_coord}+{y_coord}")

        self.wait_window()

    def on_confirm(self):
        self.result = True
        self.destroy()

    def on_cancel(self):
        self.destroy()


class TranslatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Properties Translator Tool")
        self.root.geometry("900x700")

        # --- TABS (NOW AT THE TOP) ---
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(10, 5))  # Added top padding

        # Tab 1: Bulk
        self.tab_bulk = tk.Frame(self.notebook)
        self.notebook.add(self.tab_bulk, text="  Auto Replace  ")
        self.init_bulk_tab()

        # Tab 2: Search
        self.tab_search = tk.Frame(self.notebook)
        self.notebook.add(self.tab_search, text="  Manual Replace  ")
        self.init_search_tab()

        # --- SHARED: Log ---
        fr_log = tk.Frame(root)
        fr_log.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        tk.Label(fr_log, text="Log:").pack(anchor="w")
        self.log_text = Text(fr_log, height=8, state="disabled", bg="#f5f5f5")
        self.log_text.pack(fill="both", expand=True)

        # --- Class variables ---
        self.bulk_matches_data = {}  # Stores data for bulk tree items
        self.search_matches_data = {}  # Stores data for search tree items

    def create_path_filter_frame(self, parent_tab):
        """Helper to create the Path and Filter widgets inside a tab."""
        top_frame = tk.Frame(parent_tab)
        top_frame.pack(fill="x", padx=5, pady=5)

        # Path
        fr_path = tk.Frame(top_frame)
        fr_path.pack(fill="x")
        tk.Label(fr_path, text="Project Path:").pack(side="left")
        path_entry = tk.Entry(fr_path)
        path_entry.pack(side="left", fill="x", expand=True, padx=5)
        # We use lambda to pass the specific entry widget to browse_path
        tk.Button(fr_path, text="Browse...", command=lambda: self.browse_path(path_entry)).pack(side="right")

        # Filter
        fr_filter = tk.Frame(top_frame)
        fr_filter.pack(fill="x", pady=(5, 0))
        tk.Label(fr_filter, text="File Filter:   ").pack(side="left")
        filter_entry = tk.Entry(fr_filter)
        filter_entry.pack(side="left", fill="x", expand=True, padx=5)
        tk.Label(fr_filter, text="(e.g. qhs AND (1501 OR 1502))", font=("Arial", 8), fg="gray").pack(side="right")

        ttk.Separator(parent_tab, orient='horizontal').pack(fill='x', pady=10, padx=5)

        return path_entry, filter_entry

    def init_bulk_tab(self):
        # --- Create Path/Filter frame for this tab ---
        self.bulk_path_entry, self.bulk_filter_entry = self.create_path_filter_frame(self.tab_bulk)

        # --- Top frame for translations ---
        fr_top_bulk = tk.Frame(self.tab_bulk)
        fr_top_bulk.pack(fill="x", padx=5, pady=(0, 0))  # Removed top padding

        tk.Label(fr_top_bulk, text="Paste translations (Eng <two spaces> Chi):").pack(anchor="w")
        self.translations_text = Text(fr_top_bulk, height=8)
        self.translations_text.pack(fill="x", pady=5)
        self.translations_text.insert("1.0", "DHB Type  雙重房屋福利類別\nViolated By  違反人士")

        tk.Button(fr_top_bulk, text="Search", command=self.find_bulk_matches,
                  font=("Arial", 11, "bold"), pady=5).pack(pady=5)

        # --- Treeview for bulk results ---
        tk.Label(self.tab_bulk, text="Double-click a row to review and confirm replacement:", fg="gray").pack(
            anchor="w", padx=5)

        tree_frame = tk.Frame(self.tab_bulk)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        cols = ("file", "key", "eng", "old_zh", "new_zh")
        self.bulk_tree = ttk.Treeview(tree_frame, columns=cols, show="headings")
        self.bulk_tree.heading("file", text="Filename")
        self.bulk_tree.heading("key", text="Key")
        self.bulk_tree.heading("eng", text="English Value")
        self.bulk_tree.heading("old_zh", text="Current Chinese")
        self.bulk_tree.heading("new_zh", text="New Chinese")

        self.bulk_tree.column("file", width=120)
        self.bulk_tree.column("key", width=120)
        self.bulk_tree.column("eng", width=200)
        self.bulk_tree.column("old_zh", width=200)
        self.bulk_tree.column("new_zh", width=200)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.bulk_tree.yview)
        self.bulk_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.bulk_tree.pack(fill="both", expand=True)

        self.bulk_tree.bind("<Double-1>", self.on_bulk_tree_double_click)

        self.bulk_tree.bind("<Button-3>", self.on_bulk_right_click)

    def init_search_tab(self):
        # --- Create Path/Filter frame for this tab ---
        self.search_path_entry, self.search_filter_entry = self.create_path_filter_frame(self.tab_search)

        fr_top = tk.Frame(self.tab_search)
        fr_top.pack(fill="x", padx=5, pady=0)  # Removed top padding

        tk.Label(fr_top, text="Search English Keywords (one per line):").pack(anchor="nw")
        self.search_text = Text(fr_top, height=4)
        self.search_text.pack(fill="x", pady=5)
        self.search_text.insert("1.0", "quarter\nMIR")

        tk.Button(fr_top, text="Search", command=self.start_search,
                  font=("Arial", 11, "bold")).pack(pady=5)

        tk.Label(self.tab_search, text="Double-click a row to edit Translation immediately:", fg="gray").pack(
            anchor="w", padx=5)

        # Treeview for results
        cols = ("file", "key", "eng", "zh")
        self.tree = ttk.Treeview(self.tab_search, columns=cols, show="headings")
        self.tree.heading("file", text="Filename")
        self.tree.heading("key", text="Key")
        self.tree.heading("eng", text="English Value (Contains Keyword)")
        self.tree.heading("zh", text="Current Chinese Value")

        self.tree.column("file", width=150)
        self.tree.column("key", width=150)
        self.tree.column("eng", width=250)
        self.tree.column("zh", width=250)

        vsb = ttk.Scrollbar(self.tab_search, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        self.tree.bind("<Double-1>", self.on_tree_double_click)

        self.tree.bind("<Button-3>", self.on_search_right_click)

    def on_bulk_right_click(self, event):
        """Handles the right-click event on the bulk tree for copying."""
        # Identify the row that was right-clicked
        item_id = self.bulk_tree.identify_row(event.y)
        if not item_id:
            return

        # Select the row that was right-clicked
        self.bulk_tree.selection_set(item_id)

        try:
            # Get the values from the selected row
            item_data = self.bulk_tree.item(item_id, "values")
            eng_val = item_data[2]
            old_zh_val = item_data[3]
            new_zh_val = item_data[4]

            # Create the popup menu
            popup_menu = tk.Menu(self.root, tearoff=0)
            popup_menu.add_command(label="Copy English Value",
                                   command=lambda: self.copy_to_clipboard(eng_val))
            popup_menu.add_command(label="Copy Current Chinese",
                                   command=lambda: self.copy_to_clipboard(old_zh_val))
            popup_menu.add_command(label="Copy New Chinese",
                                   command=lambda: self.copy_to_clipboard(new_zh_val))

            # Display the menu at the cursor's location
            popup_menu.post(event.x_root, event.y_root)
        except Exception as e:
            self.log(f"Error creating copy menu: {e}")

    def on_search_right_click(self, event):
        """Handles the right-click event on the search tree for copying."""
        # Identify the row that was right-clicked
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return

        # Select the row that was right-clicked
        self.tree.selection_set(item_id)

        try:
            # Get the values from the selected row
            item_data = self.tree.item(item_id, "values")
            eng_val = item_data[2]
            zh_val = item_data[3]

            # Create the popup menu
            popup_menu = tk.Menu(self.root, tearoff=0)
            popup_menu.add_command(label="Copy English Value",
                                   command=lambda: self.copy_to_clipboard(eng_val))
            popup_menu.add_command(label="Copy Chinese Value",
                                   command=lambda: self.copy_to_clipboard(zh_val))

            # Display the menu at the cursor's location
            popup_menu.post(event.x_root, event.y_root)
        except Exception as e:
            self.log(f"Error creating copy menu: {e}")

    # --- SHARED HELPERS ---
    def copy_to_clipboard(self, text):
        """Helper to copy text to the system clipboard."""
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        # Optional: Log the action
        self.log(f"📋 Copied to clipboard: \"{text[:50]}...\"")

    def log(self, msg):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")
        self.root.update_idletasks()

    def browse_path(self, target_entry):
        """Updates the specified path entry widget."""
        path = filedialog.askdirectory()
        if path:
            target_entry.delete(0, tk.END)
            target_entry.insert(0, path)

    def get_target_files(self, path_entry, filter_entry):
        """Gets files based on the specified path and filter entries."""
        path = path_entry.get()
        filt = filter_entry.get().strip()
        if not os.path.isdir(path): return None
        targets = []
        for r, d, f in os.walk(path):
            d[:] = [x for x in d if x not in ['.git', 'node_modules', 'build', 'target']]
            for file in f:
                if file.endswith(".properties") and not file.endswith("_zh_TW.properties"):
                    if self.file_matches_filter(file, filt):
                        targets.append(os.path.join(r, file))
        return targets

    def file_matches_filter(self, filename, expression):
        if not expression: return True
        try:
            # Safe-ish eval for boolean keywords
            safe_expr = expression.lower()
            for term in set(re.findall(r'[a-zA-Z0-9_.-]+', safe_expr)) - {'and', 'or', 'not'}:
                safe_expr = re.sub(r'\b' + re.escape(term) + r'\b', str(term in filename.lower()), safe_expr)
            return eval(safe_expr)
        except:
            return True

    def get_key_value_map(self, filepath):
        """Helper to read a properties file into a key->value dict."""
        kv_map = {}
        if not os.path.exists(filepath):
            return kv_map

        # Try a list of common encodings for this file type
        encodings_to_try = ['utf-8', 'cp950', 'iso-8859-1']

        for encoding in encodings_to_try:
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    lines = f.readlines()

                # If we successfully read, process the lines
                for line in lines:
                    if '=' in line and not line.strip().startswith('#'):
                        k, v = line.split('=', 1)
                        kv_map[k.strip()] = v.strip()

                # If successful, log it (if it wasn't utf-8) and return
                if encoding != 'utf-8':
                    self.log(f"  ...Read {os.path.basename(filepath)} using '{encoding}'.")
                return kv_map

            except UnicodeDecodeError:
                # This is the expected error, just try the next encoding
                continue
            except Exception as e:
                # Catch any other unexpected error (e.g., permission denied)
                self.log(f"Error reading {filepath}: {e}")
                return kv_map  # Abort on non-encoding errors

        # If all encodings failed
        self.log(f"❌ Error reading {filepath}: Could not decode file with any of {encodings_to_try}")
        return kv_map

    # --- BULK MODE ---
    def find_bulk_matches(self):
        """Finds all potential replacements and populates the bulk tree."""
        # *** Use bulk tab's entries ***
        files = self.get_target_files(self.bulk_path_entry, self.bulk_filter_entry)
        if files is None: return messagebox.showerror("Error", "Invalid Path for Auto Replace")

        raw_txt = self.translations_text.get("1.0", tk.END)
        translations = {}
        malformed_lines = 0
        for line in raw_txt.splitlines():
            line = line.strip()
            if not line: continue

            # Split on the first occurrence of two spaces
            parts = line.split('  ', 1)

            if len(parts) == 2:
                eng_key = parts[0].strip()
                chi_val = parts[1].strip()
                if eng_key and chi_val:  # Ensure neither part is empty
                    translations[eng_key] = chi_val
                else:
                    malformed_lines += 1  # Empty key or value
            else:
                malformed_lines += 1  # No '  ' delimiter found

        if malformed_lines > 0:
            self.log(f"⚠️ Skipped {malformed_lines} lines (missing '  ' delimiter or empty parts).")

        if not translations:
            self.log("❌ No valid translations found. Check your input format (Eng  Chi).")
            return messagebox.showerror("Error",
                                        "No valid translations found. Ensure you are using two spaces as a delimiter.")

        # Clear previous results
        self.bulk_tree.delete(*self.bulk_tree.get_children())
        self.bulk_matches_data.clear()

        self.log(f"🚀 Finding potential replacements for {len(translations)} keys...")
        match_count = 0

        for eng_path in files:
            zh_path = eng_path.replace(".properties", "_zh_TW.properties")
            if not os.path.exists(zh_path): continue

            eng_map = self.get_key_value_map(eng_path)
            zh_map = self.get_key_value_map(zh_path)

            for key, eng_val in eng_map.items():
                if eng_val in translations:
                    new_zh = translations[eng_val]
                    old_zh = zh_map.get(key, "[Not Found]")

                    if old_zh != new_zh:
                        values = (zh_path, key, eng_val, old_zh, new_zh)
                        item_id = self.bulk_tree.insert("", "end", values=values)
                        self.bulk_matches_data[item_id] = (zh_path, key, eng_val, old_zh, new_zh)
                        match_count += 1

        self.log(f"✅ Found {match_count} potential replacements. Double-click a row to review.")

    def on_bulk_tree_double_click(self, event):
        """Handles the double-click event on the bulk replacement tree."""
        item_id = self.bulk_tree.selection()
        if not item_id:
            return

        item_id = item_id[0]

        if item_id not in self.bulk_matches_data:
            return

        zh_path, key, eng_val, old_zh, new_zh = self.bulk_matches_data[item_id]

        dlg = ConfirmationDialog(self.root, (zh_path, key), eng_val, old_zh, new_zh)

        if dlg.result:
            if self.update_single_key_in_file(zh_path, key, new_zh):
                self.log(f"  ➡️ Replaced [{key}] in {os.path.basename(zh_path)}")
                self.bulk_tree.delete(item_id)
                del self.bulk_matches_data[item_id]
            else:
                self.log(f"  ❌ FAILED to replace [{key}] (file write error)")
        else:
            self.log(f"  Cancelled replacement for [{key}]")

    # --- SEARCH MODE ---
    def start_search(self):
        # *** Use search tab's entries ***
        files = self.get_target_files(self.search_path_entry, self.search_filter_entry)
        if files is None: return messagebox.showerror("Error", "Invalid Path for Manual Replace")

        keywords = [k.strip() for k in self.search_text.get("1.0", tk.END).splitlines() if k.strip()]

        # Clear previous results
        for item in self.tree.get_children(): self.tree.delete(item)
        self.search_matches_data.clear()

        if keywords:
            self.log(f"🔎 Searching {len(files)} files for keywords: {keywords}...")
        else:
            self.log(f"🔎 Loading all keys from {len(files)} files...")

        match_count = 0

        for eng_path in files:
            zh_path = eng_path.replace(".properties", "_zh_TW.properties")
            if not os.path.exists(zh_path): continue

            # Read ENG to find matches
            eng_matches = []
            try:
                # *** Use the new robust map function ***
                eng_map = self.get_key_value_map(eng_path)
                for k, v in eng_map.items():
                    if not keywords or any(kw.lower() in v.lower() for kw in keywords):
                        eng_matches.append((k, v))
            except Exception as e:
                self.log(f"Err processing {eng_path}: {e}")
                continue

            if not eng_matches: continue

            # Read ZH to get current values for matches
            zh_vals = self.get_key_value_map(zh_path)

            # Populate tree
            for key, eng_val in eng_matches:
                cur_zh = zh_vals.get(key, "[Not Found]")
                basename = os.path.basename(zh_path)
                item_id = self.tree.insert("", "end", values=(zh_path, key, eng_val, cur_zh))
                self.search_matches_data[item_id] = (zh_path, key, eng_val, cur_zh)
                match_count += 1

        self.log(f"🔎 Found {match_count} matches.")

    def on_tree_double_click(self, event):
        item_id = self.tree.selection()
        if not item_id:
            return
        item_id = item_id[0]

        if item_id not in self.search_matches_data:
            return

        zh_path, key, eng_val, cur_zh = self.search_matches_data[item_id]

        new_zh = simpledialog.askstring("Edit Translation",
                                        f"English: {eng_val}\nKey: {key}\n\nEnter new Chinese value:",
                                        parent=self.root,
                                        initialvalue=cur_zh)

        if new_zh is not None and new_zh != cur_zh:
            if self.update_single_key_in_file(zh_path, key, new_zh):
                basename = os.path.basename(zh_path)
                self.tree.item(item_id, values=(zh_path, key, eng_val, new_zh))
                self.search_matches_data[item_id] = (zh_path, key, eng_val, new_zh)
                self.log(f"💾 Saved immediately: {key} -> {new_zh}")
            else:
                messagebox.showerror("Error", "Could not find key in file to update.")

    def update_single_key_in_file(self, filepath, target_key, new_value):

        # *** Determine encoding for writing ***
        # Default to utf-8, but check if we read it differently
        read_encoding = 'utf-8'  # Default

        # Simple check: try reading a byte to guess
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                f.read(1)
            read_encoding = 'utf-8'
        except UnicodeDecodeError:
            try:
                with open(filepath, 'r', encoding='cp950') as f:
                    f.read(1)
                read_encoding = 'cp950'
            except UnicodeDecodeError:
                read_encoding = 'iso-8859-1'
        except Exception:
            pass  # Keep default 'utf-8'

        try:
            # Read with detected encoding
            with open(filepath, 'r', encoding=read_encoding) as f:
                lines = f.readlines()

            found = False
            for i, line in enumerate(lines):
                if line.strip().startswith(target_key + "=") or line.strip().startswith(target_key + " ="):
                    key_part = line.split('=', 1)[0]
                    lines[i] = f"{key_part.rstrip()}={new_value}\n"
                    found = True
                    break

            if found:
                # Write back with the *same* encoding
                with open(filepath, 'w', encoding=read_encoding) as f:
                    f.writelines(lines)
                if read_encoding != 'utf-8':
                    self.log(f"  ...Wrote back to file using '{read_encoding}'.")
                return True
            else:
                return False
        except Exception as e:
            self.log(f"❌ Error saving file: {e}")
            return False


if __name__ == "__main__":
    root = tk.Tk()
    app = TranslatorApp(root)
    root.mainloop()
