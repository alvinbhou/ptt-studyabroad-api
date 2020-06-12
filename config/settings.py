import os
from enum import Enum

PROJECT_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))

# Path settings
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'output')

DB_CONFIG = {
    'USERNAME': os.environ.get('POSTGRES_USER', 'test_user'),
    'PASSWORD': os.environ.get('POSTGRES_PASSWORD', '123'),
    'DB_NAME': os.environ.get('DB_NAME', 'ptt'),
    'PORT': os.environ.get('POSTGRES_PORT', 5432),
    'HOST': os.environ.get('POSTGRES_HOST', 'localhost')
}

DATABASE_URL = os.environ.get('DATABASE_URL', None)


# TYPES
class ARTICLE_TYPE(Enum):
    ADMISSION = '[錄取]'
    ASK = '選校'
    GENERAL_CS = 'GENERAL_CS'
    ALL = 'ALL'


BUILD_FROM_SCRATCH = False
