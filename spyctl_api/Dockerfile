# 
FROM python:3.11

# 
WORKDIR /code

# 
COPY ./requirements.txt /code/requirements.txt
ADD ./build/spyctl /spyctl

# 
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ../ /opt/spyderbat/spyctl

# 
COPY ./app /code/app

# 
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]