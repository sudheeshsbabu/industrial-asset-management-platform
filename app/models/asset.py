from pydantic import BaseModel
from typing import Optional

class AssetCreate(BaseModel):
    name: str
    site: str
    status: str

class AssetResponse(BaseModel):
    id: int
    name: str
    site: str
    status: str

class AssetUpdate(BaseModel):
    name: Optional[str] = None
    site: Optional[str] = None
    status: Optional[str] = None