from __future__ import annotations

import struct

from apps.document_chunking.constants import (
    VECTOR_DTYPE_FLOAT32,
    VECTOR_SERIALIZATION_VERSION,
)


class VectorSerializationError(ValueError):
    pass


def serialize_float32_vector(values: list[float]) -> bytes:
    return struct.pack(f'<{len(values)}f', *values)


def deserialize_float32_vector(
    payload: bytes,
    *,
    dimension: int,
    serialization_version: int,
    dtype: str,
) -> list[float]:
    if serialization_version != VECTOR_SERIALIZATION_VERSION:
        raise VectorSerializationError(
            f'Unsupported serialization version: {serialization_version}'
        )
    if dtype != VECTOR_DTYPE_FLOAT32:
        raise VectorSerializationError(f'Unsupported dtype: {dtype}')
    expected_len = dimension * 4
    if len(payload) != expected_len:
        raise VectorSerializationError(
            f'Payload length {len(payload)} does not match dimension {dimension} '
            f'(expected {expected_len} bytes).'
        )
    return list(struct.unpack(f'<{dimension}f', payload))


def validate_vector_payload(
    payload: bytes,
    *,
    dimension: int,
    serialization_version: int,
    dtype: str,
) -> None:
    deserialize_float32_vector(
        payload,
        dimension=dimension,
        serialization_version=serialization_version,
        dtype=dtype,
    )
