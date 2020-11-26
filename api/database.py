import os
import csv
from config.settings import DB_CONFIG, DATABASE_URL
import sqlalchemy as sa
from sqlalchemy.types import DateTime
from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, MetaData
from sqlalchemy_utils import create_view
from sqlalchemy import inspect
from sqlalchemy import and_, or_, not_
from sqlalchemy.sql import select
import pprint
pp = pprint.PrettyPrinter()

if DATABASE_URL:
    engine = create_engine(DATABASE_URL)
else:
    engine = create_engine('postgres://%s:%s@%s:%s/%s' % (
        DB_CONFIG['USERNAME'],
        DB_CONFIG['PASSWORD'],
        DB_CONFIG['HOST'],
        DB_CONFIG['PORT'],
        DB_CONFIG['DB_NAME']))

session = scoped_session(sessionmaker(autocommit=False,
                                      autoflush=False,
                                      bind=engine))
Base = declarative_base()
Base.query = session.query_property()


class ARTICLES(Base):
    __tablename__ = 'articles'
    article_id = Column(String(25), primary_key=True)
    article_title = Column(String(80))
    author = Column(String(80))
    # content = Column(Text())
    date = Column(DateTime())
    url = Column(String(80))
    article_type = Column(String(15))
    uni_id = Column(String(15))
    uni_name = Column(String(80))
    uni_cname = Column(String(20))
    uni_location = Column(String(50))
    uni_cabbr = Column(String(10))
    major_id = Column(String(15))
    major_cname = Column(String(20))
    major_name = Column(String(100))
    major_cabbr = Column(String(15))
    major_type = Column(String(15))
    max_gpa = Column(Float())
    min_gpa = Column(Float())
    mean_gpa = Column(Float())
    gpa_scale = Column(Float())


class ADMISSION_UNIVERSITIES(Base):
    __tablename__ = 'admission_universities'
    id = Column(Integer, primary_key=True, autoincrement=True)  # auto-increment id to prevent no primary key
    article_id = Column(String(25), ForeignKey(ARTICLES.article_id))

    university = Column(String(100))


class ADMISSION_UNI_PROGRAMS(Base):
    __tablename__ = 'admission_programs'
    id = Column(Integer, primary_key=True, autoincrement=True)  # auto-increment id to prevent no primary key
    article_id = Column(String(25), ForeignKey(ARTICLES.article_id))
    university = Column(String(100))
    program_level = Column(String(5))
    program = Column(String(50))
    program_type = Column(String(10))


# VIEW_COLUMNS (SELECT * for VIEW is not working with sqlalchemy_utils... don't have time to fix it now)
ARTICLES_COLUMNS = [
    ARTICLES.article_id, ARTICLES.article_title, ARTICLES.author,
    ARTICLES.date, ARTICLES.url,
    ARTICLES.article_type, ARTICLES.uni_id, ARTICLES.uni_name, ARTICLES.uni_cname,
    ARTICLES.uni_location, ARTICLES.uni_cabbr, ARTICLES.major_id, ARTICLES.major_cname,
    ARTICLES.major_name, ARTICLES.major_cabbr, ARTICLES.major_type, ARTICLES.max_gpa,
    ARTICLES.min_gpa, ARTICLES.mean_gpa, ARTICLES.gpa_scale
]


class ARTICLE_UNI_VIEW(Base):
    __table__ = create_view(
        name='article_university_view',
        selectable=sa.select(
            ARTICLES_COLUMNS + [ADMISSION_UNIVERSITIES.university],
            from_obj=(
                ARTICLES.__table__
                .join(ADMISSION_UNIVERSITIES)
            )
        ),
        metadata=Base.metadata
    )


class ARTICLE_UNI_PROGRAM_VIEW(Base):
    __table__ = create_view(
        name='article_program_view',
        selectable=sa.select(
            ARTICLES_COLUMNS + [
                ADMISSION_UNI_PROGRAMS.university,
                ADMISSION_UNI_PROGRAMS.program_level,
                ADMISSION_UNI_PROGRAMS.program,
                ADMISSION_UNI_PROGRAMS.program_type
            ],
            from_obj=(
                ARTICLES.__table__
                .join(ADMISSION_UNI_PROGRAMS)
            )
        ),
        metadata=Base.metadata
    )


def create_tables_and_dump_data():
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.
    try:
        # Clean up the DB then create all tables and views
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

        # Copy CSV files
        csv_paths = ['./output/cs_articles.csv', './output/admission_universities.csv', './output/admission_uni_and_programs.csv']
        table_classes = [ARTICLES, ADMISSION_UNIVERSITIES, ADMISSION_UNI_PROGRAMS]
        # col_names = [article_header, ['id', 'article_id', 'university'], ['id',
        # 'article_id', 'university', 'program_level', 'program', 'program_type']]

        for path, table_class in zip(csv_paths, table_classes):
            with open(path, 'r') as f:
                reader = csv.reader(f, delimiter='|')
                header = next(reader)
                for row in reader:
                    d = {k: v for k, v in zip(header, row)}
                    session.add(table_class(**d))
            # Commit for each individual table
            session.commit()
            print(f'Dump {path}')
        print('DB Dump finish!')

    except Exception as error:
        print(error)


QUERY_SIMILAR_BACKGROUND_PROGRAM_STR = """
        SELECT articles.article_id, article_title, author, date, url, uni_id, uni_cname, uni_cabbr,
                major_id, major_cname, major_cabbr, major_type, mean_gpa, gpa_scale,
                universities, programs, program_types, program_levels, score, ABS(mean_gpa - :gpa) AS gpa_diff

        FROM articles JOIN
            (SELECT article_id, array_agg(sub.university) as universities, array_agg(sub.program) as programs,
                     array_agg(sub.program_type) as program_types, array_agg(sub.program_level) as program_levels, MAX(score) as score
            FROM(
                SELECT *,
                    6 * (mean_gpa BETWEEN :gpa -0.2 AND :gpa + 0.2)::int +
                    5 * ((mean_gpa BETWEEN :gpa - 0.3 AND :gpa - 0.21) OR (mean_gpa BETWEEN :gpa + 0.21 AND :gpa + 0.3))::int +
                    2 * ((mean_gpa BETWEEN :gpa - 0.5 AND :gpa - 0.31) OR (mean_gpa BETWEEN :gpa + 0.31 AND :gpa + 0.5))::int +
                    4 * (min_gpa <= 3.01 AND (min_gpa BETWEEN :gpa -0.25 AND :gpa + 0.25) )::int +
                    4 * (min_gpa <= 3.01 AND :gpa <= 3.01 AND (min_gpa BETWEEN 0 AND 3.01) )::int +
                    -0.2 * (mean_gpa = -1)::int +
                    4 * (length(:uni_id) > 0 AND uni_id = :uni_id)::int +
                    10 * (length(:uni_id) > 0 AND uni_id = :uni_id AND NOT uni_id ~ '(NTU|NCTU|NTHU)')::int +
                    6 * (length(:uni_id) > 0 AND uni_id = :uni_id AND NOT uni_id ~ '(NCCU|NCKU)')::int +
                    3 * (length(:major_type) > 0 AND (major_id = :major_id OR major_type = :major_type))::int +
                    1 * (length(:major_id) > 0 AND (major_id = :major_id AND NOT major_type ~ '(CS|EE)'))::int +
                    2 * (length(:uni_id) > 0 AND length(:major_id) > 0 AND (uni_id = :uni_id AND major_id = :major_id))::int +
                    6 * (program ~ :programs)::int +
                    4 * (program ~ :programs AND NOT program ~ '(CS|MSCS|EE|MSEE)')::int +
                    5 * (program_type ~ :program_types)::int +
                    10 * (program_level = :program_level AND :program_level = 'PhD')::int +
                    15 * (length(:universities) > 2 AND university ~ :universities)::int as score
                FROM article_program_view
                WHERE article_type = :article_type
            ) as sub
            GROUP BY article_id) as x ON x.article_id = articles.article_id
            WHERE (length(:program_types) = 2 OR program_types && ARRAY[:program_type_arr]::varchar[])
        ORDER BY score DESC, gpa_diff ASC, date DESC;
    """

QUERY_TARGET_SCHOOL_STR = """
        SELECT articles.article_id, article_title, author, date, url, uni_id, uni_cname, uni_cabbr,
                major_id, major_cname, major_cabbr, major_type, mean_gpa, gpa_scale,
                universities, programs, program_types, program_levels, score

        FROM articles JOIN
            (SELECT article_id, array_agg(sub.university) as universities, array_agg(sub.program) as programs,
                     array_agg(sub.program_type) as program_types, array_agg(sub.program_level) as program_levels, MAX(score) as score
            FROM(
                SELECT *,
                    50 * (program ~ :programs)::int +
                    1 * (program_type ~ :program_types)::int +
                    1 * (program_level = :program_level AND :program_level = 'PhD')::int +
                    48 * (length(:universities) > 2 AND university ~ :universities)::int as score
                FROM article_program_view
                WHERE article_type = :article_type
            ) as sub
            GROUP BY article_id) as x ON x.article_id = articles.article_id
            WHERE (length(:program_types) = 2 OR program_types && ARRAY[:program_type_arr]::varchar[])
       ORDER BY score DESC, date DESC;
    """


def query_similar_background_api(candidate):
    candidate['program_type_arr'] = candidate['program_types']
    columns = ['universities', 'programs', 'program_types']
    for col in columns:
        if candidate[col]:
            likestring = '(' + '|'.join(candidate[col]) + ')'
            candidate[col] = likestring
    articles = session.execute(QUERY_SIMILAR_BACKGROUND_PROGRAM_STR, candidate)
    session.commit()
    return list(articles)


def query_target_school_api(candidate):
    candidate['program_type_arr'] = candidate['program_types']
    columns = ['universities', 'programs', 'program_types']
    for col in columns:
        if candidate[col]:
            likestring = '(' + '|'.join(candidate[col]) + ')'
            candidate[col] = likestring
    articles = session.execute(QUERY_TARGET_SCHOOL_STR, candidate)
    session.commit()
    return list(articles)


if __name__ == "__main__":
    # For local testing
    inst = inspect(ARTICLES)
    d = {'uni_id': '', 'major_id': 'IM', 'article_type': 'ADMISSION', 'gpa': 0,
         'universities': '', 'program': 'MHCI', 'major_type': 'CS', 'program_type': 'HCI'
         }
    articles = session.execute("""
               SELECT articles.article_id, article_title, author, date, url, uni_id, uni_cname, uni_cabbr, \
                major_id, major_cname, major_cabbr, major_type, mean_gpa, gpa_scale, \
                universities, programs, program_types, program_levels, score

        FROM articles JOIN
            (SELECT article_id, array_agg(sub.university) as universities, array_agg(sub.program) as programs,  \
                     array_agg(sub.program_type) as program_types, array_agg(sub.program_level) as program_levels, MAX(score) as score
            FROM(
                SELECT *, \
                    5 * (mean_gpa BETWEEN :gpa -0.25 AND :gpa + 0.25)::int + \
                    2 * (mean_gpa BETWEEN :gpa -0.5 AND :gpa -0.25 OR mean_gpa BETWEEN :gpa +0.25 AND :gpa + 0.5)::int + \
                    3 * (min_gpa <= 3.01 AND min_gpa BETWEEN :gpa -0.4 AND :gpa + 0.4 )::int + \
                    4 * (uni_id = :uni_id)::int + \
                    3 * (major_id = :major_id OR major_type = :major_type)::int + \
                    10 * (program = :program)::int + \
                    7 * (program_type = :program_type)::int + \
                    15 * (length(:universities) > 0 AND university ~ :universities)::int as score
                FROM article_program_view
                WHERE article_type = :article_type
            ) as sub
            WHERE score >= 0
            GROUP BY article_id) x ON x.article_id = articles.article_id
        ORDER BY score DESC;
    """, d)

    for i, article in enumerate(list(articles)):
        print(f"""{article.score} {article.article_title}, GPA: {article.mean_gpa},
              {article.uni_id}/{article.major_id}, {article.universities} {article.programs} {article.program_levels}/{article.program_types}, {article.url}""")
