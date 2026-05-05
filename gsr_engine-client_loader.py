import importlib


def load_client(client_id: str = "default"):
    module_name = f"clients.{client_id}"

    try:
        module = importlib.import_module(module_name)
        return module.CLIENT
    except Exception:
        fallback = importlib.import_module("clients.default_client")
        return fallback.CLIENT