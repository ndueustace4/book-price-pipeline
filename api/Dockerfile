FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY api ./api
COPY pipeline ./pipeline
COPY scrapers ./scrapers
COPY run_books.py run_quotes.py ./
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
