# 该文件封装项目中的模型调用入口。
# 主要负责读取环境变量、调用 planner agent 和角色 agent，
# 并对模型返回的 JSON 结构做基础解析与校验。
import json
import os

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


class Muilty_Agent_Box(Role_Agent_Box):
    """兼容旧命名，内部复用新的角色 agent 调用器。"""


if __name__ == "__main__":
    from prompt import planner_agent_prompt

    base_url, api_key, model = load_env()
    planner_agent = Planner_Agent(base_url, api_key, model)
    output = planner_agent.generate_outline(planner_agent_prompt)
    print(type(output))
