FROM python:3-alpine
RUN pip install pipenv
WORKDIR /usr/src/app
COPY . .
RUN pipenv install
#ENTRYPOINT ["docker-entrypoint.sh"]
#CMD ["python", "-m", "atxmond", "--db", "db"]
