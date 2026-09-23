FROM python:3.12-slim
WORKDIR /seed
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY *.py ./
CMD ["python", "-u", "run_all.py"]
