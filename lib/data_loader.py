"""
BESS Dashboard - Data Loading & Preprocessing Module

Handles CSV/TSV parsing, BOM removal, datetime conversion,
and pivot transformations for all BESS logger data files.
"""

import pandas as pd
import re
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def _clean_str(s):
    """Strip BOM, tabs, quotes, and whitespace from a string."""
    if not isinstance(s, str):
        return s
    # Repeatedly strip all unwanted edge characters
    prev = None
    while s != prev:
        prev = s
        s = s.strip()
        s = s.strip("\ufeff")
        s = s.strip('"')
        s = s.strip("\t")
    return s


def _strip_bom_and_whitespace(df):
    """Clean all string columns and column names."""
    for col in df.columns:
        if pd.api.types.is_string_dtype(df[col]):
            df[col] = df[col].apply(_clean_str)
    df.columns = [_clean_str(c) for c in df.columns]
    return df


def load_perfmg_minute():
    """Load 5-min performance metrics (TSV with quoted fields).

    Returns a pivoted DataFrame:
        index: datetime
        columns: metric names (e.g. 'Active power', 'ESS Average SOC')
        values: float
    """
    df = pd.read_csv(
        DATA_DIR / "perfmg_minute.csv",
        sep="\t",
        dtype=str,
    )
    df = _strip_bom_and_whitespace(df)

    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    df["Statistical start time"] = pd.to_datetime(
        df["Statistical start time"], errors="coerce"
    )

    pivot = df.pivot_table(
        index="Statistical start time",
        columns="Performance Data",
        values="Value",
        aggfunc="first",
    )
    pivot.index.name = "datetime"
    pivot = pivot.sort_index()
    return pivot


def load_grid_dispatch_log():
    """Load grid dispatch log (CSV with BOM, NULL-padded records)."""
    raw = (DATA_DIR / "grid_dispatch_log.csv").read_bytes()
    # Strip NULL bytes used as record padding
    cleaned = raw.replace(b"\x00", b"")
    from io import StringIO
    text = cleaned.decode("utf-8-sig")
    df = pd.read_csv(StringIO(text), dtype=str)
    df = _strip_bom_and_whitespace(df)

    # Drop empty trailing column
    df = df.loc[:, ~df.columns.str.match(r"^Unnamed")]

    df["Dispatch Time"] = pd.to_datetime(df["Dispatch Time"], errors="coerce")
    df["Discarded Times"] = pd.to_numeric(df["Discarded Times"], errors="coerce")
    df = df.sort_values("Dispatch Time").reset_index(drop=True)
    return df


def load_historyalarm():
    """Load alarm history (CSV with BOM)."""
    df = pd.read_csv(
        DATA_DIR / "historyalarm.csv",
        encoding="utf-8-sig",
        dtype=str,
    )
    df = _strip_bom_and_whitespace(df)
    df = df.loc[:, ~df.columns.str.match(r"^Unnamed")]

    df["Generation time"] = pd.to_datetime(df["Generation time"], errors="coerce")
    df["End time"] = pd.to_datetime(df["End time"], errors="coerce")
    df["SN"] = pd.to_numeric(df["SN"], errors="coerce")
    df = df.sort_values("Generation time").reset_index(drop=True)
    return df


def load_soe_event():
    """Load SOE (Sequence of Events) data (CSV with BOM)."""
    df = pd.read_csv(
        DATA_DIR / "soe_event.csv",
        encoding="utf-8-sig",
        dtype=str,
    )
    df = _strip_bom_and_whitespace(df)
    df = df.loc[:, ~df.columns.str.match(r"^Unnamed")]

    # SOE timestamp uses ':' for milliseconds separator
    df["Generation time"] = df["Generation time"].str.replace(
        r":(\d{3})$", r".\1", regex=True
    )
    df["Generation time"] = pd.to_datetime(df["Generation time"], errors="coerce")
    df["No."] = pd.to_numeric(df["No."], errors="coerce")
    df = df.sort_values("Generation time").reset_index(drop=True)
    return df


def load_usrmg_user_log():
    """Load user management / operation log (CSV with BOM)."""
    df = pd.read_csv(
        DATA_DIR / "usrmg_user_log.csv",
        encoding="utf-8-sig",
        dtype=str,
    )
    df = _strip_bom_and_whitespace(df)
    df = df.loc[:, ~df.columns.str.match(r"^Unnamed")]

    df["Operation Time"] = pd.to_datetime(df["Operation Time"], errors="coerce")
    df["No."] = pd.to_numeric(df["No."], errors="coerce")
    df = df.sort_values("Operation Time").reset_index(drop=True)
    return df


def get_perfmg_units():
    """Return a dict mapping metric name -> unit string."""
    df = pd.read_csv(
        DATA_DIR / "perfmg_minute.csv",
        sep="\t",
        dtype=str,
    )
    df = _strip_bom_and_whitespace(df)
    units = {}
    for _, row in df.drop_duplicates(subset=["Performance Data"]).iterrows():
        units[row["Performance Data"]] = row["Unit"]
    return units
