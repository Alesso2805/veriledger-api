from backend.app.main import app
from backend.app.openapi_document import DOCUMENT, render


def test_docs_openapi_json_is_the_document_the_app_serves() -> None:
    # read_text turns Windows line ends back into \n, so a checkout with autocrlf compares equal too
    assert DOCUMENT.read_text(encoding="utf-8") == render(app.openapi()), "docs/openapi.json is stale: run make openapi"


def test_every_operation_answers_a_named_schema_and_the_enums_are_named() -> None:
    # What the webapp's generated types need: no {} response, and enums it can import by name
    document = app.openapi()
    unnamed: list[str] = []
    for path, item in document["paths"].items():
        for method, operation in item.items():
            success = next(response for code, response in operation["responses"].items() if code.startswith("2"))
            schema = success["content"]["application/json"]["schema"]
            if "$ref" not in schema and "$ref" not in schema.get("items", {}):
                unnamed.append(f"{method.upper()} {path}")
    assert unnamed == []
    assert {"TransactionStatus", "UserRole"} <= set(document["components"]["schemas"])
