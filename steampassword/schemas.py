from typing import Optional

import pydantic


class PasswordChangeParams(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)
    
    s: int
    account: int
    reset: int
    issueid: int
    lost: int = 0


class RSAKey(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True
    )
    
    mod: str = pydantic.Field(alias='publickey_mod')
    exp: str = pydantic.Field(alias='publickey_exp')
    timestamp: int
    token_gid: Optional[str] = None
