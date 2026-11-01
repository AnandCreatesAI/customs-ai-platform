"""
Documented architecture for post–Phase 0 training and chat retrieval.

Nothing in this module performs training, indexing, or chat RAG. It records contracts
for later phases so all BusinessModel keys share one pipeline.

Common training pipeline (future phases)
----------------------------------------
Input → Validation → Secure Storage → Content Extraction → Normalization → Chunking
→ Embedding (dedicated embedding service, not LLMGateway.generate) → Model-scoped Qdrant
indexing → Training completion.

Input channels (same BusinessModel scope for all):
- File upload (pdf, docx, doc, txt, xlsx, xls, csv, json)
- Text (title + body, centrally limited)
- JSON (title + structured object/array, syntax validated)

Multi-model extensibility
-------------------------
Register or seed a BusinessModel row; storage paths and validation stay shared.
Model-specific behavior belongs behind small extension hooks only when required.

User and model isolation (storage and APIs)
-------------------------------------------
Every stored document is scoped by authenticated user id, BusinessModel id/key, and
document UUID. Storage keys include user id and business_model.key. Future list/detail/
delete/upload endpoints must filter with request.user and verify business_model on every
operation. Never trust client-supplied user ids for ownership.

Chat and retrieval consistency (future phases)
----------------------------------------------
Training under a BusinessModel tags metadata and vector indexes with that model.
Chat retrieval uses the conversation's business_model as authoritative scope: only
knowledge indexed for that model is eligible; private knowledge additionally requires
matching user. No cross-model or cross-user retrieval.

Object storage (future configuration)
-------------------------------------
Set DOCUMENT_STORAGE_BACKEND to a Django S3-compatible storage backend and supply the
vendor OPTIONS (bucket, region, credentials via environment). Keep DOCUMENT_STORAGE_ROOT
for local FileSystemStorage only.

Document delete (future APIs)
-----------------------------
After authorization (``request.user`` + business model scope), delete the ``Document`` row
then remove the storage key via ``delete_stored_document`` (or equivalent) so orphaned
binaries are not left on disk.
"""
