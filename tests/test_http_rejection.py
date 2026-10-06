"""Real loopback sockets and a mock backend; no credentials or external services."""
import http.client
import json
import socket
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock
from app.server import create_server


class HTTPRejectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.backend = Mock()
        self.server = create_server(self.temp.name, 0, self.backend)
        self.port = self.server.server_port
        self.closed = {}
        shutdown = self.server.shutdown_request

        def record_close(connection):
            try:
                self.closed[connection.getpeername()[1]] = time.monotonic()
            except OSError:
                pass
            shutdown(connection)

        self.server.shutdown_request = record_close
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        client = http.client.HTTPConnection('127.0.0.1', self.port, timeout=2)
        client.request('GET', '/api/state')
        self.token = json.loads(client.getresponse().read())['token']
        client.close()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()
        self.assertEqual(self.backend.mock_calls, [])

    def connect(self, length='32', extra='', authorized=False, valid_content_type=False):
        client = socket.create_connection(('127.0.0.1', self.port), timeout=2)
        client.settimeout(2)
        auth = f'X-Workspace-Token: {self.token}\r\n' if authorized else ''
        content_type = 'application/json' if valid_content_type else 'text/plain'
        # Valid token with a wrong content type still must reject credentials.
        headers = (f'POST /api/credentials/save HTTP/1.1\r\nHost: 127.0.0.1:{self.port}\r\n'
                   f'Origin: http://127.0.0.1:{self.port}\r\nContent-Type: {content_type}\r\n'
                   f'Content-Length: {length}\r\n{auth}{extra}\r\n')
        client.sendall(headers.encode('ascii'))
        return client, client.getsockname()[1]

    def response(self, client, status=403):
        data = b''
        while b'\r\n\r\n' not in data:
            chunk = client.recv(4096)
            self.assertTrue(chunk, 'connection closed before HTTP response headers')
            data += chunk
        headers, body = data.split(b'\r\n\r\n', 1)
        self.assertTrue(headers.startswith(f'HTTP/1.0 {status} '.encode()), headers)
        self.assertIn(b'Connection: close', headers)
        length = next(int(line.split(b':', 1)[1]) for line in headers.split(b'\r\n') if line.lower().startswith(b'content-length:'))
        while len(body) < length:
            chunk = client.recv(4096)
            self.assertTrue(chunk, 'connection closed before complete rejection body')
            body += chunk
        return json.loads(body)

    def closed_by(self, port, started, limit=1):
        deadline = started + limit
        while port not in self.closed and time.monotonic() < deadline:
            time.sleep(.005)
        self.assertIn(port, self.closed, 'rejected handler did not finish within the bounded drain')
        self.assertLess(self.closed[port] - started, limit)

    def test_headers_only_response_then_delayed_body(self):
        for authorized in (False, True):
            with self.subTest(valid_token=authorized):
                started = time.monotonic()
                client, port = self.connect(authorized=authorized)
                try:
                    self.assertIn('error', self.response(client))
                    # Observe the complete 403 before transmitting the request body.
                    time.sleep(.03)
                    client.sendall(b'x' * 32)
                    self.assertEqual(client.recv(1), b'')
                    self.closed_by(port, started)
                finally:
                    client.close()

    def test_missing_body_times_out_without_blocking_server(self):
        started = time.monotonic()
        client, port = self.connect()
        try:
            self.response(client)
            self.closed_by(port, started)
            probe = http.client.HTTPConnection('127.0.0.1', self.port, timeout=2)
            probe.request('GET', '/api/health')
            self.assertEqual(probe.getresponse().status, 200)
            probe.close()
        finally:
            client.close()

    def test_trickling_body_cannot_extend_total_deadline(self):
        started = time.monotonic()
        client, port = self.connect(length='65536')
        try:
            self.response(client)
            while port not in self.closed and time.monotonic() - started < .8:
                try:
                    client.sendall(b'x')
                except OSError:
                    break
                time.sleep(.03)
            self.closed_by(port, started, limit=.8)
        finally:
            client.close()

    def test_ambiguous_chunked_oversize_length_does_not_wait_for_body(self):
        for length, extra in (('65537', ''), ('32', 'Content-Length: 32\r\n'),
                              ('32', 'Transfer-Encoding: chunked\r\n'), ('32', 'Transfer-Encoding:\r\n'), ('-1', ''), ('abc', '')):
            with self.subTest(length=length, extra=extra):
                started = time.monotonic()
                client, port = self.connect(length, extra)
                try:
                    self.response(client)
                    self.closed_by(port, started, limit=.2)
                finally:
                    client.close()

    def test_oversize_credential_body_rejected_before_backend(self):
        started = time.monotonic()
        client, port = self.connect(length='4097', authorized=True, valid_content_type=True)
        try:
            self.response(client, status=400)
            time.sleep(.03)
            client.sendall(b'x' * 4097)
            self.assertEqual(client.recv(1), b'')
            self.closed_by(port, started)
        finally:
            client.close()

    def test_credential_ambiguous_framing_rejects_without_backend(self):
        for length, extra in (('32', 'Content-Length: 32\r\n'),
                              ('32', 'Transfer-Encoding: chunked\r\n'), ('32', 'Transfer-Encoding:\r\n'), ('abc', '')):
            with self.subTest(length=length, extra=extra):
                started = time.monotonic()
                client, port = self.connect(length, extra, authorized=True, valid_content_type=True)
                try:
                    self.response(client, status=400)
                    self.closed_by(port, started, limit=.2)
                finally:
                    client.close()


if __name__ == '__main__':
    unittest.main()
