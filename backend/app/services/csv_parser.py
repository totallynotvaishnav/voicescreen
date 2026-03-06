import io
import pandas as pd
from typing import Tuple


def parse_candidates_csv(file_content: bytes) -> Tuple[list[dict], list[str]]:
    """Parse and validate a candidates CSV file.
    
    Required columns: name, phone
    Optional columns: email, resume_url
    
    Returns: (list of candidate dicts, list of error messages)
    """
    errors = []
    candidates = []

    try:
        df = pd.read_csv(io.BytesIO(file_content), dtype=str)
    except Exception as e:
        return [], [f"Failed to parse CSV: {str(e)}"]

    # Normalize column names
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

    # Check required columns
    required = {"name", "phone"}
    missing = required - set(df.columns)
    if missing:
        return [], [f"Missing required columns: {', '.join(missing)}"]

    for idx, row in df.iterrows():
        row_num = idx + 2  # 1-indexed + header row

        name = str(row.get("name", "")).strip()
        phone = str(row.get("phone", "")).strip()
        # Ensure phone has + prefix for international format
        if phone and not phone.startswith("+"):
            phone = f"+{phone}"
        email = str(row.get("email", "")).strip() if pd.notna(row.get("email")) else None
        resume_url = str(row.get("resume_url", "")).strip() if pd.notna(row.get("resume_url")) else None

        if not name:
            errors.append(f"Row {row_num}: missing name")
            continue
        if not phone:
            errors.append(f"Row {row_num}: missing phone")
            continue

        candidates.append({
            "name": name,
            "email": email,
            "phone": phone,
            "resume_url": resume_url,
        })

    return candidates, errors
