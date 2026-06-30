import yaml
from langgraph.runtime import Runtime
from langchain_core.prompts import PromptTemplate
from app.prompt.prompt_loader import load_prompt
from langchain_core.output_parsers import JsonOutputParser
from app.agent.llm import llm
from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState, TableInfoState
from app.core.log import logger


async def filter_table(state:DataAgentState,runtime:Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    step = "过滤表信息"
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        query = state["query"]
        table_infos: list[TableInfoState] = state["table_infos"]

        if not table_infos:
            writer({"type": "progress", "step": step, "status": "success"})
            logger.info("无表信息需要过滤，跳过")
            return {"table_infos": []}

        prompt = PromptTemplate(template=load_prompt("filter_table_info"), input_variables=['query', 'table_infos'])
        output_parser = JsonOutputParser()
        chain = prompt | llm | output_parser

        result = await chain.ainvoke({"query": query,
                                      "table_infos": yaml.dump(table_infos, allow_unicode=True, sort_keys=False)})

        if not isinstance(result, dict):
            result = {}

        filter_table_infos: list[TableInfoState] = []
        for table_info in table_infos:
            if table_info["name"] in result:
                selected_columns = result[table_info["name"]]
                if isinstance(selected_columns, list):
                    table_info["columns"] = [column_info for column_info in table_info["columns"] if
                                             column_info["name"] in selected_columns]
                    filter_table_infos.append(table_info)
        writer({"type": "progress", "step": step, "status": "success"})
        logger.info(f"过滤表信息：{[filter_table_info["name"] for filter_table_info in filter_table_infos]}")
        return {"table_infos": filter_table_infos}
    except Exception as e:
        logger.error(f"过滤表信息失败:{e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise
