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
import logging
logging.disable(sys.maxsize) # Python 3
import os
import json

"""## Парсинг демки"""

# Путь к файлу с демкой
fname = None

if len(sys.argv) > 1:
    fname = sys.argv[1]
    

if fname and False == os.path.isfile(fname):
    print(f'Файл "{fname}" не найден!')
    sys.exit()  

if fname is None and False == os.path.isfile('DEMO_ID.json'):
    print(f'Файла "DEMO_ID.json" для парсинга тоже нет!')
    sys.exit() 
    
# Парсинг демки    
if fname:   
    demo_parser = DemoParser(
        demofile = fname, 
        demo_id = 'DEMO_ID', 
        parse_frames=False
    )

# Парсинг JSON
with open('DEMO_ID.json') as json_file:
    data = json.load(json_file)
    
kast = {}
rounds = 0
gameRounds = data.get('gameRounds', [])
for gameRound in gameRounds: # по раундам
  if len(gameRound.get('kills', [])): rounds += 1
  for kill in gameRound.get('kills', []):      # по килам
    
    for teg in ('attacker','assister','playerTraded','flashThrower','victim'):
      name = kill[f'{teg}Name']
      if name is None: continue
      team = kill[f'{teg}Team']
      if team and kast.get(team) is None: kast[team] = {}
      if name and kast[team].get(name) is None: kast[team][name] = {}

      # стата по килам
      if 'attacker' == teg:
        k = kast[team][name].get('k', 0) + 1
        if team != kill['victimTeam']:
          kast[team][name].update({'k': k})
      
      # стата по аситам
      # по дамагу
      if 'assister' == teg:  
        a = kast[team][name].get('a', 0) + 1
        kast[team][name].update({'a': a})
      # по флешке  
      if 'flashThrower' == teg:  
        a = kast[team][name].get('a', 0) + 1
        kast[team][name].update({'a': a})

      # подсчет жертв в раунде
      if 'victim' == teg:  
        s = kast[team][name].get('s', 0) - 1
        kast[team][name].update({'s': s})

      # стата по размену
      if 'playerTraded' == teg and name:
        t = kast[team][name].get('t', 0)
        kast[team][name].update({'t': t + 1})
  
# суммирование 
max_kast = 0
for team in kast:
  for name in kast[team]:
    # коррекция выживания 
    s = kast[team][name].get('s', 0)
    kast[team][name]['s'] = s + rounds
    agg = kast[team][name].get('k', 0)
    agg += kast[team][name].get('a', 0)
    agg += kast[team][name].get('s', 0)
    agg += kast[team][name].get('t', 0)
    kast[team][name]['kast'] = agg
    if max_kast < agg: max_kast = agg

# проценты
for team in kast:
  for name in kast[team]:
    agg = kast[team][name]['kast']
    kast[team][name]['kast'] = agg/max_kast
print(kast)