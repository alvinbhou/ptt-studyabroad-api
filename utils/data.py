# -*- coding: utf-8 -*-
from config.settings import DATA_DIR, OUTPUT_DIR, ARTICLE_TYPE
import csv
import json
import gc
import os
import re
import time
import numpy as np
import pandas as pd
import pprint
import copy
import textdistance
from datetime import datetime
from utils.background import TWBackground, USBackground
from utils.programs import Programs
from api.database import create_tables_and_dump_data

pp = pprint.PrettyPrinter()


class DataModel:
    def __init__(self, all_articles=[]):
        self.all_articles = np.array(all_articles)
        self.cs_article_indices = []
        self.admission_article_indices = []
        self.ask_article_indices = []
        # CS related keywords (CS/DS/ML/HCI/CV/NLP/Robotics/Stats)
        self.cs_keywords = ['eecs', 'ece', 'cs', 'ee', 'ds', 'ml', 'stat', 'mscv', ' ce ', ' se ',
                            'cmusv', 'cmu-sv', ' sv', 'hci', 'nlp', 'robotics', 'computer science']
        # False positive keywords
        self.fp_keywords = ['cheers', 'physics', 'ucs.', 'csu', 'facebook', 'indeed', 'fee', 'cec', 'economics', 'mlb', 'mli', 'emle', 'emlyon', 'need',
                            'career', 'sva', 'milwaukee', 'leeds', 'records', 'sdsu', 'ds2019', 'ds2016', 'kids', 'state']
        self.tw_background = TWBackground()
        self.us_background = USBackground()
        self.programs = Programs()

        # Information of the author of the articles
        self.universities = []
        self.majors = []
        self.gpas = []

    @classmethod
    def from_processed_data(cls, ptt_data_path):
        with open(ptt_data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return DataModel(all_articles=data['articles'])

    def load_and_clean_ptt_data(self, ptt_data_path, save_path=None):
        with open(ptt_data_path, 'r', encoding='utf-8') as f:
            self.all_articles = json.load(f)

        article_id_set = set()
        # Clean up the data, remove comments, messages, message_count, board  and ips
        for article in self.all_articles['articles']:
            if 'article_id' in article and article['article_id'] in article_id_set:
                article['error'] = 'duplicate_id'
            if 'ip' in article:
                del article['ip']
            if 'message_count' in article:
                del article['message_count']
            if 'messages' in article:
                del article['messages']
            if 'board' in article:
                del article['board']
            try:
                article['date'] = datetime.strptime(article['date'], '%a %b %d %H:%M:%S %Y').strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, KeyError) as e:
                article['date'] = datetime(1970, 1, 1).strftime("%Y-%b-%d %H:%M:%S")

            if 'article_id' in article:
                article_id_set.add(article['article_id'])
        self.all_articles['articles'] = [article for article in self.all_articles['articles'] if 'error' not in article]
        # Save data
        if save_path:
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(self.all_articles, f, ensure_ascii=False)
        # We only need the articles array
        self.all_articles = np.array(self.all_articles['articles'])

    def classify_articles(self):
        self.cs_article_indices, self.admission_article_indices, self.ask_article_indices = [], [], []
        for idx, article in enumerate(self.all_articles):
            if 'article_title' not in article or article['article_title'] is None:
                continue
            article_title = article['article_title']
            if re.match(r'.*(' + '|'.join(self.cs_keywords) + ').*', article_title, re.IGNORECASE):
                # Ignore false positive, CEE and "* engineer" ones
                if (re.match(r'.*(' + '|'.join(self.fp_keywords) + ').*', article_title,
                             re.IGNORECASE) and self.get_occurrence_count(self.cs_keywords, article_title) < 2) or \
                        re.match(r'.*( CEE|CEEB|civil and environmental engineering).*', article_title, re.IGNORECASE) or \
                        re.match(r'^(?!.*(electrical engineer|computer engineer|software engineer)).*engineer.*$', article_title, re.IGNORECASE):
                    continue
                if ARTICLE_TYPE.ADMISSION.value in article_title and 'Re: ' not in article_title:
                    self.admission_article_indices.append(idx)
                    article['article_type'] = ARTICLE_TYPE.ADMISSION.name
                elif ARTICLE_TYPE.ASK.value in article_title:
                    self.ask_article_indices.append(idx)
                    article['article_type'] = ARTICLE_TYPE.ASK.name
                else:
                    article['article_type'] = ARTICLE_TYPE.GENERAL_CS.name
                self.cs_article_indices.append(idx)
            else:
                article['article_type'] = ARTICLE_TYPE.ALL.name

    def parse_university_major_gpa(self):
        indices = self.cs_article_indices
        # Parse universities
        for article in self.all_articles[indices]:
            content = article['content']
            university = self.tw_background.find_university(content, aid=article['article_id'])
            self.universities.append(university)
        # Parse majors
        for idx, article in enumerate(self.all_articles[indices]):
            content = article['content']
            major = self.tw_background.find_major(content, self.universities[idx], aid=article['article_id'])
            self.majors.append(major)
        # Parse GPA
        for idx, article in enumerate(self.all_articles[indices]):
            content = article['content']
            gpa = self.tw_background.find_gpa(content, self.universities[idx], aid=article['article_id'])
            self.gpas.append(gpa)

        def count_none_null(arr): return sum([1 for x in arr if x])
        uni_count, gpa_count, major_count = count_none_null(self.universities), count_none_null(self.gpas), count_none_null(self.majors)
        pp.pprint(f'Parsed {uni_count} universities, {major_count} majors, and {gpa_count} GPAs')

        # Save the parsed results to the articles
        for idx, article in enumerate(self.all_articles[self.cs_article_indices]):
            if self.universities[idx] is not None:
                d = {}
                d.update(self.universities[idx])
                # Get the University info based on the 'uid'
                d.update(self.tw_background.universities.loc[self.universities[idx]['uni_id']].to_dict())
                # Remove unnecessary attributes
                for k in ('university_row_index', 'background_row_idx', 'matched_word'):
                    d.pop(k, None)
                article['university_info'] = d
            if self.majors[idx] is not None:
                d = {'major_id': self.majors[idx]}
                d.update(self.tw_background.majors.loc[self.majors[idx]].to_dict())
                article['major_info'] = d
            if self.gpas[idx] is not None:
                article['gpa_info'] = self.gpas[idx]

    def parse_admission_programs(self):
        print('Parsing admission programs for all CS admission articles...')
        # We only parse the admission articles
        indices = self.admission_article_indices

        # Parse the admission section
        raw_ad_results = self.us_background.parse_admission_section(self.all_articles[indices])

        # Parse the university and program
        result = self.us_background.find_university(raw_ad_results, articles=self.all_articles[indices])

        # Save the parsed result to the articles
        for idx, article in enumerate(self.all_articles[indices]):
            article['admission_info'] = result[idx]

    def get_articles(self, type=ARTICLE_TYPE.ALL):
        if type == ARTICLE_TYPE.ALL:
            return self.all_articles
        elif type == ARTICLE_TYPE.CS:
            return self.all_articles[self.cs_article_indices]
        elif type == ARTICLE_TYPE.ASK:
            return self.all_articles[self.ask_article_indices]
        elif type == ARTICLE_TYPE.ADMISSION:
            return self.all_articles[self.admission_article_indices]
        else:
            raise Exception('Unknown Article Type')

    def save_classified_articles(self, verbose=True):
        if verbose:
            with open(os.path.join(OUTPUT_DIR, 'cs_articles.json'), 'w', encoding='utf-8') as f:
                json.dump({'articles': list(self.all_articles[self.cs_article_indices])}, f, ensure_ascii=False, indent=2)
            with open(os.path.join(OUTPUT_DIR, 'admission_articles.json'), 'w', encoding='utf-8') as f:
                json.dump({'articles': list(self.all_articles[self.admission_article_indices])}, f, ensure_ascii=False, indent=2)
            with open(os.path.join(OUTPUT_DIR, 'ask_articles.json'), 'w', encoding='utf-8') as f:
                json.dump({'articles': list(self.all_articles[self.ask_article_indices])}, f, ensure_ascii=False, indent=2)
        with open(os.path.join(OUTPUT_DIR, 'all_articles.json'), 'w', encoding='utf-8') as f:
            json.dump({'articles': list(self.all_articles)}, f, ensure_ascii=False, indent=2)

    def load_all_articles(self):
        with open(os.path.join(OUTPUT_DIR, 'all_articles.json'), 'r', encoding='utf-8') as f:
            self.all_articles = np.array(json.load(f)['articles'])

    def dump_articles_to_csv(self):
        # Additional info
        additional_info = ['major_info', 'gpa_info', 'admission_info']

        # Gather column names for general header
        general_keys = [k for k in self.all_articles[self.cs_article_indices][-1].keys() if k not in additional_info]
        university_info_keys = [self.tw_background.universities.index.name] + \
            [k for k in self.tw_background.universities.columns.tolist() if k != 'ip']
        major_info_keys = [self.tw_background.majors.index.name] + self.tw_background.majors.columns.tolist()
        gpa_keys = ['max_gpa', 'min_gpa', 'mean_gpa', 'gpa_scale']

        general_header = copy.deepcopy(general_keys)
        general_header.extend(university_info_keys)
        general_header.extend(major_info_keys)
        general_header.extend(gpa_keys)
        # print(general_header)

        with open(os.path.join(OUTPUT_DIR, 'cs_articles.csv'), 'w', newline='', encoding='utf - 8') as csvfile:
            writer = csv.writer(csvfile, delimiter='|')
            writer.writerow(general_header)

            for article in self.all_articles[self.cs_article_indices]:
                assert 'error' not in article, article
                row = []
                # General stuff
                for k in general_keys:
                    if k != 'content':
                        row.append(article[k].replace('|', ' ') if article[k] else None)
                    else:
                        tmp = article[k].replace('\n', '\\n').replace('|', ' ')
                        row.append(tmp)
                # University stuff
                if 'university_info' in article:
                    for k in university_info_keys:
                        row.append(article['university_info'][k])
                else:
                    row.extend([''] * len(university_info_keys))
                # Major stuff
                if 'major_info' in article:
                    for k in major_info_keys:
                        row.append(article['major_info'][k])
                else:
                    row.extend([''] * len(major_info_keys))
                # GPA stuff
                if 'gpa_info' in article:
                    for k in gpa_keys:
                        row.append(article['gpa_info'][k])
                else:
                    row.extend([''] * len(gpa_keys))

                writer.writerow(row)

        with open(os.path.join(OUTPUT_DIR, 'admission_universities.csv'), 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile, delimiter='|')
            writer.writerow(['article_id', 'university'])
            for article in self.all_articles[self.admission_article_indices]:
                if 'admission_info' in article:
                    for uni in article['admission_info']['admission_universities']:
                        writer.writerow([article['article_id'], uni])
        with open(os.path.join(OUTPUT_DIR, 'admission_uni_and_programs.csv'), 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile, delimiter='|')
            writer.writerow(['article_id', 'university', 'program_level', 'program', 'program_type'])
            for article in self.all_articles[self.admission_article_indices]:
                uni_program_set = set()
                if 'admission_info' in article:
                    for pair in article['admission_info']['program_uni_pairs']:
                        university, program_level, program_name = pair['university'], pair['program_level'], pair['program_name']
                        program_name_norm = self.programs.normalize_program_name(program_level, program_name)
                        k = university + '@' + program_name_norm if program_name_norm else university + '@'
                        if k not in uni_program_set:
                            uni_program_set.add(k)
                            writer.writerow([
                                article['article_id'],
                                university,
                                program_level,
                                program_name_norm,
                                self.programs.program2type[program_name] if program_name else 'N/A'
                            ])

    def run_data_pipeline(self, parse_admissions=False):
        """Run the whole data preprocess pipeline

        Parameters
        ----------
        parse_admissions : bool, optional
            Whether we parse the admissions programs, by default False
        """
        self.classify_articles()
        pp.pprint(f'CS articles: {len(self.cs_article_indices)}, Admission {len(self.admission_article_indices)}, Ask {len(self.ask_article_indices)}')
        if parse_admissions:
            self.parse_university_major_gpa()
            self.parse_admission_programs()
            self.save_classified_articles()
        else:
            self.load_all_articles()
        self.dump_articles_to_csv()
        # Create Tables and Dump to postgres DB
        create_tables_and_dump_data()
        self.all_articles = None
        gc.collect()
        print('Data Model initialization finished!')

    @staticmethod
    def get_article_titles(articles):
        return [article['article_title'] for article in articles]

    @staticmethod
    def get_occurrence_count(keywords, target_string):
        target_string = target_string.lower()
        return sum(map(lambda x: target_string.count(x.lower()), keywords))


if __name__ == "__main__":
    # Load from Raw data
    # dm = DataModel()
    # dm.load_and_clean_ptt_data(os.path.join(DATA_DIR, 'Studyabroad-0-1625.json'), save_path=os.path.join(DATA_DIR, 'studyabroad.json'))
    # Load from semi-processed data
    dm = DataModel.from_processed_data(os.path.join(DATA_DIR, 'studyabroad.json'))
    dm.run_data_pipeline(parse_admissions=True)
