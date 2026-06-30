from dataclasses import asdict

from app.entities.metric_info import MetricInfo
from app.models.metric_info import MetricInfoMySQL

class MetricInfoMapper:
    @staticmethod
    def to_entity(model: MetricInfoMySQL) -> MetricInfo:
        return MetricInfo(
            id=model.id or "",
            name=model.name or "",
            description=model.description or "",
            relevant_columns=model.relevant_columns if isinstance(model.relevant_columns, list) else [],
            alias=model.alias if isinstance(model.alias, list) else [],
        )

    @staticmethod
    def to_model(entity: MetricInfo):
        return MetricInfoMySQL(**asdict(entity))