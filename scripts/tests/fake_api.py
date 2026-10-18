"""API simulada de ElevenLabs para pruebas unitarias (NO es el servicio real).

Imita solo la forma de las respuestas documentadas; no prueba que ElevenLabs acepte los payloads.
"""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.parse
from email.message import Message
from typing import Any


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeElevenLabs:
    def __init__(self, key: str = "xxxxx-test-key"):
        self.key = key
        self.docs: dict[str, dict[str, Any]] = {}
        self.agents: dict[str, dict[str, Any]] = {}
        self.indexes: dict[str, str] = {}  # doc_id -> status final
        self.index_polls_until_done = 0
        self.index_final_status = "succeeded"
        self.calls: list[tuple[str, str]] = []
        self.fail_next: list[tuple[int, str]] = []  # (status, body) por llamada, en orden
        self.fail_on: dict[tuple[str, str], list[tuple[int, str]]] = {}
        self._n = 0
        self.last_headers: dict[str, str] = {}
        self._polls: dict[str, int] = {}

    # --- interfaz de urlopen
    def __call__(self, req, timeout=None):
        parsed = urllib.parse.urlparse(req.full_url)
        method, path = req.get_method(), parsed.path
        query = urllib.parse.parse_qs(parsed.query)
        body = json.loads(req.data.decode()) if req.data else None
        self.last_headers = {k.lower(): v for k, v in req.header_items()}
        self.calls.append((method, path))
        if self.fail_next:
            status, text = self.fail_next.pop(0)
            raise self._http_error(req.full_url, status, text)
        key = (method, path)
        if self.fail_on.get(key):
            status, text = self.fail_on[key].pop(0)
            raise self._http_error(req.full_url, status, text)
        if self.last_headers.get("xi-api-key") != self.key:
            raise self._http_error(req.full_url, 401, json.dumps({"detail": "invalid key"}))
        result = self._route(method, path, query, body)
        return _Resp(json.dumps(result).encode())

    @staticmethod
    def _http_error(url, status, text):
        hdrs = Message()
        return urllib.error.HTTPError(url, status, "err", hdrs, io.BytesIO(text.encode()))

    def _next(self, prefix: str) -> str:
        self._n += 1
        return f"{prefix}{self._n:04d}"

    # --- rutas
    def _route(self, method, path, query, body):
        if method == "GET" and path == "/v1/convai/knowledge-base":
            prefix = query.get("search", [""])[0]
            docs = [d for d in self.docs.values() if d["name"].startswith(prefix)]
            return {"documents": docs, "has_more": False, "next_cursor": None}
        if method == "POST" and path == "/v1/convai/knowledge-base/text":
            doc_id = self._next("doc")
            self.docs[doc_id] = {
                "id": doc_id,
                "name": body["name"],
                "type": "text",
                "metadata": {"size_bytes": len(body["text"].encode())},
            }
            return {"id": doc_id, "name": body["name"], "folder_path": []}
        if method == "GET" and path == "/v1/convai/knowledge-base/rag-index":
            return {"total_used_bytes": 1234, "total_max_bytes": 2000000, "models": []}
        if path.startswith("/v1/convai/knowledge-base/") and path.endswith("/rag-index"):
            doc_id = path.split("/")[-2]
            if method == "POST":
                self.indexes.setdefault(doc_id, "processing")
                self._polls[doc_id] = 0
                st = "processing" if self.index_polls_until_done > 0 else self.index_final_status
                self.indexes[doc_id] = st
                return {"id": "idx", "model": body["model"], "status": st, "progress_percentage": 0.0,
                        "document_model_index_usage": {"used_bytes": 10}}
            if method == "GET":
                if doc_id not in self.indexes:
                    return {"indexes": []}
                self._polls[doc_id] = self._polls.get(doc_id, 0) + 1
                if self._polls[doc_id] >= self.index_polls_until_done:
                    self.indexes[doc_id] = self.index_final_status
                return {"indexes": [{"id": "idx", "model": "e5_mistral_7b_instruct",
                                     "status": self.indexes[doc_id], "progress_percentage": 1.0,
                                     "document_model_index_usage": {"used_bytes": 10}}]}
        if method == "DELETE" and path.startswith("/v1/convai/knowledge-base/"):
            self.docs.pop(path.rsplit("/", 1)[-1], None)
            return {}
        if method == "GET" and path == "/v1/convai/agents":
            s = query.get("search", [""])[0]
            return {"agents": [{"agent_id": i, "name": a["name"], "tags": a.get("tags", []), "archived": False}
                               for i, a in self.agents.items() if s in a["name"]],
                    "has_more": False, "next_cursor": None}
        if method == "POST" and path == "/v1/convai/agents/create":
            agent_id = self._next("agent_")
            self.agents[agent_id] = json.loads(json.dumps(body))
            return {"agent_id": agent_id}
        if path.startswith("/v1/convai/agents/"):
            agent_id = path.rsplit("/", 1)[-1]
            if method == "PATCH":
                self.agents[agent_id].update(json.loads(json.dumps(body)))
                return {"agent_id": agent_id, **self.agents[agent_id]}
            if method == "GET":
                return {"agent_id": agent_id, **self.agents[agent_id]}
        raise AssertionError(f"ruta no simulada: {method} {path}")

    def writes(self) -> list[tuple[str, str]]:
        return [c for c in self.calls if c[0] in ("POST", "PATCH", "DELETE")]
