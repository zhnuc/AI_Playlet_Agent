# 该文件封装项目中的模型调用入口。
# 主要负责读取环境变量、调用 planner agent 和角色 agent，
# 并对模型返回的 JSON 结构做基础解析与校验。
import json
import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI


def load_env() -> tuple[str, str, str]:
    """读取模型调用所需的环境变量。"""
    load_dotenv()

    base_url = os.getenv("base_url")
    api_key = os.getenv("api_key")
    model = os.getenv("model")

    if not base_url:
        raise ValueError("找不到 base_url")
    if not api_key:
        raise ValueError("找不到 api_key")
    if not model:
        raise ValueError("找不到 model")

    return base_url, api_key, model


def is_valid_role_response(payload: dict, role_name: str) -> bool:
    """校验角色 agent 的输出字段是否完整。"""
    required_keys = {"Inner_Thought", "Action", "Dialogue", "next_speaker"}
    return role_name in payload and required_keys.issubset(payload[role_name].keys())


def is_valid_summary_response(payload: dict[str, Any]) -> bool:
    """校验单角色摘要结果是否符合固定 schema。"""
    required_keys = {
        "carryover_summary",
        "current_goal",
        "beliefs_about_others",
        "unresolved_hook",
    }
    if not required_keys.issubset(payload.keys()):
        return False
    if not isinstance(payload["carryover_summary"], str):
        return False
    if not isinstance(payload["current_goal"], str):
        return False
    if not isinstance(payload["beliefs_about_others"], dict):
        return False
    if not isinstance(payload["unresolved_hook"], str):
        return False
    return True


def extract_json_text(raw_text: str | None) -> str:
    """从模型原始输出中提取可解析的 JSON 文本。"""
    if raw_text is None:
        raise ValueError("模型返回内容为空")

    stripped_text = raw_text.strip()
    if not stripped_text:
        raise ValueError("模型返回内容为空字符串")

    if stripped_text.startswith("```"):
        lines = stripped_text.splitlines()
        if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].startswith("```"):
            stripped_text = "\n".join(lines[1:-1]).strip()
            if stripped_text.lower().startswith("json"):
                stripped_text = stripped_text[4:].strip()

    start = stripped_text.find("{")
    end = stripped_text.rfind("}")
    if start == -1 or end == -1 or start > end:
        raise ValueError(f"模型输出中未找到 JSON 对象: {stripped_text[:200]}")

    return stripped_text[start : end + 1]


def parse_json_response(raw_text: str | None) -> dict:
    """解析模型返回的 JSON 对象。"""
    json_text = extract_json_text(raw_text)
    return json.loads(json_text)


class Planner_Agent:
    """负责生成每集大纲的总策划 agent。"""

    def __init__(self, base_url: str, api_key: str, model: str):
        """初始化总策划 agent。"""
        self.model = model
        self.client = OpenAI(base_url=base_url, api_key=api_key)

    def generate_outline(self, prompt: str) -> dict | str:
        """调用模型生成分集大纲。"""
        print(f"总策划Agent正在策划分集大纲,使用模型{self.model}")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            raw_text = response.choices[0].message.content
            return parse_json_response(raw_text)
        except (json.JSONDecodeError, ValueError) as exc:
            print(f"总策划Agent输出格式不正确:{exc}")
            return "format_error"
        except Exception as exc:
            print(f"总策划Agent调用Api失败:{exc}")
            return "api_error"


class Role_Agent_Box:
    """负责单角色响应生成的模型调用器。"""

    def __init__(self, base_url: str, api_key: str, model: str):
        """初始化角色 agent 调用器。"""
        self.model = model
        self.client = OpenAI(base_url=base_url, api_key=api_key)

    def generate_role_response(self, role_name: str, prompt: str) -> dict | str:
        """调用模型生成当前角色的一轮结构化输出。"""
        print(f"角色{role_name}的Agent正在调用中...")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            raw_text = response.choices[0].message.content
            raw_json = parse_json_response(raw_text)

            if not is_valid_role_response(raw_json, role_name):
                print(f"角色{role_name}的Agent输出字段不完整")
                return "key_error"

            return raw_json[role_name]
        except (json.JSONDecodeError, ValueError) as exc:
            preview = (raw_text[:200] if "raw_text" in locals() and raw_text else "EMPTY")
            print(f"角色{role_name}的Agent输出格式不正确:{exc}")
            print(f"角色{role_name}的Agent原始输出片段:{preview}")
            return "format_error"
        except Exception as exc:
            print(f"角色{role_name}的Agent调用失败:{exc}")
            return "api_error"


class Summary_Agent:
    """负责在集末压缩角色记忆的摘要 agent。"""

    def __init__(self, base_url: str, api_key: str, model: str):
        """初始化摘要 agent。"""
        self.model = model
        self.client = OpenAI(base_url=base_url, api_key=api_key)

    def build_summary_prompt(self, role_inputs: dict[str, dict[str, Any]]) -> str:
        """构造批量角色摘要请求 prompt。"""
        serialized_inputs = json.dumps(role_inputs, ensure_ascii=False, indent=2)
        return f"""
# Role:
你是短剧系统中的角色记忆整理器，只负责压缩已有信息，不负责编剧、扩写剧情或补写桥段。

# Task:
请基于输入中的角色可见事件和已有记忆，为每个角色整理出下一集可继承的结构化记忆。
你必须严格站在角色自己的视角总结，不允许使用上帝视角。

# Output Rules:
1. 只输出严格 JSON，不要输出解释文字。
2. 顶层 key 必须与输入中的角色名完全一致。
3. 每个角色必须输出以下字段：
   - carryover_summary: 角色视角下真正记住的关键信息
   - current_goal: 下一集最自然的推进目标
   - beliefs_about_others: 对其他角色的当前判断
   - unresolved_hook: 最值得延续到下一集的悬念或执念
4. 若某字段没有内容，允许输出空字符串或空对象。
5. 不要发明输入中不存在的新角色、新秘密或新剧情事实。

# Input:
{serialized_inputs}
"""

    def generate_role_summaries(self, role_inputs: dict[str, dict[str, Any]]) -> dict | str:
        """批量调用模型生成角色级摘要结果。"""
        print(f"摘要Agent正在整理角色记忆,使用模型{self.model}")

        try:
            prompt = self.build_summary_prompt(role_inputs)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            raw_text = response.choices[0].message.content
            raw_json = parse_json_response(raw_text)
            if not isinstance(raw_json, dict):
                print("摘要Agent输出顶层不是 JSON 对象")
                return "schema_error"
            return raw_json
        except (json.JSONDecodeError, ValueError) as exc:
            preview = (raw_text[:200] if "raw_text" in locals() and raw_text else "EMPTY")
            print(f"摘要Agent输出格式不正确:{exc}")
            print(f"摘要Agent原始输出片段:{preview}")
            return "format_error"
        except Exception as exc:
            print(f"摘要Agent调用失败:{exc}")
            return "api_error"

    def generate_role_summary(self, role_name: str, role_input: dict[str, Any]) -> dict | str:
        """单角色调用摘要入口，便于独立测试和复用。"""
        result = self.generate_role_summaries({role_name: role_input})
        if isinstance(result, str):
            return result
        summary_payload = result.get(role_name)
        if not isinstance(summary_payload, dict) or not is_valid_summary_response(summary_payload):
            print(f"摘要Agent返回的角色摘要 schema 不合法: {role_name}")
            return "schema_error"
        return summary_payload


class Muilty_Agent_Box(Role_Agent_Box):
    """兼容旧命名，内部复用新的角色 agent 调用器。"""


if __name__ == "__main__":
    from prompt import planner_agent_prompt

    base_url, api_key, model = load_env()
    planner_agent = Planner_Agent(base_url, api_key, model)
    output = planner_agent.generate_outline(planner_agent_prompt)
    print(type(output))
