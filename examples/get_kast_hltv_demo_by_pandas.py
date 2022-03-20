# -*- coding: utf-8 -*-
"""Расчет KAST демки HLTV

# Задача

Реализовать питоновский модуль, который будет расчитывать
метрику KAST для каждого игрока из демки.

"""

# Commented out IPython magic to ensure Python compatibility.
# #@title Установка парсера демок
# %%shell
# add-apt-repository -y ppa:longsleep/golang-backports
# apt -y update
# apt -y install golang-go
# 
# pip install git+https://github.com/pnxenopoulos/awpy.git
# 
# wget https://storage.googleapis.com/csgo-tests/default.dem

#@title Импорт библиотек
from awpy import DemoParser
import pandas as pd
import operator
from typing import Dict, List, Tuple, Union
import sys

"""## Парсинг демки"""

# Путь к файлу с демкой
fname = None
if len(sys.argv) > 1:
    fname = sys.argv[1]
else:
    fname = input('Введите путь до демки:')
if fname is None:
    print('Путь к демки не определен')
    sys.exit()
    
import logging
logging.disable(sys.maxsize) # Python 3
    
demo_parser = DemoParser(
    demofile = fname, 
    demo_id = 'DEMO_ID', 
    parse_frames=False
)
df = demo_parser.parse(return_type="df")

#@title Чистка данных
# Clean the dataframes. 
def clean(df: pd.DataFrame) -> pd.DataFrame:
        df_copy = df.copy()
        df_copy = df_copy.loc[(df_copy["roundNum"]>3) & (df_copy["roundNum"]<32)].copy()
        df_copy.reset_index(inplace=True, drop=True)
        df_copy["roundNum"]=df_copy["roundNum"]-3
        return df_copy

#@markdown Результаты по убийствам за игру
kill_data = clean(df["kills"])

#@title Функции расчета
def extract_num_filters(
    filters: Dict[str, Union[List[bool], List[str]]], key: str
) -> Tuple[List[str], List[float]]:
    sign_list = []
    val_list = []
    for index in filters[key]:
        if not isinstance(index, str):
            raise ValueError(
                f'Filter(s) for column "{key}" must be of type ' f"string."
            )
        i = 0
        sign = ""
        while i < len(index) and not index[i].isdecimal():
            sign += index[i]
            end_index = i
            i += 1
        if sign not in ("==", "!=", "<=", ">=", "<", ">"):
            raise Exception(
                f'Invalid logical operator in filters for "{key}"' f" column."
            )
        sign_list.append(sign)
        try:
            val_list.append(float(index[end_index + 1 :]))
        except ValueError as ve:
            raise Exception(
                f'Invalid numerical value in filters for "{key}" ' f"column."
            ) from ve
    return sign_list, val_list


def check_filters(df: pd.DataFrame, filters: Dict[str, Union[List[bool], List[str]]]):
    for key in filters:
        if df.dtypes[key] == "bool":
            for index in filters[key]:
                if not isinstance(index, bool):
                    raise ValueError(
                        f'Filter(s) for column "{key}" must be ' f"of type boolean"
                    )
        elif df.dtypes[key] == "O":
            for index in filters[key]:
                if not isinstance(index, str):
                    raise ValueError(
                        f'Filter(s) for column "{key}" must be ' f"of type string"
                    )
        else:
            extract_num_filters(filters, key)

            
def num_filter_df(df: pd.DataFrame, col: str, sign: str, val: float) -> pd.DataFrame:
    ops = {
        "==": operator.eq(df[col], val),
        "!=": operator.ne(df[col], val),
        "<=": operator.le(df[col], val),
        ">=": operator.ge(df[col], val),
        "<": operator.lt(df[col], val),
        ">": operator.gt(df[col], val),
    }
    filtered_df = df.loc[ops[sign]]
    return filtered_df


def filter_df(
    df: pd.DataFrame, filters: Dict[str, Union[List[bool], List[str]]]
) -> pd.DataFrame:
    df_copy = df.copy()
    check_filters(df_copy, filters)
    for key in filters:
        if df_copy.dtypes[key] == "bool" or df_copy.dtypes[key] == "O":
            df_copy = df_copy.loc[df_copy[key].isin(filters[key])]
        else:
            i = 0
            for sign in extract_num_filters(filters, key)[0]:
                val = extract_num_filters(filters, key)[1][i]
                df_copy = num_filter_df(
                    df_copy, key, extract_num_filters(filters, key)[0][i], val
                )
                i += 1
    return df_copy


def calc_stats(
    df: pd.DataFrame,
    filters: Dict[str, Union[List[bool], List[str]]],
    col_to_groupby: List[str],
    col_to_agg: List[str],
    agg: List[List[str]],
    col_names: List[str],
) -> pd.DataFrame:
    df_copy = filter_df(df, filters)
    agg_dict = dict(zip(col_to_agg, agg))
    if col_to_agg:
        df_copy = df_copy.groupby(col_to_groupby).agg(agg_dict).reset_index()
    df_copy.columns = col_names
    return df_copy

#@title Расчет KAST
def kast(
    kill_data: pd.DataFrame,
    kast_string: str = "KAST",
    flash_assists: bool = True,
    kill_filters: Dict[str, Union[List[bool], List[str]]] = {},
    death_filters: Dict[str, Union[List[bool], List[str]]] = {},
) -> pd.DataFrame:
    columns = ["Player", f"{kast_string.upper()}%"]
    kast_counts = {}
    kast_rounds = {}
    for stat in kast_string.upper():
        columns.append(stat)
    killers = calc_stats(
        kill_data.loc[kill_data["attackerTeam"] != kill_data["victimTeam"]],
        kill_filters,
        ["roundNum"],
        ["attackerName"],
        [["sum"]],
        ["RoundNum", "Killers"],
    )
    victims = calc_stats(
        kill_data,
        kill_filters,
        ["roundNum"],
        ["victimName"],
        [["sum"]],
        ["RoundNum", "Victims"],
    )
    assisters = calc_stats(
        kill_data.loc[kill_data["assisterTeam"] != kill_data["victimTeam"]].fillna(""),
        kill_filters,
        ["roundNum"],
        ["assisterName"],
        [["sum"]],
        ["RoundNum", "Assisters"],
    )
    traded = calc_stats(
        kill_data.loc[
            (kill_data["attackerTeam"] != kill_data["victimTeam"])
            & (kill_data["isTrade"] == True)
        ].fillna(""),
        kill_filters,
        ["roundNum"],
        ["playerTradedName"],
        [["sum"]],
        ["RoundNum", "Traded"],
    )
    if flash_assists:
        flash_assisters = calc_stats(
            kill_data.loc[
                kill_data["flashThrowerTeam"] != kill_data["victimTeam"]
            ].fillna(""),
            kill_filters,
            ["roundNum"],
            ["flashThrowerName"],
            [["sum"]],
            ["RoundNum", "Flash Assisters"],
        )
        assisters = assisters.merge(flash_assisters, on="RoundNum")
        assisters["Assisters"] = assisters["Assisters"] + assisters["Flash Assisters"]
        assisters = assisters[["RoundNum", "Assisters"]]
    kast_data = killers.merge(assisters, how="outer").fillna("")
    kast_data = kast_data.merge(victims, how="outer").fillna("")
    kast_data = kast_data.merge(traded, how="outer").fillna("")
    for player in kill_data["attackerName"].unique():
        kast_counts[player] = [[0, 0, 0, 0] for i in range(len(kast_data))]
        kast_rounds[player] = [0, 0, 0, 0, 0]
    for rd in kast_data.index:
        for player in kast_counts:
            if "K" in kast_string.upper():
                kast_counts[player][rd][0] = kast_data.iloc[rd]["Killers"].count(player)
                kast_rounds[player][1] += kast_data.iloc[rd]["Killers"].count(player)
            if "A" in kast_string.upper():
                kast_counts[player][rd][1] = kast_data.iloc[rd]["Assisters"].count(
                    player
                )
                kast_rounds[player][2] += kast_data.iloc[rd]["Assisters"].count(player)
            if "S" in kast_string.upper():
                if player not in kast_data.iloc[rd]["Victims"]:
                    kast_counts[player][rd][2] = 1
                    kast_rounds[player][3] += 1
            if "T" in kast_string.upper():
                kast_counts[player][rd][3] = kast_data.iloc[rd]["Traded"].count(player)
                kast_rounds[player][4] += kast_data.iloc[rd]["Traded"].count(player)
    for player in kast_rounds:
        for rd in kast_counts[player]:
            if any(rd):
                kast_rounds[player][0] += 1
        kast_rounds[player][0] /= len(kast_data)
    kast = pd.DataFrame.from_dict(kast_rounds, orient="index").reset_index()
    kast.columns = ["Player", f"{kast_string.upper()}%", "K", "A", "S", "T"]
    kast = kast[columns]
    kast.fillna(0, inplace=True)
    kast.sort_values(by=f"{kast_string.upper()}%", ascending=False, inplace=True)
    kast.reset_index(drop=True, inplace=True)
    return kast

print(kast(kill_data).to_json())