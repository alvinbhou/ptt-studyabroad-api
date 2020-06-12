# PTT StudyAbroad API

<img src ="https://circleci.com/gh/CryoliteZ/ptt-studyabroad-api.svg?style=svg"/>

> Having a hard time searching for information about studying CS abroad? 

> Got flamed for not doing enough research before posting on PTT? 

PTT StudyAbroad API provides a way to search for CS related articles with customized results

Find articles that match your **background**, **research interest** and **target school**
<!-- <p align="center">
    <em> Find articles that matches your background, your research interest and your target school</em>
</p> -->





**Documentation**: https://ptt-studyabroad-api.herokuapp.com/docs  

## Getting Started

Given specific education information (e.g. GPA, major, etc.), target programs (e.g. LTI, MHCI, MSCS, etc.) and target schools, the API returns articles that matches your background best. 

The API supports a wide range of programs (especially the CMU ones) and you could specify which domains you are interested in (e.g. HCI, EE, MEng).


**Example Request:**
```yaml
POST /admission
Content-Type: application/json
{
  "university": "NTU",
  "major": "IM",
  "gpa": 3.7,
  "target_schools": [
    "Stanford",
    "University of California, Berkeley",
    "CMU"
  ],
  "target_programs": [
    "MHCI", "MSIN"
  ],
  "program_types": [
    "HCI", "CS"
  ],
  "program_level": "MS"
}
```
**Successful Response:**
```yaml
[
  {
    "article_id": "M.1554447713.A.2A5",
    "article_title": "[錄取] UVA/NCSU CS PhD w/o publications",
    "author": "catalish (Hannah)",
    "date": "2019-04-05T15:01:44",
    "url": "https://www.ptt.cc/bbs/studyabroad/M.1554447713.A.2A5.html",
    "university": "CGU",
    "university_cname": "長庚大學",
    "university_cabbr": "長庚",
    "major": "IM",
    "major_cname": "資訊管理學系",
    "major_cabbr": "資管",
    "major_type": "IM",
    "gpa": 3.76,
    "gpa_scale": 4,
    "admission_programs": [
      {
        "university": "University of Virginia",
        "program": "CS",
        "program_level": "PhD",
        "program_type": "CS"
      },
      {
        "university": "North Carolina State University",
        "program": "CS",
        "program_level": "PhD",
        "program_type": "CS"
      },
      {
        "university": "Carnegie Mellon University",
        "program": "MSIN",
        "program_level": "MS",
        "program_type": "CS"
      },
      {
        "university": "Ohio State University",
        "program": "MSCS",
        "program_level": "MS",
        "program_type": "CS"
      }
    ],
    "score": 42
  },...
]
```

## API schema

### Entrypoint: https://ptt-studyabroad-api.herokuapp.com/

### Playground
Visit [the docs](https://ptt-studyabroad-api.herokuapp.com/docs#/admission/list_programs_admission_post) and click the **[Try it out]** button to play with the API


API Playground           |  Example Response
:-------------------------:|:-------------------------:
![](https://i.imgur.com/IDBu2Rq.png) |  ![](https://i.imgur.com/7A1xzon.png)


### Parameters


#### Request

| parameter                    | type                 | description|
|:-----------------------------|:----------------------------|:----------------------------|
| `university`                 | string                              | University that you graduated from. Name in English or Chinese are both acceptable. Examples: `NCTU`, `交大`, `國立交通大學` |
| `major`                       | string                | Major that you study. Name in English or Chinese are both acceptable. Examples: `CS`, `IM`, `CSIE`, `GINM`, `Finance`, `資工`, `網媒`, `電信工程學研究所`  |
| `gpa`                          | float                  |  Overall GPA. Any number between `0` and `4.3`
| `target_schools`               | List[string]                       | A list of target schools, fullname or abbreviation are both acceptable. Example: [ `Stanford`, `University of California, Berkeley`, `CMU`, `UofT`] |
| `target_programs`            | List[string]      | A list of target programs. Example:  [`CS,` `MCS`, `MHCI`, `MITS`, `MSSE`, `PMP`, `Robotics`] |
| `program_types`               | List[string]        | A list of target program types. We accept the following 6 program types:  [`CS,` `EE`, `SE`, `IS`, `HCI`, `MEng`]|
| `program_level`               | string      | Target program level: `MS` or `PhD` |

#### Response

The response JSON should be pretty self-explanatory. The `score` indicates how well the artilce matches your query, the higher the better. The detailed API schemas is also documentaed [here](https://ptt-studyabroad-api.herokuapp.com/docs#/admission/list_programs_admission_post). 


#### Example curl request

```bash
curl -X POST "https://ptt-studyabroad-api.herokuapp.com/admission" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d "{\"university\":\"NTU\", \"target_schools\": [\"MIT\",\"CMU\"], \
  \"target_programs\":[\"CS\"], \
  \"program_level\":\"PhD\"}"
```

## Deployment

### Deploy Locally

All the deployment is done in one line. Visit `localhost:5000` to see the results.

```
docker-compose up -d
```

If you would like to build and parse all the articles from scratch, set `BUILD_FROM_SCRATCH` to `True` in the `settings.py` file. The build takes around a minute.


### Deploy on Heroku
We use the `heroku-postgresql` addon as our database
```
heroku apps:create ptt-studyabroad-api
heroku addons:create heroku-postgresql:hobby-dev
heroku stack:set container
git push heroku master 
```

## Built With

* [FastAPI](https://fastapi.tiangolo.com/) -  Modern, fast framework for building APIs 
* [PostgreSQL](https://www.postgresql.org/) - Relational database that comes in handy
* [docker-compose](https://docs.docker.com/compose/) - For multi-container Docker applications
* [heroku.yml](https://devcenter.heroku.com/articles/build-docker-images-heroku-yml) - New feature from Heroku to build Docker Images with self defined manifest

## TODO

*Note: The API is still under development, so some information parsing may be incorrect. If the quarantine ends I maybe won't have that much time to work on these TODOs...

* Refactor code (Too much special cases to deal with, the code is kinda ugly...)
* Deploy the API to AWS Fargate
* Add background workers that parse new aritcles from PTT
* Exclude some large files from GitHub
* Improve keyword extraction
* Add other APIs (such as college decision articles)


## License

This project is licensed under the GPLv3 License - see the [LICENSE.md](LICENSE.md) file for details.

## Acknowledgments

* [majors.csv](data/tw/majors.csv) is parsed from http://www.aca.ntu.edu.tw/curri/curs_deptabb.asp
* [tw_universities.csv](data/tw/tw_universities.csv) and [us_universities_uids.csv](data/us/us_universities_uids.csv) are parsed from Wiki
* [world_universities_and_domains.json](data/us/world_universities_and_domains.json) is downloaded from [Hipo/university-domains-ist](https://github.com/Hipo/university-domains-list)
* All articles belong to PTT/StudyAborad
