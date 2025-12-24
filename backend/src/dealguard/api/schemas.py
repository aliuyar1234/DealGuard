"""Shared API schemas and base models."""

from pydantic import BaseModel, ConfigDict


class APIRequestModel(BaseModel):
    """Base model for request bodies.

    Forbids unknown fields to avoid silently accepting typos or outdated clients.
    """

    model_config = ConfigDict(extra="forbid")
