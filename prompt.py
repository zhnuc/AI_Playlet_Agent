# 该文件集中管理 prompt 文本的构造逻辑。
# 当前主要负责生成总策划 agent 使用的分集规划提示词，
# 并把角色卡与单场景约束组织成稳定的输入模板。
from global_config import global_config


def build_chara(global_config: dict) -> str:
    """构造 planner 使用的角色卡文本。"""
    chara_text = ""
    for name, info in global_config["character_roster"].items():
        appearance = "、".join(info["appearance_tags"])
        personality = "、".join(info["personality_tags"])
        chara_text += f"{info['char_id']}：{name}（{info['role_type']}）：\n"
        chara_text += f"-【基础信息】：{info['gender']}，{info['age']}岁，{info['identity']}\n"
        chara_text += f"-【外貌】：{appearance}\n"
        chara_text += f"-【性格】：{personality}\n"
        chara_text += f"-【口头禅】：{info['catchphrase']}\n\n"
    return chara_text


def build_planner_agent_prompt(global_config: dict) -> str:
    """构造总策划 agent 的提示词。"""
    chara_text = build_chara(global_config)
    return f"""
# Role:
你是一位打造过无数爆款（如流水过亿的复仇爽剧）的“金牌微短剧总策划”。你的核心能力是极其敏锐的市场嗅觉、精准的节奏把控以及制造让人欲罢不能的剧情悬念。

# Context:
现在，你的团队正在筹备一部新剧，基础设定如下：
-【题材】：{global_config['drama_settings']['theme']}
-【目标受众】：{global_config['drama_settings']['target_audience']}
-【预期集数】：{global_config['drama_settings']['expected_episodes']} 集
-【一句话故事核】：{global_config['logline']}

# Characters:
以下是本剧出场的核心角色卡（你必须严格遵循他们的性格和动机，挖掘他们之间的冲突）：
{chara_text}

# Task:
你的任务是根据以上信息，规划出全剧 {global_config['drama_settings']['expected_episodes']} 集的剧情大纲。

# Constraints & Rules:
1. 剧情节奏必须极快、极爽，每一集都必须有一个极其明确的核心冲突。
2. 每一集只允许一个主场景，聚焦单一时间和单一地点。
3. 你必须给出本集在场角色 `scene_roles`，该字段只填写本集主场景中实际参与互动的角色名列表。
4. 悬念钩子（Hook）：每一集的结尾必须卡在剧情最高潮或最意想不到的转折处，强迫观众看下一集。
5. 角色锦囊（Directives）：你不仅要写大纲，还必须为每一集出场角色制定“专属行动策略”。

# Output Format (Strict JSON):
你必须且只能输出严格的 JSON 格式，绝不允许包含 Markdown 代码块修饰符或额外解释。数据结构必须如下：
{{
  "episodes": [
    {{
      "episode_number": 1,
      "global_plot": "（一句话总结本集剧情精髓）",
      "place": "（本集的单一主要场景）",
      "scene_roles": ["（角色名A）", "（角色名B）", "（角色名C）"],
      "core_conflict": "（本集的具体矛盾爆发点）",
      "plot_twist_or_hook": "（本集结尾的钩子/悬念）",
      "first_speaker": "（本集第一个开口说话的角色名字，必须在 scene_roles 中）",
      "character_directives": {{
          "（角色名A）": "【本集情绪】：...【本集目标】：...【行动策略】：...",
          "（角色名B）": "【本集情绪】：...【本集目标】：...【行动策略】：...",
          "（角色名C）": "【本集情绪】：...【本集目标】：...【行动策略】：..."
      }}
    }}
  ]
}}
"""


chara_text = build_chara(global_config)
planner_agent_prompt = build_planner_agent_prompt(global_config)
