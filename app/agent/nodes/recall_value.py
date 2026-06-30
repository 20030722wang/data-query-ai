from langgraph.runtime import Runtime
from app.agent.llm import llm
from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.entities.value_info import ValueInfo
from app.prompt.prompt_loader import load_prompt
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from app.core.log import logger


async def recall_value(state:DataAgentState,runtime:Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    step = "召回字段取值"
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        query = state["query"]
        keywords = state["keywords"]
        value_es_repository = runtime.context["value_es_repository"]

        # 借助LLM扩展关键词
        prompt = PromptTemplate(template=load_prompt("extend_keywords_for_value_recall"), input_variables=['query'])
        output_parser = JsonOutputParser()
        chain = prompt | llm | output_parser

        result = await chain.ainvoke({"query": query})

        if isinstance(result, list):
            llm_keywords = result
        elif isinstance(result, dict):
            llm_keywords = list(result.values())[0] if result.values() else []
        else:
            llm_keywords = []

        keywords = set(keywords + llm_keywords)

        # 根据关键词召回字段取值
        value_infos_map: dict[str, ValueInfo] = {}
        for keyword in keywords:
            current_value_infos: list[ValueInfo] = await value_es_repository.search(keyword)
            for current_value_info in current_value_infos:
                if current_value_info.id not in value_infos_map:
                    value_infos_map[current_value_info.id] = current_value_info
        retrieved_value_infos: list[ValueInfo] = list(value_infos_map.values())
        writer({"type": "progress", "step": step, "status": "success"})
        logger.info(f"检索到字段取值信息：{list(value_infos_map.keys())}")
        return {"retrieved_value_infos": retrieved_value_infos}
    except Exception as e:
        logger.error(f"召回字段取值失败:{e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise
