from fastapi import FastAPI, Body
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import List


class Candidate(BaseModel):
    university: str = Field(None, example="NTU", title="University that you graduated",
                            description="Name in English or Chinese are both acceptable. Examples: [NCTU, 交大, 國立交通大學]")
    major: str = Field(
        None,
        example="MATH",
        title="Major that you study",
        description="Name in English or Chinese are both acceptable. Examples: [CS, IM, CSIE, GINM, Finance, 資工, 網媒, 電信工程學研究所]")
    gpa: float = Field(0, example=3.7, title="Overall GPA")
    target_schools: list = Field([], example=[
        "Stanford",
        "University of California, Berkeley",
        "CMU"],
        description="A list of target schools, fullname or abbreviation are both acceptable")
    target_programs: list = Field([], example=["LTI", "MHCI"], description="Other examples: [CS, MCS, HCI, MITS, MSSE, PMP, Robotics]")
    program_types: list = Field([], example=["HCI", "CS"], description="Allows 6 different program types: [CS, EE, SE, IS, HCI, MEng]")
    program_level: str = Field("MS", example="MS", description="MS or PhD")

    @validator('gpa')
    def validate_gpa(cls, gpa):
        if gpa < 0 or gpa > 4.3:
            raise ValueError('Invalid GPA, must in range [0, 4.3]')
        return gpa

    @validator('program_level')
    def validate_program_level(cls, s):
        if s.upper() not in ('MS', 'PHD'):
            raise ValueError('Invalid program level')
        return s

    @validator('program_types')
    def validate_program_types(cls, types):
        for c in types:
            if c not in ('CS', 'EE', 'SE', 'MEng', 'IS', 'HCI'):
                raise ValueError('Invalid program type')
        return types


class Program(BaseModel):
    university: str
    program: str = Field(None)
    program_level: str = Field(None)
    program_type: str = Field(None)


class Article(BaseModel):
    article_id: str
    article_title: str
    author: str
    date: datetime
    url: str
    university: str = Field(None)
    university_cname: str = Field(None)
    university_cabbr: str = Field(None)
    major: str = Field(None)
    major_cname: str = Field(None)
    major_cabbr: str = Field(None)
    major_type: str = Field(None)
    gpa: float = Field(None)
    gpa_scale: float = Field(None)
    admission_programs: List[Program] = Field([])
    score: float


def init_programs(article):
    programs = []
    for uni, program, program_level, program_type in zip(article.universities, article.programs, article.program_levels, article.program_types):
        programs.append(
            Program(
                university=uni,
                program=program,
                program_level=program_level,
                program_type=program_type
            )
        )
    return programs


def init_candidate(article, programs):
    return Article(
        article_id=article.article_id,
        article_title=article.article_title,
        author=article.author,
        date=article.date,
        url=article.url,
        university=article.uni_id,
        university_cname=article.uni_cname,
        university_cabbr=article.uni_cabbr,
        major=article.major_id,
        major_cname=article.major_cname,
        major_cabbr=article.major_cabbr,
        major_type=article.major_type,
        gpa=article.mean_gpa,
        gpa_scale=article.gpa_scale,
        admission_programs=programs,
        score=article.score
    )
