BodhiRAG-main/
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app initialization
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── chat_models.py   # ← ADD MODELS HERE
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── chat.py          # ← ADD ROUTES WITH RATE LIMITING HERE
│   ├── services/
│   │   ├── __init__.py
│   │   └── rag_service.py       # Your RAG business logic
│   └── core/
│       ├── __init__.py
│       └── config.py            # App configuration
├── requirements.txt
└── main.py                      # Optional: top-level runner