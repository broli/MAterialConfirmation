from pydantic import BaseModel, Field, model_validator
from typing import Optional, Dict, Any

class ContractItem(BaseModel):
    category: Optional[str] = Field(default=None, description="The general category, e.g., 'Vanity', 'Faucet', 'Grab Bar'")
    base_item: Optional[str] = Field(default=None, description="The core item description without sizes or finishes")
    brand: Optional[str] = Field(default=None, description="The manufacturer brand, e.g., 'Moen', 'Kohler'")
    finish: Optional[str] = Field(default=None, description="The color or texture, e.g., 'Matte Black', 'Chrome'")
    dimensions: Dict[str, Optional[str]] = Field(
        default_factory=dict, 
        description="Extracted dimensions as key-value pairs, e.g., {'width': '48', 'height': '34'}"
    )

    @model_validator(mode='before')
    @classmethod
    def coerce_and_unwrap(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Unwrap hallucinated properties key
            if 'properties' in data and isinstance(data['properties'], dict):
                data = data['properties']
                
            # Coerce complex structures to string for strict fields
            for key, val in data.items():
                if key == 'dimensions' and isinstance(val, dict):
                    new_dims = {}
                    for d_k, d_v in val.items():
                        if d_v is None:
                            new_dims[d_k] = None
                        elif isinstance(d_v, dict):
                            new_dims[d_k] = " ".join(f"{k} {v}" for k, v in d_v.items())
                        elif isinstance(d_v, list):
                            new_dims[d_k] = " ".join(str(i) for i in d_v)
                        else:
                            new_dims[d_k] = str(d_v)
                    data['dimensions'] = new_dims
                elif key != 'dimensions' and val is not None:
                    if isinstance(val, dict):
                        data[key] = " ".join(f"{k} {v}" for k, v in val.items())
                    elif isinstance(val, list):
                        data[key] = " ".join(str(i) for i in val)
                    else:
                        data[key] = str(val)
        return data
