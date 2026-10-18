# poc-agents

POC de un agente de WhatsApp con ElevenLabs que responde únicamente desde una base de preguntas frecuentes (FAQ) indexada con RAG, sin backend propio en el camino crítico. Se construye con Spec-Driven Development (GitHub Spec Kit) y se despliega con GitHub Actions.

## Estructura

```
poc-agents/
├── .specify/ y specs/        # Spec Kit: constitución y una carpeta por feature (los crea `specify init`)
├── agents.json               # agentes gestionados por el CLI de ElevenLabs (lo crea el CLI)
├── tools.json                # solo si se añaden herramientas (lo crea el CLI)
├── tests.json                # pruebas del agente (lo crea el CLI)
├── agent_configs/            # prompt, RAG, análisis, mensajería
├── tool_configs/
├── test_configs/             # pruebas de respuesta y de herramienta
├── knowledge/
│   ├── faq/*.md              # la FAQ, un archivo por tema
│   ├── manifest.json         # archivo -> ID de documento (producción)
│   └── manifest.staging.json # archivo -> ID de documento (staging)
├── scripts/                  # sync_faq.py (sincroniza la FAQ por API)
├── receptor/                 # opcional: webhook post-conversación
└── .github/workflows/        # ci.yml, deploy-staging.yml, deploy-prod.yml
```

Los archivos `agents.json`, `tools.json` y `tests.json` los genera el CLI de ElevenLabs al inicializar el proyecto, y las carpetas de Spec Kit se crean con `specify init`; por eso aún no están en el repositorio.

## Principios

- El agente, la FAQ y sus pruebas son código versionado.
- Ninguna credencial entra al repositorio (`ELEVENLABS_API_KEY` vive en GitHub Secrets).
- Todo cambio de prompt o de FAQ pasa las pruebas del agente antes del merge.
