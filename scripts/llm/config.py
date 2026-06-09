"""Config Ollama partagée — source unique URL.

IPv4 explicite : `localhost` résout `::1` en premier sur Windows → timeout
~2 s avant fallback IPv4. Tous les modules llm/ importent d'ici.
"""
OLLAMA_URL = "http://127.0.0.1:11434"
