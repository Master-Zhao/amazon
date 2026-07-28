# OpenAPI contract artifacts

`schema.yaml` is generated from Django with:

```powershell
uv run python backend/manage.py spectacular --file openapi/schema.yaml --validate
```

The frontend consumes this file through `pnpm --dir frontend generate:api`.
