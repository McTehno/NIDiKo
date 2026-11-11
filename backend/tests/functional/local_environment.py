"""Disposable E2E data and a narrow Supabase Auth test double (never production)."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from pymongo import MongoClient


REPO_ROOT = Path(__file__).resolve().parents[3]
INVALID_EMAIL = 'neveljaven_uporabnik@test.si'
INVALID_PASSWORD = 'NepravilnoGeslo123!'


def seed_database(uri, database_name):
    # Fail closed: this helper must never write to Atlas or the staging database.
    if urlparse(uri).hostname not in {'localhost', '127.0.0.1', '::1'}:
        raise ValueError('Functional tests require a loopback MongoDB URI')
    if not database_name.startswith('nidiko_functional_'):
        raise ValueError('Database name must start with nidiko_functional_')
    with MongoClient(uri, serverSelectionTimeoutMS=5000) as client:
        client.admin.command('ping')
        database = client[database_name]
        if database.list_collection_names():
            raise ValueError('Use a fresh, empty functional database; existing data is preserved')
        for name in ('learning_paths', 'modules', 'learning_units'):
            documents = json.loads(
                (REPO_ROOT / 'backend/data/nova_verzija_data' / f'{name}.json').read_text(encoding='utf-8-sig'))
            fixture = Path(__file__).with_name('fixtures') / f'{name}.json'
            if fixture.exists():
                documents.extend(json.loads(fixture.read_text(encoding='utf-8')))
            database[name].insert_many(documents)


class AuthStub(BaseHTTPRequestHandler):
    """Only the specified invalid password login is implemented; no sessions issued."""
    def reply(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header('Access-Control-Allow-Origin', 'http://localhost:5173')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers',
                         'apikey, authorization, content-type, x-client-info, x-supabase-api-version')
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.reply(200, {})

    def do_GET(self):
        self.reply(200 if self.path == '/health' else 404, {})

    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
        if (self.path == '/auth/v1/token?grant_type=password' and
                data.get('email') == INVALID_EMAIL and data.get('password') == INVALID_PASSWORD):
            self.server.rejected_logins += 1
            self.reply(400, {'code': 'invalid_credentials', 'message': 'Invalid login credentials'})
        else:
            self.reply(404, {'message': 'Unexpected request to functional auth stub'})

    def log_message(self, format, *args):
        pass  # Do not log authentication request bodies or headers.


def create_auth_stub():
    server = ThreadingHTTPServer(('127.0.0.1', 54321), AuthStub)
    server.rejected_logins = 0
    return server
