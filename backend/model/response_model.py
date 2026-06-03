from pydantic import BaseModel
from typing import Any, Dict


class ResponseModel(BaseModel):
    def __init__(self, *args, **kwargs):
        """Dynamically initialize the Response Model by validating provided fields against the runtime class definition.
        """
        super().__init__(*args, **kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """Converts internal class schema data into standard Python dictionary.
        """
        return self.instance.model_dump()
    
    def to_json(self, indent: int = None) -> str:
        """Converts internal class schema data into standard JSON string format.
        :param indent: Optional, size of json indentation
        """
        return self.instance.model_dump_json(indent=indent)
    