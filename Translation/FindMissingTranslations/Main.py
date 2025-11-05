import os
import glob
import pandas as pd


def extract_properties_to_list(directory_paths, module_name, filename_filter=None):
    """
    Extracts key-value pairs from *_resource.properties files in one or more directories.

    Args:
        directory_paths (list[str]): Paths to search.
        module_name (str): Value to put in the 'Module' column.
        filename_filter (callable, optional): Function that receives filename and returns True/False.

    Returns:
        list of dict: Extracted properties data.
    """
    data = []

    for directory_path in directory_paths:
        all_files = glob.glob(os.path.join(directory_path, "*.properties"), recursive=True)

        # Filter for *_resource.properties only
        filtered_files = [f for f in all_files if f.lower().endswith("_resource.properties")]

        # Apply optional custom filter
        if filename_filter:
            filtered_files = [f for f in filtered_files if filename_filter(os.path.basename(f))]

        for file_path in filtered_files:
            resource_name = os.path.basename(file_path)
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        key, value = line.split('=', 1)
                        data.append({
                            "Module": module_name,
                            "ENG VALUE": value.strip(),
                            "ZH VALUE": "",
                            "RESOURCE PROPERTIES NAME": resource_name
                        })
    return data


def autofit_columns(writer, df, sheet_name):
    """
    Auto-adjust Excel columns to fit longest text in each column.
    """
    worksheet = writer.sheets[sheet_name]
    for idx, col in enumerate(df.columns):
        # Find max length in column + length of column header
        max_len = max(
            df[col].astype(str).map(len).max(),
            len(col)
        ) + 2  # add some padding
        worksheet.set_column(idx, idx, max_len)


# Paths
bd_paths = [
    r"C:\Users\admin\Workspace\pj-hkpf-pics3-revamp2-boot-up-application-with-ant-gaussdb\pwing_web\JavaSourceGeneral\resource\bd",
    r"C:\Users\admin\Workspace\pj-hkpf-pics3-revamp2-boot-up-application-with-ant-gaussdb\pwing_web\JavaSource\resource\bd"
]
bo_paths = [
    r"C:\Users\admin\Workspace\pj-hkpf-pics3-revamp2-boot-up-application-with-ant-gaussdb\pwing_web\JavaSourceGeneral\resource\bo",
    r"C:\Users\admin\Workspace\pj-hkpf-pics3-revamp2-boot-up-application-with-ant-gaussdb\pwing_web\JavaSource\resource\bo"
]

# Extract Bd (only from bd folder)
qhs_data = extract_properties_to_list(
    bd_paths,
    module_name="qhs",
    filename_filter=lambda fn: (
            "qhs" in fn.lower()
    )
)

# Extract Bo (Qhs but not BaseQhs or SearchBo)
bo_data = extract_properties_to_list(
    bo_paths,
    module_name="qhs",
    filename_filter=lambda fn: (
            "qhs" in fn.lower()
            and not fn.lower().startswith("baseqhs")
            and not fn.endswith("S_resource.properties")  # exclude SearchBo
    )
)

# Extract SearchBo (must end with S_resource.properties, capital S)
searchbo_data = extract_properties_to_list(
    bo_paths,
    module_name="qhs",
    filename_filter=lambda fn:
    (
            "qhs" in fn.lower()
            and fn.endswith("S_resource.properties")
    )
)

# Extract BaseBo (BaseQhs only)
basebo_data = extract_properties_to_list(
    bo_paths,
    module_name="qhs",
    filename_filter=lambda fn: fn.lower().startswith("baseqhs")
)

# Create DataFrames
df_qhs = pd.DataFrame(qhs_data, columns=["Module", "ENG VALUE", "ZH VALUE", "RESOURCE PROPERTIES NAME"])
df_bo = pd.DataFrame(bo_data, columns=["Module", "ENG VALUE", "ZH VALUE", "RESOURCE PROPERTIES NAME"])
df_searchbo = pd.DataFrame(searchbo_data, columns=["Module", "ENG VALUE", "ZH VALUE", "RESOURCE PROPERTIES NAME"])
df_basebo = pd.DataFrame(basebo_data, columns=["Module", "ENG VALUE", "ZH VALUE", "RESOURCE PROPERTIES NAME"])

# Output Excel file
output_excel = os.path.join(os.getcwd(), "QHS_RESOURCES_PWING.xlsx")

# Write multiple sheets
with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
    df_qhs.to_excel(writer, sheet_name="Bd", index=False)
    autofit_columns(writer, df_qhs, "Bd")

    df_bo.to_excel(writer, sheet_name="Bo", index=False)
    autofit_columns(writer, df_bo, "Bo")

    df_searchbo.to_excel(writer, sheet_name="SearchBo", index=False)
    autofit_columns(writer, df_searchbo, "SearchBo")

    df_basebo.to_excel(writer, sheet_name="BaseBo", index=False)
    autofit_columns(writer, df_basebo, "BaseBo")

print(f"Excel file with sheets 'Bd', 'Bo', 'SearchBo', and 'BaseBo' generated at: {output_excel}")
