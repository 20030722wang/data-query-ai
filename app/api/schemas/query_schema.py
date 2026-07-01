"""Request schema for the query endpoint."""

from pydantic import BaseModel, Field


class QuerySchema(BaseModel):
    """Natural-language query input with length constraints.

    Attributes:
        query: The user's question in natural language (1‒1000 characters).
    """
    query: str = Field(
        min_length=1,
        max_length=1000,
        description="User's natural language query",
        examples=["统计华北地区的销售总额"],
    )
