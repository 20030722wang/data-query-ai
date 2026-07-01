"""Merge retrieved column/metric/value metadata into structured table/metric summaries.

Fetches missing column and table info from the meta DB using concurrent
``asyncio.gather`` calls instead of the original sequential N+1 pattern.
"""

import asyncio

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import (
    ColumnInfoState,
    DataAgentState,
    MetricInfoState,
    TableInfoState,
)
from app.core.log import logger
from app.entities.column_info import ColumnInfo
from app.entities.metric_info import MetricInfo
from app.entities.table_info import TableInfo
from app.entities.value_info import ValueInfo


async def merge_retrieved_info(
    state: DataAgentState, runtime: Runtime[DataAgentContext],
):
    """Merge and enrich retrieved metadata with concurrent DB lookups.

    Steps:
    1. Collect missing column IDs from metric ``relevant_columns`` and values.
    2. Fetch all missing columns in one ``asyncio.gather`` batch.
    3. Group columns by table ID.
    4. Fetch table + key-column metadata concurrently per table.
    5. Build the final ``table_infos`` and ``metric_infos`` state payloads.
    """
    writer = runtime.stream_writer
    step = "合并召回信息"
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        retrieved_column_infos: list[ColumnInfo] = state["retrieved_column_infos"]
        retrieved_metric_infos: list[MetricInfo] = state["retrieved_metric_infos"]
        retrieved_value_infos: list[ValueInfo] = state["retrieved_value_infos"]

        repo = runtime.context["meta_mysql_repository"]

        # Build initial column map from directly-retrieved columns
        col_map: dict[str, ColumnInfo] = {
            c.id: c for c in retrieved_column_infos
        }

        # Collect all missing column IDs from metrics and values
        missing_ids: set[str] = set()
        for metric in retrieved_metric_infos:
            for col_id in metric.relevant_columns:
                if col_id not in col_map:
                    missing_ids.add(col_id)
        for vi in retrieved_value_infos:
            if vi.column_id not in col_map:
                missing_ids.add(vi.column_id)

        # Fetch all missing columns concurrently
        if missing_ids:
            tasks = [repo.get_column_info_by_id(cid) for cid in missing_ids]
            fetched = await asyncio.gather(*tasks)
            for col in fetched:
                if col:
                    col_map[col.id] = col

        # Merge value examples into column metadata
        for vi in retrieved_value_infos:
            if vi.column_id in col_map:
                col = col_map[vi.column_id]
                if vi.value not in col.examples:
                    col.examples.append(vi.value)

        # Group columns by table ID
        table_cols: dict[str, list[ColumnInfo]] = {}
        for col in col_map.values():
            table_cols.setdefault(col.table_id, []).append(col)

        # Fetch table info + key columns concurrently for every table
        table_ids = list(table_cols.keys())
        table_tasks = [repo.get_table_info_by_id(tid) for tid in table_ids]
        keycol_tasks = [repo.get_key_columns_by_table_id(tid) for tid in table_ids]

        tables_and_keys = await asyncio.gather(
            asyncio.gather(*table_tasks),
            asyncio.gather(*keycol_tasks),
        )
        table_results, keycol_results = tables_and_keys

        # Build table_infos payload
        table_infos: list[TableInfoState] = []
        for table_id, columns in table_cols.items():
            table: TableInfo | None = table_results[table_ids.index(table_id)]
            if not table:
                continue

            # Add key columns that aren't already present
            key_cols = keycol_results[table_ids.index(table_id)]
            existing_ids = {c.id for c in columns}
            for kc in key_cols:
                if kc.id not in existing_ids:
                    columns.append(kc)

            col_states = [
                ColumnInfoState(
                    name=c.name, type=c.type, role=c.role,
                    examples=c.examples, description=c.description, alias=c.alias,
                )
                for c in columns
            ]
            table_infos.append(TableInfoState(
                name=table.name, role=table.role,
                description=table.description, columns=col_states,
            ))

        # Build metric_infos payload
        metric_infos: list[MetricInfoState] = [
            MetricInfoState(
                name=m.name, description=m.description,
                relevant_columns=m.relevant_columns, alias=m.alias,
            )
            for m in retrieved_metric_infos
        ]

        writer({"type": "progress", "step": step, "status": "success"})
        return {"table_infos": table_infos, "metric_infos": metric_infos}
    except Exception as e:
        logger.error(f"合并召回信息失败:{e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise
