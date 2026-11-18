"""
Build a unified NBA team-season dataset (2000-01 to 2024-25).

Combines Basketball-Reference per-game and advanced team stats for each
season into one table, tags each season's champion, and normalizes
franchise names so teams can be tracked across relocations/renames.

Input:  data/<season>_per_game.csv and data/<season>_advanced.csv
        (e.g. data/2000-01_per_game.csv)
Output: data/nba_master.csv
"""

from pathlib import Path

import pandas as pd

DATA_DIR = Path("data")

# Columns needed for the analysis
KEEP_COLS = ["Season", "Team", "G", "FGA", "3P", "3PA", "3P%", "FG%", "PTS",
             "W", "L", "Pace", "ORtg", "3PAr", "TS%"]
NUMERIC_COLS = KEEP_COLS[2:]

CHAMPIONS = {
    "2000-01": "Los Angeles Lakers",
    "2001-02": "Los Angeles Lakers",
    "2002-03": "San Antonio Spurs",
    "2003-04": "Detroit Pistons",
    "2004-05": "San Antonio Spurs",
    "2005-06": "Miami Heat",
    "2006-07": "San Antonio Spurs",
    "2007-08": "Boston Celtics",
    "2008-09": "Los Angeles Lakers",
    "2009-10": "Los Angeles Lakers",
    "2010-11": "Dallas Mavericks",
    "2011-12": "Miami Heat",
    "2012-13": "Miami Heat",
    "2013-14": "San Antonio Spurs",
    "2014-15": "Golden State Warriors",
    "2015-16": "Cleveland Cavaliers",
    "2016-17": "Golden State Warriors",
    "2017-18": "Golden State Warriors",
    "2018-19": "Toronto Raptors",
    "2019-20": "Los Angeles Lakers",
    "2020-21": "Milwaukee Bucks",
    "2021-22": "Golden State Warriors",
    "2022-23": "Denver Nuggets",
    "2023-24": "Boston Celtics",
    "2024-25": "Oklahoma City Thunder",
}

# Map old franchise names to current ones
NAME_MAP = {
    "Vancouver Grizzlies": "Memphis Grizzlies",
    "New Jersey Nets": "Brooklyn Nets",
    "Seattle SuperSonics": "Oklahoma City Thunder",
    "New Orleans Hornets": "New Orleans Pelicans",
    "New Orleans/Oklahoma City Hornets": "New Orleans Pelicans",
    "Charlotte Bobcats": "Charlotte Hornets",
}


def clean_team_rows(df: pd.DataFrame, season: str) -> pd.DataFrame:
    """Drop repeated header / league-average rows and tidy team names."""
    df = df[~df["Team"].isin(["Team", "League Average"])].copy()
    # Playoff teams are marked with '*' on Basketball-Reference
    df["Team"] = df["Team"].str.replace("*", "", regex=False).str.strip()
    df["Season"] = season
    return df


def load_per_game() -> pd.DataFrame:
    dfs = []
    for path in sorted(DATA_DIR.glob("*_per_game.csv")):
        season = path.stem.replace("_per_game", "")
        dfs.append(clean_team_rows(pd.read_csv(path, header=0), season))
    print(f"Loaded {len(dfs)} per-game files")
    return pd.concat(dfs, ignore_index=True)


def load_advanced() -> pd.DataFrame:
    dfs = []
    for path in sorted(DATA_DIR.glob("*_advanced.csv")):
        season = path.stem.replace("_advanced", "")
        # Advanced tables have a two-row header; the second row has the names
        df = pd.read_csv(path, header=1)
        df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
        dfs.append(clean_team_rows(df, season))
    print(f"Loaded {len(dfs)} advanced files")
    return pd.concat(dfs, ignore_index=True)


def build_master() -> pd.DataFrame:
    master = pd.merge(load_per_game(), load_advanced(),
                      on=["Team", "Season"], how="inner")
    print(f"Merged: {master.shape[0]} rows, {master.shape[1]} columns")

    master = master[KEEP_COLS].copy()
    master[NUMERIC_COLS] = master[NUMERIC_COLS].apply(pd.to_numeric, errors="coerce")
    master["Year"] = master["Season"].str[:4].astype(int)

    # Tag champions before renaming, since CHAMPIONS uses each season's actual name
    master["Champion"] = (master["Season"].map(CHAMPIONS) == master["Team"]).astype(int)
    master["Team"] = master["Team"].replace(NAME_MAP)
    return master


if __name__ == "__main__":
    master = build_master()

    # Sanity check: exactly one champion per season
    assert master.groupby("Season")["Champion"].sum().eq(1).all(), \
        "Some season is missing a champion (check team names)"

    out = DATA_DIR / "nba_master.csv"
    master.to_csv(out, index=False)
    print(f"Saved {out}: {master.shape[0]} rows, {master.shape[1]} columns")
    print(master.head())
