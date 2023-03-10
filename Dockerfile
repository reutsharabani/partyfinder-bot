FROM python:3

WORKDIR /usr/src/app


COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ARG DISCORD_TOKEN
ENV DISCORD_TOKEN $DISCORD_TOKEN

ARG DISCORD_ADMIN
ENV DISCORD_ADMIN $DISCORD_ADMIN

ARG BACKUP_BUCKET_NAME
ENV BACKUP_BUCKET_NAME $BACKUP_BUCKET_NAME

ARG AWS_ACCESS_KEY_ID
ENV AWS_ACCESS_KEY_ID $AWS_ACCESS_KEY_ID

ARG AWS_SECRET_ACCESS_KEY
ENV AWS_SECRET_ACCESS_KEY $AWS_SECRET_ACCESS_KEY

CMD [ "python", "./bot.py" ]