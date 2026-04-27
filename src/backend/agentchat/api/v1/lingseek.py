import json
from fastapi import APIRouter, Depends
from starlette.responses import StreamingResponse

from agentchat.api.services.user import UserPayload, get_login_user
from agentchat.schemas. import GuidePrompt, GuidePromptFeedBack, Task
from agentchat.schemas.usage_stats import UsageStatsAgentType
from agentchat.services..agent import Agent
from agentchat.utils.contexts import set_user_id_context, set_agent_name_context

router = APIRouter(prefix="/workspace/", tags=[""])


@router.post("/guide_prompt", summary="生成灵寻的指导提示")
async def generate__guide_prompt(
    *,
    _info: GuidePrompt,
    login_user: UserPayload = Depends(get_login_user)
):
    # 设置全局变量统计调用
    set_user_id_context(login_user.user_id)
    set_agent_name_context(UsageStatsAgentType._agent)

    _agent = Agent(login_user.user_id)

    async def general_generate():
        async for chunk in _agent.generate_guide_prompt(_info):
            yield f"data: {json.dumps(chunk)}\n\n"

    return StreamingResponse(general_generate(), media_type="text/event-stream")


@router.post("/guide_prompt/feedback", summary="根据用户的反馈进行重新生成")
async def rebuild_generate__guide_prompt(
    *,
    feedback_guide_prompt: GuidePromptFeedBack,
    login_user: UserPayload = Depends(get_login_user)
):
    # 设置全局变量统计调用
    set_user_id_context(login_user.user_id)
    set_agent_name_context(UsageStatsAgentType._agent)

    _agent = Agent(login_user.user_id)

    async def general_generate():
        async for chunk in _agent.generate_guide_prompt(feedback_guide_prompt, True):
            yield f"data: {json.dumps(chunk)}\n\n"

    return StreamingResponse(general_generate(), media_type="text/event-stream")


@router.post("/task", summary="灵寻生成的任务列表")
async def generate__tasks(
    *,
    task: Task,
    login_user: UserPayload = Depends(get_login_user)
):
    _agent = Agent(login_user.user_id)

    async def general_generate():
        async for chunk in _agent.generate_tasks(task):
            yield chunk

    return StreamingResponse(general_generate(), media_type="text/event-stream")


@router.post("/task_start", summary="灵寻开始执行任务")
async def submit__task(
    *,
    task: Task,
    login_user: UserPayload = Depends(get_login_user)
):
    # 设置全局变量统计调用
    set_user_id_context(login_user.user_id)
    set_agent_name_context(UsageStatsAgentType._agent)

    _agent = Agent(login_user.user_id)

    async def general_generate():
        async for chunk in _agent.submit__task(task):
            yield f"data: {json.dumps(chunk)}\n\n"
    return StreamingResponse(general_generate(), media_type="text/event-stream")