---
name: add-model
description: Add or extend a Beanie MongoDB document model in a BarriApp module, following the data-model conventions (enums, embedded sub-docs, indexes incl. 2dsphere and partial-unique, timestamps) and registering it with Beanie. Use when creating a new collection or adding fields to an existing one.
---

# Add a Beanie model

Add a `Document` (or embedded `BaseModel`) consistent with `docs/DATA_MODEL.md`.
**Reference: `app/users/models.py` and `app/audit/models.py`.**

## Steps
1. **Check the spec** in `docs/DATA_MODEL.md` for the collection's fields, types,
   relationships, and indexes. Match field names and semantics exactly.
2. **Define enums** as `StrEnum` (see `Role`, `UserStatus`, `AuditModule`).
3. **Define embedded objects** as `pydantic.BaseModel` (see `Address`, `GeoPoint`,
   `Consent`). GeoJSON points use `coordinates: tuple[float, float]` = `[lng, lat]`.
4. **Define the Document** with:
   - Full type annotations; `Field(default_factory=...)` for mutable defaults.
   - `created_at` / `updated_at` via a module-level `_utcnow()` returning
     `datetime.now(UTC)`.
   - A `Settings` inner class with `name = "<collection>"` and `indexes` (use
     `# noqa: RUF012` on the `indexes` list).
5. **Indexes** with `pymongo.IndexModel`:
   - Unique: `IndexModel("field", unique=True)`.
   - **Nullable-unique** (e.g. optional email): use a **partial** index, NOT sparse —
     `IndexModel("email", unique=True, partialFilterExpression={"email": {"$type": "string"}})`
     (sparse only skips *missing* fields, not `null` values).
   - **Geo**: `IndexModel([("location.geo", "2dsphere")])`.
   - Compound: `IndexModel([("a", 1), ("b", -1)])`.
6. **Register** the Document in `_document_models()` in `app/core/db.py`.
7. **Snapshots**: for historical records (e.g. order items), store a copy of the
   values at the time (name/price), not just a reference — see `docs/DATA_MODEL.md` §1.
8. **Gates**: `uv run mypy app && uv run ruff check . && uv run pytest -q`.

## Notes
- Beanie 2.x uses PyMongo's native async client (not Motor).
- Never store secrets in models; PII fields must be handled per `docs/AUDIT_LOG.md`.

## Related skills
`scaffold-module`, `add-endpoint`.
