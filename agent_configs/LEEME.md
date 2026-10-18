# agent_configs/ — el agente como código (CDU-001)

| Archivo | Qué es |
| --- | --- |
| `cdu-001-agent.json` | Configuración del agente en el formato de la API REST de ElevenLabs (`name`, `tags`, `conversation_config`) más un bloque `deploy` con ajustes del script. |
| `cdu-001-system-prompt.md` | Prompt aprobado (v0.1). Se despliega solo el bloque entre ``` bajo `## Prompt`. |
| `cdu-001-prompt-resoluciones.json` | Cómo resolver los marcadores `<...>` del prompt. Cada entrada necesita `aprobado: true` para aplicarse. Hoy están **sin aprobar** (son propuestas). |

El despliegue lo hace `scripts/deploy_agent.py` (ver `docs/guias/despliegue-cdu-001.md`). El script inyecta el prompt y los documentos del manual (`prompt` y `knowledge_base` NO van en el JSON) y descarta cualquier clave que empiece con `_`.

## Qué cambiar y dónde

| Quiero cambiar | Dónde (en `cdu-001-agent.json`) | Valor inicial |
| --- | --- | --- |
| Modelo de lenguaje | `conversation_config.agent.prompt.llm` | `gemini-2.5-flash` (elegido, sin comparar) |
| Idioma | `conversation_config.agent.language` | `es` |
| Primer mensaje | `conversation_config.agent.first_message` | vacío (en WhatsApp escribe primero la persona). El script falla si no está vacío. |
| RAG: modelo de embeddings | `...prompt.rag.embedding_model` | `e5_mistral_7b_instruct` (el de la documentación; `multilingual_e5_large_instruct` también existe, sin probar) |
| RAG: distancia máxima | `...prompt.rag.max_vector_distance` | 0.6 — **por calibrar** (más bajo = más estricto = más "no encuentro") |
| RAG: longitud máxima recuperada | `...prompt.rag.max_documents_length` | 50000 — **por calibrar** |
| RAG: fragmentos recuperados | `...prompt.rag.max_retrieved_rag_chunks_count` | 20 — **por calibrar** |
| Herramientas de sistema | `...prompt.built_in_tools` | solo `end_call` |
| Nombre del agente | `name` (es la clave de idempotencia: cambiarlo crea un agente nuevo) | `CDU-001 Haval H6 - manual (POC)` |
| Topes del manual | `deploy.min_doc_bytes`, `deploy.max_total_bytes` | 500 bytes; 2 000 000 bytes |

Los valores de RAG son los **predeterminados que muestra la referencia de la API** (no valores calibrados). Cambiar cualquier valor del prompt o de RAG exige pruebas del agente en verde (constitución, principio II); las pruebas del agente aún no existen (ver la guía de despliegue).

## Lo que NO se configura aquí

- Ajustes por número de WhatsApp (respuesta en audio, indicador de escritura, mensajería): son de la cuenta de WhatsApp importada, no del agente. Se hacen en el panel (guía `cdu-001-servicios-y-configuracion.md`, paso 12). No hay forma documentada de ponerlos por este archivo.
- `platform_settings` (criterios de éxito y extracción de datos de conversaciones): no se envía nada todavía porque el esquema exacto está por verificar.
- Duración máxima de conversación y mensaje de cierre: quedan en los valores de la plataforma hasta que Christian decida.
