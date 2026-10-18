"""Cliente minimo (solo biblioteca estandar) para la API REST de ElevenLabs Agents.

Endpoints usados (referencia oficial, verificada el 2026-10-18; ver docs/guias/despliegue-cdu-001.md):
  GET    /v1/convai/knowledge-base                       (listar documentos; `search` es prefijo de nombre)
  POST   /v1/convai/knowledge-base/text                  (crear documento desde texto)
  POST   /v1/convai/knowledge-base/{id}/rag-index        (calcular indice RAG; idempotente)
  GET    /v1/convai/knowledge-base/{id}/rag-index        (estado del indice por modelo)
  GET    /v1/convai/knowledge-base/rag-index             (uso total de indice del workspace)
  DELETE /v1/convai/knowledge-base/{id}                  (borrar documento; `force`)
  GET    /v1/convai/agents                               (listar agentes)
  POST   /v1/convai/agents/create                        (crear agente)
  GET    /v1/convai/agents/{agent_id}                    (leer agente)
  PATCH  /v1/convai/agents/{agent_id}                    (actualizar agente)

Seguridad: la clave solo se lee del entorno (ELEVENLABS_API_KEY), solo viaja en la cabecera
`xi-api-key` y se elimina de cualquier texto que salga en errores o logs (`redact`).
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

DEFAULT_BASE = "https://api.elevenlabs.io"
USER_AGENT = "poc-agents-deploy/1.0"
RETRY_STATUS = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 4
TIMEOUT_SECONDS = 30
MAX_ERROR_BODY = 600


class ApiError(RuntimeError):
    """Error de la API o de red, con mensaje ya sin secretos."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def redact(text: str, secret: str | None) -> str:
    """Quita la clave (y su cabecera) de un texto."""
    if not text:
        return text
    if secret:
        text = text.replace(secret, "***")
    return text


class ElevenLabsClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE,
        *,
        opener: Callable[..., Any] | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        if not api_key or not api_key.strip():
            raise ApiError("Falta ELEVENLABS_API_KEY en el entorno.")
        self._key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self._open = opener or urllib.request.urlopen
        self._sleep = sleep

    # ------------------------------------------------------------------ nucleo
    def _redact(self, text: str) -> str:
        return redact(text, self._key)

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: Any | None = None,
        idempotent: bool = True,
    ) -> Any:
        """Hace una llamada JSON. Reintenta (acotado) 429/5xx y fallos de red.

        Las llamadas no idempotentes (crear) solo se reintentan ante 429, que significa que
        el servidor no llego a procesarlas; asi no se duplican documentos ni agentes.
        """
        url = self.base_url + path
        if params:
            clean = [(k, str(v).lower() if isinstance(v, bool) else str(v)) for k, v in params.items() if v is not None]
            url += "?" + urllib.parse.urlencode(clean)
        data = None
        headers = {
            "xi-api-key": self._key,
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        last: ApiError | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            req = urllib.request.Request(url, data=data, method=method, headers=headers)
            try:
                with self._open(req, timeout=TIMEOUT_SECONDS) as resp:
                    raw = resp.read()
                    return json.loads(raw.decode("utf-8")) if raw.strip() else {}
            except urllib.error.HTTPError as exc:
                detail = self._read_error_body(exc)
                status = exc.code
                last = ApiError(f"{method} {path} -> HTTP {status}: {detail}", status)
                retryable = status in RETRY_STATUS if idempotent else status == 429
                if not retryable or attempt == MAX_ATTEMPTS:
                    raise last from None
                delay = self._retry_delay(exc, attempt)
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
                reason = self._redact(str(getattr(exc, "reason", exc)))
                last = ApiError(f"{method} {path} -> error de red: {reason}")
                # Un fallo de red en una llamada de creacion puede haberse procesado: no reintentar.
                if not idempotent or attempt == MAX_ATTEMPTS:
                    raise last from None
                delay = 2 ** (attempt - 1)
            except json.JSONDecodeError:
                raise ApiError(f"{method} {path} -> respuesta que no es JSON valido") from None
            self._sleep(delay)
        raise last or ApiError(f"{method} {path} -> fallo desconocido")

    def _read_error_body(self, exc: urllib.error.HTTPError) -> str:
        try:
            text = exc.read().decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001 - cuerpo ilegible no debe ocultar el estado HTTP
            text = ""
        text = " ".join(text.split())
        return self._redact(text)[:MAX_ERROR_BODY] or "(sin cuerpo)"

    @staticmethod
    def _retry_delay(exc: urllib.error.HTTPError, attempt: int) -> float:
        retry_after = exc.headers.get("Retry-After") if exc.headers else None
        if retry_after:
            try:
                return min(float(retry_after), 30.0)
            except ValueError:
                pass
        return float(2 ** (attempt - 1))

    # ------------------------------------------------------- base de conocimiento
    def list_documents(self, name_prefix: str) -> list[dict[str, Any]]:
        docs: list[dict[str, Any]] = []
        cursor: str | None = None
        for _ in range(100):  # tope de seguridad de paginas
            page = self.request(
                "GET",
                "/v1/convai/knowledge-base",
                params={"search": name_prefix, "page_size": 100, "cursor": cursor},
            )
            docs.extend(page.get("documents", []))
            if not page.get("has_more") or not page.get("next_cursor"):
                break
            cursor = page["next_cursor"]
        # `search` es prefijo segun la documentacion; se vuelve a filtrar por si acaso.
        return [d for d in docs if str(d.get("name", "")).startswith(name_prefix)]

    def create_text_document(self, name: str, text: str) -> dict[str, Any]:
        return self.request(
            "POST", "/v1/convai/knowledge-base/text", body={"name": name, "text": text}, idempotent=False
        )

    def compute_rag_index(self, doc_id: str, model: str) -> dict[str, Any]:
        return self.request("POST", f"/v1/convai/knowledge-base/{doc_id}/rag-index", body={"model": model})

    def get_rag_indexes(self, doc_id: str) -> list[dict[str, Any]]:
        return self.request("GET", f"/v1/convai/knowledge-base/{doc_id}/rag-index").get("indexes", [])

    def get_rag_usage(self) -> dict[str, Any]:
        return self.request("GET", "/v1/convai/knowledge-base/rag-index")

    def delete_document(self, doc_id: str, force: bool = False) -> None:
        self.request("DELETE", f"/v1/convai/knowledge-base/{doc_id}", params={"force": force})

    # ------------------------------------------------------------------- agentes
    def list_agents(self, search: str) -> list[dict[str, Any]]:
        agents: list[dict[str, Any]] = []
        cursor: str | None = None
        for _ in range(100):
            page = self.request(
                "GET", "/v1/convai/agents", params={"search": search, "page_size": 100, "cursor": cursor}
            )
            agents.extend(page.get("agents", []))
            if not page.get("has_more") or not page.get("next_cursor"):
                break
            cursor = page["next_cursor"]
        return agents

    def create_agent(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", "/v1/convai/agents/create", body=payload, idempotent=False)

    def get_agent(self, agent_id: str) -> dict[str, Any]:
        return self.request("GET", f"/v1/convai/agents/{agent_id}")

    def update_agent(self, agent_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("PATCH", f"/v1/convai/agents/{agent_id}", body=payload)


def key_from_env(env: dict[str, str] | None = None) -> str:
    env = os.environ if env is None else env
    key = env.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        raise ApiError(
            "No hay ELEVENLABS_API_KEY en el entorno. En GitHub debe venir del secreto del Environment "
            "'POC' (el job debe declarar `environment: POC`)."
        )
    return key
