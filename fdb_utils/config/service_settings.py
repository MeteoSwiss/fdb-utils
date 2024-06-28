from pydantic import BaseModel
from pathlib import Path
from mch_python_commons.config.base_settings import BaseServiceSettings

class GRIBDefinitions(BaseModel):
    cosmo_eccodes: str
    eccodes: str

class LocalFDBSettings(BaseModel):
    root: Path
    schema: Path

class RemoteFDBSettings(BaseModel):
    hostname: str
    port: int

class FDBSettings(BaseModel):
    local: LocalFDBSettings
    remote: RemoteFDBSettings
    fdb_home: Path
    definitions: GRIBDefinitions

class Settings(BaseServiceSettings):
    main: FDBSettings
