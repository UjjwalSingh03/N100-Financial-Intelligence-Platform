"""Export the actual FastAPI OpenAPI schema and a Postman v2.1 collection.

Run: python -m scripts.day40_export_api
"""
import json
from pathlib import Path
from src.api.main import app

def export(destination="docs"):
    folder = Path(destination)
    folder.mkdir(parents=True, exist_ok=True)
    schema = app.openapi()
    (folder / "openapi.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")
    items = []
    for path, operations in schema["paths"].items():
        for method, op in operations.items():
            if method.lower() not in ("get", "post", "put", "patch", "delete"): continue
            params = op.get("parameters", [])
            query = [{"key": p["name"], "value": "", "disabled": not p.get("required", False)}
                     for p in params if p["in"] == "query"]
            segments = [(":" + part[1:-1] if part.startswith("{") and part.endswith("}") else part)
                        for part in path.strip("/").split("/")]
            url = {"raw": "{{baseUrl}}/" + "/".join(segments), "host": ["{{baseUrl}}"],
                   "path": segments, "query": query}
            items.append({"name": op.get("summary", op["operationId"]), "request": {
                "method": method.upper(), "header": [], "url": url},
                "response": []})
    collection = {"info": {"name": "N100 Financial Intelligence API",
                           "description": "Generated from the FastAPI OpenAPI specification.",
                           "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
                  "item": items, "variable": [{"key": "baseUrl", "value": "http://127.0.0.1:8000"}]}
    (folder / "postman_collection.json").write_text(json.dumps(collection, indent=2), encoding="utf-8")
    return len(items)

if __name__ == "__main__":
    print(f"Exported {export()} operations to docs/openapi.json and docs/postman_collection.json")
