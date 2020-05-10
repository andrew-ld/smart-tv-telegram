FROM python:3

WORKDIR /app/

COPY . .

RUN pip3 install --no-cache-dir -r requirements.txt

RUN python -OO -m compileall .

CMD ["python", "."]
