FROM python:3.7


# Pip install
WORKDIR /app
COPY requirements.txt /app
RUN pip install -r requirements.txt

COPY . /app

# Clean US university data
ENV PYTHONPATH=/app
RUN python ./utils/clean_us_data.py

EXPOSE ${PORT:-5000}
CMD uvicorn main:app --port ${PORT:-5000} --host 0.0.0.0
