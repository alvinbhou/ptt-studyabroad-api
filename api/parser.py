import os
from config.settings import DATA_DIR, BUILD_FROM_SCRATCH
from utils.data import DataModel
from api.models import Candidate, Article, Program

# Initialization of the DataModel when the parser is imported
if BUILD_FROM_SCRATCH:
    dm = DataModel()
    dm.load_and_clean_ptt_data(os.path.join(DATA_DIR, 'studyabroad.json'), save_path=os.path.join(DATA_DIR, 'studyabroad.json'))
else:
    dm = DataModel.from_processed_data(os.path.join(DATA_DIR, 'studyabroad.json'))

dm.run_data_pipeline(parse_admissions=BUILD_FROM_SCRATCH)


def parse_request(request, article_type="ADMISSION"):
    print('Request:', request)
    # Normalize the university
    university_id = dm.tw_background.sentence2university(request.university)[0] if request.university else ''

    # Normalize the major
    major_id = dm.tw_background.sentence2major(request.major, from_api=True) if request.major else ''
    major_type = dm.tw_background.mid2mtype[major_id] if major_id else ''

    # Normalize the target schools
    target_schools = [dm.us_background.normalize_university_name(school) for school in request.target_schools]
    target_schools = [dm.us_background.search_single_university_name(school) for school in target_schools]
    target_schools = [school for school in target_schools if school]

    # Normalize target programs
    target_programs = []
    program_types = []
    for program in request.target_programs:
        (program_level, program_name), _ = dm.us_background.programs.search_program(program)
        program_name = dm.us_background.programs.normalize_program_name(program_level, program_name)
        if program_name:
            target_programs.append(program_name)
            program_types.append(dm.programs.program2type[program_name])
    # Extend request.program_types
    program_types.extend(request.program_types)
    program_types = list(set(program_types))
    target_programs = list(set(target_programs))

    # Use GPA 3.6 if GPA not given
    # gpa = request.gpa if request.gpa else 3.6

    query_dict = {
        'article_type': article_type,
        'uni_id': university_id,
        'major_id': major_id,
        'major_type': major_type,
        'gpa': request.gpa,
        'universities': target_schools,
        'programs': target_programs,
        'program_level': request.program_level,
        'program_types': program_types
    }
    return query_dict
