from typing import List

def csv_to_list(v: str | List[str] | None) -> List[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [s.strip() for s in v if s and str(s).strip()]
    return [s.strip() for s in str(v).split(",") if s.strip()]