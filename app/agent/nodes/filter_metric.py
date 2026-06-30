import yaml
from langgraph.runtime import Runtime
from langchain_core.prompts import PromptTemplate
from app.prompt.prompt_loader import load_prompt
from langchain_core.output_parsers import JsonOutputParser
from app.agent.llm import llm
from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState, MetricInfoState
from app.core.log import logger



async def filter_metric(state:DataAgentState,runtime:Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    step = "过滤指标信息"
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        query = state["query"]
        metric_infos: list[MetricInfoState] = state["metric_infos"]

        if not metric_infos:
            writer({"type": "progress", "step": step, "status": "success"})
            logger.info("无指标信息需要过滤，跳过")
            return {"metric_infos": []}

        prompt = PromptTemplate(template=load_prompt("filter_metric_info"), input_variables=['query', 'metric_infos'])
        output_parser = JsonOutputParser()
        chain = prompt | llm | output_parser

        result = await chain.ainvoke({"query": query,
                                      "metric_infos": yaml.dump(metric_infos, allow_unicode=True, sort_keys=False)})

        if not isinstance(result, list):
            result = []

        filter_metric_infos = [metric_info for metric_info in metric_infos if metric_info["name"] in result]
        writer({"type": "progress", "step": step, "status": "success"})

        logger.info(f"过滤指标信息成功：{[filter_metric_info['name'] for filter_metric_info in filter_metric_infos]}")
        return {"metric_infos": filter_metric_infos}
    except Exception as e:
        logger.error(f"过滤指标信息失败:{e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise
