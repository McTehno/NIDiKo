# backenda za Python FastAPI
FROM python:3.11-slim

# Nastavitev delovnega imenika
WORKDIR /app

# Kopiranje datotek z zahtevami
COPY requirements.txt .
COPY tests/functional/requirements.txt tests/functional/requirements.txt

# Namestitev odvisnosti
RUN pip install --no-cache-dir -r requirements.txt

# Kopiranje preostale kode
COPY . .

# Odprtje vrat, na katerih teče FastAPI
EXPOSE 8000

# Zagon strežnika
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
