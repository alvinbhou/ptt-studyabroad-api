from fastapi import FastAPI, Body
from fastapi.openapi.utils import get_openapi
from typing import List
import os
import collections
from api.models import Candidate, Article, Program
from api.models import init_programs, init_candidate
from api.database import query_programs_api
from api.parser import parse_request

app = FastAPI()


@app.on_event("startup")
def start_up_fn():
    # Run something on startup
    pass


@app.get("/")
def read_root():
    return {"docs": "Try out APIs and read documentation at '/docs'"}


@app.post("/admission", response_model=List[Article], tags=['admission'])
def list_programs(student: Candidate) -> List[Article]:
    query_dict = parse_request(student, article_type="ADMISSION")
    articles = query_programs_api(query_dict)
    result = []
    max_score = articles[0].score if articles else 0
    for idx, article in enumerate(articles):
        if len(articles) > 100 and article.score < max_score // 2:
            break
        programs = init_programs(article)
        result.append(init_candidate(article, programs))
    print(query_dict, len(articles), len(result))
    return result


def custom_openapi(openapi_prefix: str = ''):
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="PTT StudyAbroad API",
        version="0.1.0",
        description="List of APIs to search CS related articles on PTT StudyAbroad board",
        routes=app.routes,
        openapi_prefix=openapi_prefix
    )
    openapi_schema['tags'] = [
        {"name": "admission", "description": "Get a list of admission articles with similar background information"},
    ]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
