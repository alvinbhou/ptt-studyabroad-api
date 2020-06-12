import csv
import json
import collections
import os
from config.settings import DATA_DIR

with open(os.path.join(DATA_DIR, 'us/university_avoid_list.json'), 'r') as f:
    avoid_list = set(json.load(f)['avoid'])


def load_universities_with_uids(us_universities_uids_path):
    universities = []
    id2uni = {}
    with open(us_universities_uids_path, 'r') as f:
        csv_reader = csv.reader(f, delimiter='|')
        for row in csv_reader:
            assert len(row) == 2
            us = row[1].split(',')
            if len(us) == 1 or (len(us) > 1 and '$' not in row[1]):
                name = us[0].strip().replace(' @ ', ', ')
                if name in avoid_list:
                    continue
                id2uni[row[0].strip()] = name
                universities.append(name)
                if len(name.split()) == 2 and name.split()[1] == 'University':
                    id2uni[name.split()[0]] = name
            else:
                for u in us:
                    name = u.strip().replace(' $', '').replace(' @ ', ', ')
                    if name in avoid_list:
                        continue
                    if '$' in u:
                        id2uni[row[0].strip()] = name
                        if len(name.split()) == 2 and name.split()[1] == 'University':
                            id2uni[name.split()[0]] = name
                    universities.append(name)
    return universities, id2uni


def load_general_universities(world_universities_and_domains_path):
    universities = []
    with open(world_universities_and_domains_path, 'r') as f:
        j = json.load(f)
        for x in j:
            if x['country'] == 'United States':
                universities.append(x['name'])
        return universities


def get_top_and_other_universities_fullname(id2uni, universities_top_list_path):
    """Load a comprehensive list of world universities names from
     https://github.com/Hipo/university-domains-list/
    Return the top 100 CS ranking universities and others.
    Update the id2uni mapping.

    Parameters
    ----------
    id2uni : dict
        Dict of mapping uid -> university fullname
    universities_top_list_path : str
        Path of universities_top_list_path.json

    Returns
    -------
    tuple
        (top_universities, other_universities)
    """
    top_universities, other_universities = [], []

    with open(universities_top_list_path, 'r') as f:
        top_universities = f.readlines()
        top_universities = [u.replace('\u200b', '').strip() for u in top_universities]
        for top_u in top_universities:
            if len(top_u.split()) == 2 and top_u.split()[1] == 'University':
                id2uni[top_u.split()[0]] = top_u
        other_universities = []
        for u in universities:
            if u not in top_universities and u not in avoid_list:
                # if u not in top_universities:
                other_universities.append(u)
    return top_universities, other_universities


if __name__ == "__main__":
    # Load US universities UID (abbreviation) mapping list
    universities, id2uni = load_universities_with_uids(os.path.join(DATA_DIR, 'us/us_universities_uids.csv'))
    id2uni = collections.OrderedDict(sorted(id2uni.items()))
    uni2id = collections.defaultdict(list)

    # Load general university list
    universities.extend(load_general_universities(os.path.join(DATA_DIR, 'us/world_universities_and_domains.json')))

    # Load top 100 and other universities
    top_universities, other_universities = get_top_and_other_universities_fullname(id2uni, os.path.join(DATA_DIR, 'us/us_cs_top_list.txt'))

    # Dict for university name -> university id
    for k, v in id2uni.items():
        uni2id[v].append(k)

    top_uid2name = collections.OrderedDict()
    other_uid2name = collections.OrderedDict()

    # Build Top university uid -> Top university fullname
    for uni in top_universities:
        if uni in uni2id:
            for uid in uni2id[uni]:
                top_uid2name[uid] = uni
                if uni.endswith('State University'):
                    tmp = uni.replace('State University', 'State')
                    top_uid2name[tmp] = uni

    # Build Other university uid -> Other university fullname
    for uni in uni2id:
        if uni not in top_universities:
            for uid in uni2id[uni]:
                other_uid2name[uid] = uni
            if uni not in other_universities:
                other_universities.insert(0, uni)

    # Dump to final result
    with open(os.path.join(DATA_DIR, 'us/us_universities_top.json'), 'w') as target:
        json.dump({'top_100_uid': top_uid2name, 'other_uni_uid': other_uid2name, 'top_100_names': top_universities,
                   'other_uni_names': list(set(other_universities))}, target, indent=2, ensure_ascii=False)
