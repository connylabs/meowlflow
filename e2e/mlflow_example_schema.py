from typing import Any, Dict, List

import pandas
import pydantic.dataclasses

from meowlflow.api.base import (
    BaseRequest,
    BaseResponse,
)

description = "This is an example MLflow project that models wine preferences."
title = "Example MLflow Project"
version = "0.1.0"


class Config:
    arbitrary_types_allowed = True


@pydantic.dataclasses.dataclass(config=Config)
class Properties:
    alcohol: float
    chlorides: float
    citric_acid: float
    density: float
    fixed_acidity: float
    free_sulfur_dioxide: float
    pH: float
    residual_sugar: float
    sulphates: float
    total_sulfur_dioxide: float
    volatile_acidity: float


_MAP: Dict[str, str] = {
    "alcohol": "alcohol",
    "chlorides": "chlorides",
    "citric_acid": "citric acid",
    "density": "density",
    "fixed_acidity": "fixed acidity",
    "free_sulfur_dioxide": "free sulfur dioxide",
    "pH": "pH",
    "residual_sugar": "residual sugar",
    "sulphates": "sulphates",
    "total_sulfur_dioxide": "total sulfur dioxide",
    "volatile_acidity": "volatile acidity",
}


class Request(BaseRequest):
    __root__: List[Properties]

    def transform(self) -> Any:
        data: List[Dict[str, float]] = []
        for properties in self.__root__:
            pdict: Dict[str, float] = {}
            for k, v in properties.__dict__.items():
                if k in _MAP:
                    pdict[_MAP[k]] = v
            data += [pdict]
        return pandas.DataFrame.from_records(data)

    class Config:
        schema_extra = {
            "example": [
                {
                    "alcohol": 12.8,
                    "citric_acid": 0.029,
                    "chlorides": 0.48,
                    "density": 0.98,
                    "fixed_acidity": 6.2,
                    "free_sulfur_dioxide": 29,
                    "pH": 3.33,
                    "residual_sugar": 1.2,
                    "sulphates": 0.39,
                    "total_sulfur_dioxide": 75,
                    "volatile_acidity": 0.66,
                }
            ]
        }


class Response(BaseResponse):
    predictions: List[float]

    @classmethod
    def transform(cls, data: Any) -> Any:
        return {"predictions": list(data)}

    class Config:
        schema_extra = {"example": {"predictions": [6.379428821398614]}}
