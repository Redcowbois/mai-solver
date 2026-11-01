from pathlib import Path
import re

def parse_maidata_file(file_path: str | Path) -> dict:
    with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
        content = f.read()

    # Split on '&' tags at line starts or inline
    # Pattern captures: &key=value
    pattern = re.compile(r"&([a-zA-Z0-9_]+)=(.*?)(?=\n&|\Z)", re.DOTALL)
    matches = pattern.findall(content)

    chart_data = {
        "metadata": {},
        "levels": {},
        "charts": {}
    }

    for key, value in matches:
        key = key.strip()
        value = value.strip()

        if key.startswith("lv_"):
            diff_idx = int(key.split("_")[1])
            chart_data["levels"][diff_idx] = value
        elif key.startswith("inote_"):
            diff_idx = int(key.split("_")[1])
            chart_data["charts"][diff_idx] = value
        else:
            chart_data["metadata"][key] = value

    return chart_data

# Example usage:
data = parse_maidata_file("maidata.txt")
print("Title:", data["metadata"].get("title"))
print("Master Level:", data["levels"].get(5))

# The actual simai chart string for Master:
master_chart_str = data["charts"].get(5)