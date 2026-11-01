from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, List, Any
from datetime import datetime, date


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Pagination(BaseModel):
    page: int = 1
    page_size: int = 20
    total: int = 0
    items: List[Any] = []
