from config.settings import DATA_DIR, ARTICLE_TYPE
import copy
import re
import numpy as np
import pandas as pd
import pprint
import textdistance
import os
import json
import collections
from utils.programs import Programs
pp = pprint.PrettyPrinter()


class Background:
    def find_university(self): raise NotImplementedError("Override me")
    def find_major(self): raise NotImplementedError("Override me")


class TWBackground(Background):
    def __init__(self):
        # TW universities
        self.universities = pd.read_csv(os.path.join(DATA_DIR, 'tw/tw_universities.csv'), sep='|', index_col='uni_id')
        self.universities['ip'] = self.universities['ip'].map(lambda x: str(int(x)) if not pd.isnull(x) else None)
        self.universities = self.universities.where(self.universities.notnull(), None)
        self.uid2cname = self.universities.to_dict()['uni_cname']
        self.cabbr2uid = {cabbr: uid for cabbr, uid in zip(self.universities['uni_cabbr'], self.universities.index) if cabbr is not None}
        self.cname2uid = {cname: uid for cname, uid in zip(self.universities['uni_cname'], self.universities.index) if cname is not None}
        self.name2uid = {name: uid for name, uid in zip(self.universities['uni_name'], self.universities.index) if name is not None}
        self.ip2uid = {str(int(ip)): uid for ip, uid in zip(self.universities['ip'], self.universities.index) if ip is not None}

        # Majors
        self.majors = pd.read_csv(os.path.join(DATA_DIR, 'tw/majors.csv'), sep=',', index_col='major_id', na_values=None)
        self.mid2name = self.majors.to_dict()['major_cname']
        self.cabbr2mid = {cabbr: mid for cabbr, mid in zip(self.majors['major_cabbr'], self.majors.index)}
        self.cname2mid = {cname: mid for cname, mid in zip(self.majors['major_cname'], self.majors.index)}
        self.name2mid = {name: mid for name, mid in zip(self.majors['major_name'], self.majors.index)}
        self.mid2mtype = {mid: mtype for mtype, mid in zip(self.majors['major_type'], self.majors.index)}

        # Background keywords
        self.background_keywords = ('background', 'education', '經歷', '學歷', 'academic record')
        self.gpa_keywords = ('GPA', 'Rank', ' Education', 'Background')
        self.debug_id = 'M.1330716022.A.D49'

    def find_university(self, content, aid=None):
        def helper(matched_word=None, university_row_index=None, uni_id=None, background_row_idx=None):
            """Helper function to return the result as a json object"""
            return locals()
        content = copy.deepcopy(content)
        rows = content.split('\n')

        # We try to find the "Background" keywords to identify the university
        background_row_idx = None
        for idx, row in enumerate(rows):
            s = re.search(r'(' + '|'.join(self.background_keywords) + ')', row, flags=re.IGNORECASE)
            if s is not None:
                background_row_idx = idx
                break
        search_range = [i for i in range(0, len(rows))]

        # Rotate the array so we start the search from the background section
        if background_row_idx is not None:
            search_range = search_range[background_row_idx:] + search_range[:background_row_idx]

        # Search row by row in search range
        for ridx in search_range:
            row = rows[ridx]
            uni, word = self.sentence2university(row)
            if uni:
                return helper(word, ridx, uni, background_row_idx)
        return None

    def sentence2university(self, sentence):
        ntu_siblings = ('NTUT', 'NTUST')
        for word in sentence.strip().split():
            # Exact match of university chinese name
            if word in self.cname2uid:
                return self.cname2uid[word], word
            # Exact match of university chinese abbreviation
            elif word in self.cabbr2uid:
                return self.cabbr2uid[word], word
            # NTU special cases
            elif ('NTU' in word and all([x not in word for x in ntu_siblings])) or '台灣大學' in word or '臺灣大學' in word:
                return 'NTU', word
            # Exact match uid
            elif word.upper() in self.uid2cname:
                return word.upper(), word
            elif word in self.ip2uid:
                return self.ip2uid[word], word
            else:
                # uid in word (e.g. 'NTU' in 'NTUEE')
                ruid = re.findall(r'(' + '|'.join(self.uid2cname.keys()) + ')(?!.)', word)
                # Filter False positive Hsinchu -> NCHU
                if ruid and word != 'Hsinchu':
                    return ruid[0].upper(), word
                # Chinese abbr. in word (e.g. '台大' in '台大電機')
                rabbr = re.findall(r'(' + '|'.join(self.cabbr2uid.keys()) + ')', word)
                if rabbr:
                    return self.cabbr2uid[rabbr[0]], word
        # Check if university English name in row
        for name in self.name2uid:
            if name in sentence:
                return self.name2uid[name], word
        return None, None

    def find_major(self, content, university, aid=None):
        if aid == self.debug_id:
            print(aid)
        content = copy.deepcopy(content)
        rows = content.split('\n')

        # Define the range of rows we are going to search,  where we usually start from the the "background_row_idx"
        start_row_index = university['background_row_idx'] if university is not None and university['background_row_idx'] is not None else 0
        end_row_index = min(len(rows), university['university_row_index'] + 4) if university is not None else len(rows)
        search_range = list(range(start_row_index, end_row_index))
        # We search the "university_row_index" row first, e.g. NTU EE
        if university is not None:
            search_range = [university['university_row_index']] + search_range

        # Search row by row in search range
        for ridx in search_range:
            row = rows[ridx]
            major = self.sentence2major(row, university)
            if major:
                return major
        return None

    def sentence2major(self, sentence, university=None):
        sentence = re.sub(r'(student|TOEFL|GRE)', ' ', sentence, flags=re.IGNORECASE)
        # Check if major English name in row
        for name in self.name2mid:
            if name in sentence:
                return self.name2mid[name]

        # We now determine the start idx we parse from the row!
        # 1) Major is often listed after/before university, check if we are at the same row
        start_idx = 0
        if university is not None and university['matched_word'] in sentence:
            start_idx = max(sentence.index(university['matched_word']) - 10, 0)
        # 2) Major is often listed after the background keywords, check if the keyword exists
        s = re.search(r'(' + '|'.join(self.background_keywords) + ')', sentence, re.IGNORECASE)
        # 3) Set the start index
        if s is not None:
            start_idx = min(start_idx, s.end())

        # Search after the start_idx (e.g. After university or background)
        sentence = sentence[start_idx:]
        sentence = re.sub(r'[.,:;/()]', ' ', sentence)

        for word in sentence.strip().split():

            # Exact match of major chinese name
            if word in self.cname2mid:
                return self.cname2mid[word]
            # Exact match of major chinese abbreviation
            elif word in self.cabbr2mid:
                return self.cabbr2mid[word]
            # Exact match mid, and word != 'BA' (Bachelor's of Art)
            elif word.upper() in self.mid2name and word.upper() != 'BA':
                return word.upper()
            else:
                # mid in word (e.g. 'EE' in 'NTUEE')
                rmid = re.findall(r'(' + '|'.join(self.mid2name.keys()) + ')(?!.)', word)
                # Filter False positive ENT (Entomology) and word != 'BA' (Bachelor's of Art)
                if rmid and (rmid[0] != 'ent' or re.match(r' ent', word)) and rmid[0] != 'BA':
                    return rmid[0].upper()
                # cabbr in word (e.g. '電機' in '台大電機系')
                rabbr = re.findall(r'(' + '|'.join(self.cabbr2mid.keys()) + ')', word, re.IGNORECASE)
                if rabbr:
                    return self.cabbr2mid[rabbr[0]]
        return None

    def find_gpa(self, content, university, aid=None):
        content = copy.deepcopy(content)
        rows = content.split('\n')
        gpa_scale = -1
        gpa_keyword_in_row_idx = None
        background_row_idx = university['background_row_idx'] if university is not None else None
        candidates = []
        for idx, row in enumerate(rows):
            # Check if GPA and GRE keyword in row
            gpa_keyword_in_row = re.search(r'(' + '|'.join(self.gpa_keywords) + ')', row, re.IGNORECASE)
            if gpa_keyword_in_row:
                gpa_keyword_in_row_idx = idx

            # See if GRE is in row
            gre_in_row = re.search(r'(GRE|G:|G |AW|V1|Q1|V 1|Q 1|V:|Q:)', row, re.IGNORECASE)

            # If GRE and GPA co-occur in the same row, remove the GRE part
            if gre_in_row and gpa_keyword_in_row:
                if gre_in_row.start() > gpa_keyword_in_row.end():
                    row = row[:gre_in_row.start()]
                elif gre_in_row.end() < gpa_keyword_in_row.start():
                    row = row[gpa_keyword_in_row.start():]

            # Get AW index if exists
            # aw_idx = row.index('AW') if 'AW' in row else aw_idx

            # Parse the float numbers in the current row through regex
            year_regex = r'[2][0-9]{3}'
            row = re.sub(year_regex, ' ', row)

            float_numbers = re.finditer(r'\d+\.\d+', row)
            # Only search rows that are "GPA_keyword" rows
            if gpa_keyword_in_row is not None or (gpa_keyword_in_row_idx is not None and idx - gpa_keyword_in_row_idx <= 1):
                for m in float_numbers:
                    num = float(row[m.start(0): m.end(0)])
                    # Skip AW (e.g. AW 3.5) to avoid "Fake" GPA results
                    if num in np.arange(1, 6.5, 0.5) and gre_in_row:
                        continue
                    # We expect the GPA number be in the range (0, 4.3)
                    if num < 0.001 or num > 4.31:
                        continue
                    # Ugly but efficient way to get the GPA scale...
                    if np.isclose(num, 4.0) and ('/4.0' in row or '/ 4.0' in row):
                        gpa_scale = 4.0
                    elif np.isclose(num, 4.3) and ('/4.3' in row or '/ 4.3' in row):
                        gpa_scale = 4.3
                    else:
                        candidates.append(num)
                # Don't forget that people are just too good!
                if '4.3/' in row or '4.3 /' in row:
                    candidates.append(4.3)
                elif '4.0/' in row or '4.0 /' in row:
                    candidates.append(4.0)

            # We stop searching if we are too far away from background section
            if background_row_idx is not None and idx - university['background_row_idx'] > 20:
                break

        # Return parsed GPA
        if len(candidates) > 0:
            return {'max_gpa': np.max(candidates), 'min_gpa': np.min(candidates),
                    'mean_gpa': np.round(np.mean(candidates), 2), 'gpa_scale': gpa_scale}
        else:
            return {'max_gpa': -1, 'min_gpa': -1, 'mean_gpa': -1, 'gpa_scale': -1}


class USBackground(Background):
    def __init__(self):
        self.ad_reg = r'(admit|admission|admision|accept|appected|ad |ad:|offer|錄取)'
        self.rej_reg = r'(reject|rejection|rejection:|rej|rej:|拒絕|打槍)'
        self.pending_reg = r'(pending|waitlist|wl |wl:|無聲|無消息)'
        self.useless_reg = r'w\/|w\/o|funding|without|with|stipend|tuition|waived|waive|waiver|fellowship| RA|email|e-mail|year|month|date|interviewed|\
                                decision|semester|first|for | per| technical|nomination| by | out|\(|\)'
        self.ascii_reg = r'[^\x00-\x7F]+'
        # self.debug_id = "M.1272871982.A.BF1"
        self.debug_id = None

        # Load Universities
        with open(os.path.join(DATA_DIR, 'us/us_universities_top.json'), 'r') as f:
            self.us_universities = json.load(f)

        # Init a set of all university names
        self.all_uni_names = set(self.us_universities['top_100_names'] + self.us_universities['other_uni_names'])

        # Setup university name to Uid mapping
        self.uname2uid = collections.defaultdict(list)
        for uid in self.us_universities['top_100_uid']:
            self.uname2uid[self.us_universities['top_100_uid'][uid]].append(uid)
        for uid in self.us_universities['other_uni_uid']:
            self.uname2uid[self.us_universities['other_uni_uid'][uid]].append(uid)

        # Init Programs instance
        self.programs = Programs()

    def normalize_university_name(self, words):
        if words.startswith('U '):
            words = words.replace('U ', 'University of ')
        words = words.replace('U. ', 'University of ') if 'of' not in words else words.replace('U. ', 'University ')
        words = words.replace('U of ', 'University of ')
        words = words.replace('Univ ', 'University')
        words = words.replace('UC-', 'UC ')
        words = words.replace('University of California,', 'University of California ')
        r = re.search(r'\w*State U\b', words)
        if r:
            words = words[: r.start()] + 'State University' + words[r.end():]

        r = re.search(r'\w*Univ.\b', words, flags=re.IGNORECASE)
        if r:
            words = words[: r.start()] + 'University' + words[r.end():]

        # Purify some random words:
        r = r'no|yr|ta|ra|ms'
        if len(words) == 2 and re.search(r, words, flags=re.IGNORECASE):
            words = ''
        return words

    def search_single_university_name(self, ad_row):
        for uname in self.us_universities['top_100_names']:
            if re.search(uname, ad_row, flags=re.IGNORECASE):
                return uname
        ad_row = ' ' + ad_row + ' '
        for uid in self.us_universities['top_100_uid']:
            if ' ' + uid + ' ' in ad_row:
                return self.us_universities['top_100_uid'][uid]
        ad_row = ad_row.strip()
        # ^([a-zA-Z\s]* )?apple( [a-zA-Z\s]*)?$

        for uname in self.us_universities['other_uni_names']:
            if re.search(uname, ad_row, flags=re.IGNORECASE):
                return uname

        # Search for university fullnames with high LCS similarity
        # The fullname should be at least 10 characters
        if len(ad_row) >= 10:
            td_names = []
            for uname in self.us_universities['top_100_names']:
                td = textdistance.lcsseq.similarity(uname, ad_row) / min(len(ad_row), len(uname))
                if td > 0.75:
                    td_names.append((td, uname))
            if td_names:
                return max(td_names)[1]

        for uid in self.us_universities['other_uni_uid']:
            if re.search(r'(?:^|(?<= ))(' + uid + ')(?:(?= )|$)', ad_row):
                return self.us_universities['other_uni_uid'][uid]

        return None

    def search_all_university_names(self, article_title):
        result = []
        for uname in self.us_universities['top_100_names']:
            if re.search(uname, article_title, flags=re.IGNORECASE):
                result.append(uname)
        article_title = ' ' + article_title + ' '
        for uid in self.us_universities['top_100_uid']:
            if ' ' + uid + ' ' in article_title:
                result.append(self.us_universities['top_100_uid'][uid])

        for uname in self.us_universities['other_uni_names']:
            if re.search(uname, article_title, flags=re.IGNORECASE):
                result.append(uname)

        for uid in self.us_universities['other_uni_uid']:
            if ' ' + uid + ' ' in article_title:
                result.append(self.us_universities['other_uni_uid'][uid])
        article_title = article_title.strip()

        if 'Cornell Tech' in result and 'Cornell University' in result:
            result.remove('Cornell University')
        return result

    def parse_admission_section(self, articles):
        def helper_get_end_idx_and_reg(rej_idx, pending_idx):
            """
            Given indices for reject and pending rows,
            return the right one as the ending index

            Returns
            -------
            (int, regex)
                Return a tuple of index and specified regex
            """
            if rej_idx is None and pending_idx is None:
                return None, None
            elif rej_idx is not None and pending_idx is None:
                return rej_idx, self.rej_reg
            elif rej_idx is None and pending_idx is not None:
                return pending_idx, self.pending_reg
            else:
                return (rej_idx, self.rej_reg) if rej_idx <= pending_idx else (pending_idx, self.pending_reg)

        ad_count = 0
        result = []
        for article in articles:
            if self.debug_id and article['article_id'] != self.debug_id:
                continue
            # Parse AD programs from title
            article_title = article['article_title'].replace('[錄取]', '')
            article_title = re.sub(self.ascii_reg, ' ', article_title)
            article_title = re.sub(self.useless_reg, ' ', article_title, flags=re.IGNORECASE)
            ad_title = re.split(r'[:;/(),\[\]]', article_title)
            ad_title = [r.strip() for r in ad_title if len(r.strip()) > 1]

            # Parse AD section from content
            content = article['content']
            rows = copy.deepcopy(content.split('\n'))
            ad_idx = None
            rej_idx = None
            pending_idx = None

            # Find the index for "ADMISSION", "REJECT" and "PENDING" rows
            for ridx, row in enumerate(rows):
                if re.search(self.ad_reg, row, flags=re.IGNORECASE) and (
                        (rej_idx is None or ridx <= rej_idx) and (pending_idx is None or ridx <= pending_idx)):
                    ad_idx = ridx
                if re.search(self.rej_reg, row, flags=re.IGNORECASE) and (rej_idx is None or (
                        ad_idx is not None and rej_idx <= ad_idx and ridx <= ad_idx + 4)):
                    rej_idx = ridx
                if re.search(self.pending_reg, row, flags=re.IGNORECASE) and (pending_idx is None or (
                        ad_idx is not None and pending_idx <= ad_idx and ridx <= ad_idx + 4)):
                    pending_idx = ridx

            # Replace non ASCII characters with 'blank'
            rows = [re.sub(self.ascii_reg, ' ', row) for row in rows]

            if article['article_id'] == self.debug_id:
                print('parsed index', ad_idx, rej_idx, pending_idx)
                # pp.pprint(rows)

            ad_list = []
            end_idx, end_reg = helper_get_end_idx_and_reg(rej_idx, pending_idx)
            if ad_idx is not None and end_idx is not None:
                break_flag = False
                for idx in range(ad_idx, end_idx + 1):
                    row = rows[idx]

                    # Scrap "Admission:" from the row
                    ad_match = re.search(self.ad_reg, row, flags=re.IGNORECASE)
                    if ad_match:
                        row = row[:ad_match.start()] + row[ad_match.end():]

                    # Scrap "Reject:" or "Pending:" from the row, and break after this row
                    end_match = re.search(end_reg, row, flags=re.IGNORECASE)
                    if end_match:
                        row = row[:end_match.start()]
                        break_flag = True

                    # Remove date
                    date_reg = re.findall(r'\d+\/\d+', row)
                    for date in date_reg:
                        row = row.replace(date, ' ')

                    # Remove useless stuff, eg. w or w/o funding
                    row = re.sub(self.useless_reg, ' ', row, flags=re.IGNORECASE)

                    # If there is only one comma, it is most likely the row only
                    # contains one university, e.g. 'MIT, EECS'
                    if row.count(',') <= 2:
                        row = row.replace(',', ' ')

                    # Split programs! e.g. 'MIT / CMU -> ['MIT', 'CMU']
                    row = re.split(r'[:;,/\[\]]', row)

                    # Keep rows with length > 1
                    row = [r.strip() for r in row if len(r.strip()) > 1]
                    ad_list.extend(row)

                    # Break if we reach the end (reject/pending row)
                    if break_flag:
                        break
            # Count how many aritlces with AD successively parsed
            if len(ad_list) > 0:
                ad_count += 1
            result.append({'article_id': article['article_id'], 'article_title': article['article_title'],
                           'url': article['url'], 'admission_title': ad_title, 'admission': ad_list})
        print(f'Found {ad_count} articles with admission section')
        return result

    def find_university(self, ad_results, articles=None, update=True):
        def hash_program_uni_pair(x):
            a = x['program_level'] if x['program_level'] else ''
            b = x['program_name'] if x['program_name'] else ''
            c = x['university'] if x['university'] else ''
            return a + '@' + b + '@' + c

        result = []
        debug_ads = []
        # Iterate the raw ad_results
        for idx, article in enumerate(ad_results):
            if self.debug_id and article['article_id'] != self.debug_id:
                continue
            # Parse university and programs from admission sections
            parsed_admission_results = []
            d1 = []

            parsed_program_uni_pairs = []
            parsed_program_names = []
            parsed_program_levels = []
            debug_rows = []
            parsed_uni_pair_set = set()
            for i, row in enumerate(article['admission']):
                row = self.normalize_university_name(row)
                debug_rows.append(row)

                if not row:
                    continue

                # Parse program from this row
                (program_level, program_name), row_new = self.programs.search_program(row, aid=article['url'])
                if program_level is not None:
                    parsed_program_levels.append(program_level)
                if program_name is not None:
                    parsed_program_names.append(program_name)

                # No university left to search in row
                if len(row_new) == 0:
                    continue

                # Find university in article admission section
                uni_match = self.search_single_university_name(row_new)
                # print('Norm', row, '@', uni_match, '@', program_level, program_name)

                # If we found a university, add to `parsed_admission_results`
                if uni_match is not None:
                    # Map parsed results to uni names
                    parsed_admission_results.append(uni_match)
                    d1.append((row, uni_match))
                else:
                    # parsed_admission_results.append(None)
                    d1.append((row, ''))

                if (program_name or program_level) and uni_match:
                    parsed_program_uni_pairs.append(
                        {
                            'program_level': program_level,
                            'program_name': program_name,
                            'university': uni_match
                        }
                    )
                    parsed_uni_pair_set.add(uni_match)

            parsed_admission_title_results = []
            parsed_program_names_from_title = []
            parsed_program_levels_from_title = []
            d2 = []

            # If we passed articles into the function, we try to parse the article title
            if articles is not None:
                for ad_title in article['admission_title']:

                    # Parse program from title
                    (program_level, program_name), ad_title_new = self.programs.search_program(ad_title)
                    if program_level is not None:
                        parsed_program_levels_from_title.append(program_level)
                    if program_name is not None:
                        parsed_program_names_from_title.append(program_name)
                    ad_title_new = self.normalize_university_name(ad_title_new)
                    if not ad_title_new:
                        continue

                    # Find university in article title
                    uni_matches = self.search_all_university_names(ad_title_new)

                    # If we found a university, add to `parsed_admission_title_results`
                    if uni_matches:
                        parsed_admission_title_results.extend(uni_matches)
                        d2.append((ad_title, uni_matches))
                    else:
                        d2.append((ad_title, ''))

            # Combine admission results from "title" + "section"
            parsed_admission_results.extend(parsed_admission_title_results)
            parsed_admission_universities = list(set(parsed_admission_results))

            # Fill in program name and levels if not found in `parsed_program_uni_pairs` but in title
            if parsed_program_levels_from_title or parsed_program_levels:
                program_level = parsed_program_levels_from_title[0] if parsed_program_levels_from_title else parsed_program_levels[0]
                for pair in parsed_program_uni_pairs:
                    if pair['program_level'] is None:
                        pair['program_level'] = program_level

            if parsed_program_names_from_title or parsed_program_names:
                program_name = parsed_program_names_from_title[0] if parsed_program_names_from_title else parsed_program_names[0]
                for pair in parsed_program_uni_pairs:
                    if pair['program_name'] is None:
                        pair['program_name'] = program_name
            # Hash parsed_program_uni_pairs to set to prevent duplicate parsed_program_uni_pairs
            uni_pairs_set = set()
            for pair in parsed_program_uni_pairs:
                uni_pairs_set.add(hash_program_uni_pair(pair))

            # Fill in Universities with no program level or program name associated
            universities_without_programs = set(parsed_admission_universities) - parsed_uni_pair_set
            for uni in universities_without_programs:
                # Fill in from title
                program_level = parsed_program_levels_from_title[0] if parsed_program_levels_from_title else None
                program_name = parsed_program_names_from_title[0] if parsed_program_names_from_title else None
                # No program level from title, try to fill in from admission results
                program_level = parsed_program_levels[0] if not program_level and parsed_program_levels else program_level
                program_name = parsed_program_names[0] if not program_name and parsed_program_names else program_name
                uni_pair = {
                    'program_level': program_level,
                    'program_name': program_name,
                    'university': uni
                }
                if hash_program_uni_pair(uni_pair) not in uni_pairs_set:
                    uni_pairs_set.add(hash_program_uni_pair(uni_pair))
                    parsed_program_uni_pairs.append(uni_pair)

            # Merge program levels / names from title
            parsed_program_levels.extend(parsed_program_levels_from_title)
            parsed_program_names.extend(parsed_program_names_from_title)

            # Append universities/programs to result
            result.append({
                'admission_universities': parsed_admission_universities,
                'program_levels': list(set(parsed_program_levels)),
                'program_names': list(set(parsed_program_names)),
                'program_uni_pairs': parsed_program_uni_pairs
            })

            # For debug purpose
            """
            debug_ads.append({
                'article_title': articles[idx]['article_title'], 'url': articles[idx]['url'],
                'program_levels': list(set(parsed_program_levels)),
                'program_names': list(set(parsed_program_names)),
                'program_title_levels': parsed_program_levels_from_title,
                'program_title_names': parsed_program_names_from_title,
                'program_uni_pairs': parsed_program_uni_pairs,
                'debug_rows': debug_rows
            })
            """

        # For debug purpose
        # with open(os.path.join(DATA_DIR, 'debug_ad.json'), 'w') as target:
        #     json.dump(debug_ads, target, indent=2, ensure_ascii=False)
        print(f'Parsed {len(result)} admission articles')
        return result

    def map_university_token_to_fullname(self, uni):
        # Deprecated for now
        if uni in self.all_uni_names:
            return uni
        elif uni in self.us_universities['top_100_uid']:
            return self.us_universities['top_100_uid'][uni]
        elif uni in self.us_universities['other_uni_uid']:
            return self.us_universities['other_uni_uid'][uni]
        raise Exception('Should not reach here, university not found')
