FROM python:3-slim
RUN pip install pipenv
WORKDIR /usr/src/app
COPY Pipfile .
RUN pipenv install
COPY . .
#ENTRYPOINT ["docker-entrypoint.sh"]
#CMD ["python", "-m", "atxmond", "--db", "db"]
