# -*- coding: utf-8 -*-
import json
with open('../data/studyabroad.json') as f:
    data = json.load(f)

with open('./Studyabroad-1656-1672.json') as f:
    data2 = json.load(f)

for a in data2['articles']:
    data['articles'].append(a)

with open('studyabroad2.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False)
