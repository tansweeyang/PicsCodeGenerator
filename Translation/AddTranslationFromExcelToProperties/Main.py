import xml.etree.ElementTree as ET
import pandas as pd

# -------------------- CONFIG --------------------
MENU_XML_FILE = r"C:\Users\admin\Workspace\pj-hkpf-pics3-revamp2-boot-up-application-with-ant-gaussdb\picsII_web\JavaSource\menu.xml"
EN_PROPERTIES_FILE = r"C:\Users\admin\Workspace\pj-hkpf-pics3-revamp2-boot-up-application-with-ant-gaussdb\picsII_web\JavaSource\menu.properties"
ZH_PROPERTIES_FILE = r"C:\Users\admin\Workspace\pj-hkpf-pics3-revamp2-boot-up-application-with-ant-gaussdb\picsII_web\JavaSource\menu_zh_TW.properties"

EXCEL_FILE = "translations.xlsx"  # Excel with columns: Key, EN_value, zh_TW_value
OUTPUT_MISSING_FILE = "missing_translations_menu.xlsx"

ROOT_MENU_ID = "PIMS"  # <menu id="PIMS"> root
KEY_FILTER = "PIMS"  # Only touch keys containing this. Set to "ALL" for no filter.

EXCEL_KEY_COL = "Key"
EXCEL_ZH_COL = "zh_TW_value"


# ------------------------------------------------


def key_matches_filter(key: str) -> bool:
    if KEY_FILTER.upper() == "ALL":
        return True
    return KEY_FILTER in key


def is_menu_tag(elem):
    """Namespace-agnostic check for <menu> tag."""
    return elem.tag.endswith("menu")


def parse_menu_labels(menu_xml_file, root_menu_id=ROOT_MENU_ID):
    """
    Build {label -> id} for all <menu ...> INSIDE <menu id=root_menu_id>.
    Namespace-agnostic.
    """
    tree = ET.parse(menu_xml_file)
    root = tree.getroot()

    # Find <menu id="PIMS">
    menu_block = None
    for node in root.iter():
        if is_menu_tag(node) and node.attrib.get("id") == root_menu_id:
            menu_block = node
            break

    if menu_block is None:
        seen = [n.attrib.get("id") for n in root.iter() if is_menu_tag(n) and "id" in n.attrib]
        raise ValueError(
            f"No menu block with id={root_menu_id} found. Seen ids: {', '.join([s for s in seen if s]) or '(none)'}")

    label_to_id = {}

    def recurse(n):
        if is_menu_tag(n):
            mid = n.attrib.get("id")
            lbl = n.attrib.get("label")
            if mid and lbl:
                label_to_id[lbl.strip()] = mid.strip()
            for c in list(n):
                if is_menu_tag(c):
                    recurse(c)

    # Only traverse inside the PIMS block’s children (skip the root node’s own label)
    for child in list(menu_block):
        if is_menu_tag(child):
            recurse(child)

    if not label_to_id:
        raise ValueError(f"Menu block id={root_menu_id} found but contains no labeled child <menu> nodes.")
    return label_to_id


def read_properties_lines(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.readlines()


def write_properties_lines(path, lines):
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)


def rename_keys_by_labels_in_en(path, label_to_id):
    """
    Scan EN properties; when a line's value equals a known label AND key matches filter,
    rename key -> corresponding menu id. Record old_key -> new_key mapping (for use on ZH).
    Preserve order and untouched lines.
    """
    lines = read_properties_lines(path)
    new_lines = []
    old_to_new = {}

    for line in lines:
        stripped = line.strip()
        if "=" in stripped and not stripped.startswith("#"):
            key, value = stripped.split("=", 1)
            raw_value = value  # keep RHS spacing
            key = key.strip()
            val_clean = value.strip()
            if key_matches_filter(key) and val_clean in label_to_id:
                new_key = label_to_id[val_clean]
                old_to_new[key] = new_key
                new_lines.append(f"{new_key}={raw_value}\n")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    write_properties_lines(path, new_lines)
    return old_to_new


def rename_keys_using_map(path, old_to_new):
    """
    Apply the same key renames to another properties file (e.g., ZH),
    regardless of the value (works even if values are Chinese).
    Only rename if original key matches filter.
    """
    if not old_to_new:
        return

    lines = read_properties_lines(path)
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if "=" in stripped and not stripped.startswith("#"):
            key, value = stripped.split("=", 1)
            key_clean = key.strip()
            if key_matches_filter(key_clean) and key_clean in old_to_new:
                new_key = old_to_new[key_clean]
                new_lines.append(f"{new_key}={value}\n")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    write_properties_lines(path, new_lines)


def load_excel_translations(excel_path):
    """
    Return dict of {excel_key -> zh_value} filtered by KEY_FILTER.
    """
    df = pd.read_excel(excel_path)
    df[EXCEL_KEY_COL] = df[EXCEL_KEY_COL].astype(str).str.strip()
    df[EXCEL_ZH_COL] = df[EXCEL_ZH_COL].astype(str).str.strip()
    if KEY_FILTER.upper() != "ALL":
        df = df[df[EXCEL_KEY_COL].apply(key_matches_filter)]
    return dict(zip(df[EXCEL_KEY_COL], df[EXCEL_ZH_COL]))


def update_zh_values_from_excel(zh_path, excel_map, old_to_new):
    """
    Update zh_TW.properties values from Excel.
    - Only touch lines whose key matches the filter.
    - Support both old keys and their renamed new keys (via old_to_new).
    """
    # Build a unified lookup: any new_key gets value from its original Excel old_key
    excel_lookup = excel_map.copy()
    for old_key, new_key in old_to_new.items():
        if old_key in excel_map:
            excel_lookup[new_key] = excel_map[old_key]

    lines = read_properties_lines(zh_path)
    new_lines = []

    for line in lines:
        stripped = line.strip()
        if "=" in stripped and not stripped.startswith("#"):
            key, value = stripped.split("=", 1)
            key_clean = key.strip()
            if key_matches_filter(key_clean) and key_clean in excel_lookup:
                # Replace ONLY the value, keep key as-is
                new_val = excel_lookup[key_clean]
                new_lines.append(f"{key_clean}={new_val}\n")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    write_properties_lines(zh_path, new_lines)


def collect_properties_keys(path):
    keys = []
    lines = read_properties_lines(path)
    for line in lines:
        stripped = line.strip()
        if "=" in stripped and not stripped.startswith("#"):
            key = stripped.split("=", 1)[0].strip()
            if key_matches_filter(key):
                keys.append(key)
    return set(keys)


def write_missing_report(excel_map, props_keys_after, old_to_new):
    """
    Create missing_translations_menu.xlsx (filtered by KEY_FILTER).
    - Excel-only: Excel key (or its mapped new key) not in properties.
    - Properties-only: Property key not represented by any Excel key (considering renames).
    """
    # Excel keys (old)
    excel_keys = set(excel_map.keys())

    # Map Excel old->new when possible for presence check
    mapped_excel_presence = set()
    for k in excel_keys:
        mapped_excel_presence.add(old_to_new.get(k, k))

    in_excel_not_in_props = sorted(k for k in excel_keys if old_to_new.get(k, k) not in props_keys_after)

    # For props-only, any prop key that is not equal to any Excel key or mapped Excel new key
    props_only = []
    for pk in props_keys_after:
        # if pk equals an Excel old key OR equals a mapped new key, it's covered by Excel
        if pk in excel_keys or pk in mapped_excel_presence:
            continue
        props_only.append(pk)
    in_props_not_in_excel = sorted(props_only)

    rows = []
    for k in in_excel_not_in_props:
        rows.append([k, "Excel only"])
    for k in in_props_not_in_excel:
        rows.append([k, "Properties only"])

    if rows:
        df = pd.DataFrame(rows, columns=["Key", "Location"])
        df.to_excel(OUTPUT_MISSING_FILE, index=False)


if __name__ == "__main__":
    # 1) Parse menu.xml: label -> id
    label_to_id = parse_menu_labels(MENU_XML_FILE, root_menu_id=ROOT_MENU_ID)

    # 2) Rename keys in EN by label matching, record old->new
    old_to_new_map = rename_keys_by_labels_in_en(EN_PROPERTIES_FILE, label_to_id)

    # 3) Apply the same key renames to ZH (value-agnostic)
    rename_keys_using_map(ZH_PROPERTIES_FILE, old_to_new_map)

    # 4) Load Excel translations and update ZH values (support old & new keys)
    excel_translations = load_excel_translations(EXCEL_FILE)
    update_zh_values_from_excel(ZH_PROPERTIES_FILE, excel_translations, old_to_new_map)

    # 5) Missing keys report (filtered, and rename-aware)
    props_keys = collect_properties_keys(ZH_PROPERTIES_FILE) | collect_properties_keys(EN_PROPERTIES_FILE)
    write_missing_report(excel_translations, props_keys, old_to_new_map)

    print(
        "✅ Done: keys renamed from menu.xml (PIMS-only) and Chinese values updated from Excel. Missing report written.")
