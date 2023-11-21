# 
FROM python:3.11

# 
WORKDIR /code

# 
COPY ./build_requirements.txt /code/requirements.txt
ADD ./build/spyctl /spyctl

RUN if [ -e /code/requirements.txt ]; then \
        echo "File exists!"; \
    else \
        echo "File does not exist!"; \
    fi

# 
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# 
COPY ./app /code/app

# 
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]