import textwrap


class Planner_Agent_Prompt():
  
    def __init__(self,global_config):
        
        self.global_config=global_config

    # ---------- 生成总策划Agent的prompt -----------
    def generate_prompt(self,user_feedback=None):

        # ----- 拼接角色信息 -----
        chara_text=""
        for name,info in self.global_config["character_roster"].items():
            apperance=",".join(info['appearance_tags'])
            personality=",".join(info['personality_tags'])
            chara_text+=f"{info['char_id']}:{name}({info['role_type']}):\n"
            chara_text+=f"-[基础信息]:{info['gender']},{info['age']}岁,{info['identity']}\n"
            chara_text+=f"-[外貌]:{apperance}\n"
            chara_text+=f"-[性格]:{personality}\n"
            chara_text+=f"-[口头禅]:{info['catchphrase']}\n\n"

        # ----- 将用户反馈融入提示词 -----
        if user_feedback is not None:
            feedback_prompt=f"\n# User Feedback:\n制片人(用户)针对你生成的内容,提出了如下意见:{user_feedback}\n你必须将其作为最高优先级,根据指示生成内容"
        else:
            feedback_prompt=""

        prompt=textwrap.dedent(f"""
                                # Role:
                                你是一位打造过无数爆款(如流水过亿的复仇爽剧)的"金牌微短剧总策划",你的核心能力是极其敏锐的市场嗅觉、精准的节奏把控以及制造让人欲罢不能的剧情悬念

                                # Context:
                                现在,你的团队正在筹备一部新剧,基础设定如下:
                                -[题材]:{self.global_config['drama_settings']['theme']}
                                -[目标受众]:{self.global_config['drama_settings']['target_audience']}
                                -[预期集数]:{self.global_config['drama_settings']['expected_episodes']}集
                                -[一句话故事核]:{self.global_config['logline']}

                                # Characters:
                                以下是本剧出场的核心角色卡(你必须严格遵循他们的性格和动机,挖掘他们之间的冲突):
                                {chara_text}
                                {feedback_prompt}
                                # Task:
                                你的任务是根据以上信息,规划出全剧{self.global_config['drama_settings']['expected_episodes']}集的剧情大纲

                                # Constraints & Rules:
                                1.剧情节奏必须极快、极爽,每一集都必须有一个极其明确的核心冲突(如:当众打脸,伪造证据被拆穿,身份暴露边缘)
                                2.悬念钩子(Hook):每一集的结尾必须卡在剧情最高潮或最意想不到的转折处,并且必须与下一集的开场完美衔接
                                3.角色锦囊(Directives):这是指导后续AI演员表演的最高纲领!必须具体可执行,绝不能写空话,内容要具体

                                # Output Format(Strict JSON):
                                严格按照以下JSON格式输出(只能输出JSON格式,不要输出任何额外的解释性文字,也不要输出Markdown):
                                {{"episodes":[{{"episode_number":1,
                                                "global_plot":"(一句话总结本集剧情精髓)",
                                                "place":"(本集的单一主要场景、尽量集中,例如晚宴大厅)",
                                                "core_conflict":"(本集的具体矛盾爆发点)",
                                                "plot_twist_or_hook":"(本集结尾的钩子/悬念)",
                                                "first_speaker":"(本集第一个开口说话的角色名字，必须在角色库中)",
                                                "character_directives":{{"(角色库的角色名A)":"[本集情绪]:... [本集目标]:... [行动策略]:...",
                                                                         "(角色库的角色名B)":"[本集情绪]:... [本集目标]:... [行动策略]:...",
                                                                         "(角色库的角色名C)":"[本集情绪]:... [本集目标]:... [行动策略]:..."}}}}]}}
                                """).strip()
        
        return prompt
    

class Actor_Agent_Prompt():

    def __init__(self,global_config):

        self.global_config=global_config

    # ---------- 生成角色Agent提示词 ----------
    def generate_prompt(self,planner_output,name,episode,history,user_feedback=None,agent_feedback=None,force_speaker=None) -> str :

        # ----- Agent扮演角色的信息 -----
        own_chara=""
        chara=self.global_config["character_roster"][name]
        appearance=",".join(chara["appearance_tags"])
        personality=",".join(chara["personality_tags"])
        own_chara+=f"{name}({chara['role_type']}):\n"
        own_chara+=f"-[基础信息]:{chara['gender']},{chara['age']}岁,{chara['identity']}\n"
        own_chara+=f"-[外貌]:{appearance}\n"
        own_chara+=f"-[性格]:{personality}\n"
        own_chara+=f"-[口头禅]:{chara['catchphrase']}\n"

        # ----- 剧中其他角色的信息 -----
        other_chara=""
        for names,info in self.global_config["character_roster"].items():
            if names!=name:
                other_chara+=f"{names}({info['role_type']}):{info['gender']},{info['identity']}\n"

        # ----- 添加用户指导 -----   
        if user_feedback:
            history+=f"[来自场外用户的指令]:{user_feedback}(请你根据场外用户的指和历史互动信息重新演,你需要将用户的指导作为最高优先级)\n"

        if agent_feedback:
            history+=f"[来自场外总监制Agent的指令]:{agent_feedback}(请你根据总监制Agent的指导和历史互动信息重演)\n"

        if force_speaker:
            current_rule="1.传麦机制:我们已经指定好了下一个互动的角色,本次互动你需要在 next_speaker 字段中强制输出[],即空列表"
            current_format='"next_speaker":[]'
        else:
            current_rule="1.传麦机制:你必须在 next_speaker 字段指定你希望谁对你的行为做出反应,可以是一个人,也可以是多个人"
            current_format='''"next_speaker":["(这是一个列表,包含你互动面对的角色,即你希望对你的行为做出反应的角色,可以是一个或多个元素,例如['角色B'],或['角色B','角色C'],如果想结束本集填['end'])"]'''

        # 使用textwrap消除多余的空格,减少token浪费
        prompt=textwrap.dedent(f"""
                                # Role:
                                你是一个演技精湛的专业短剧演员,你的行动必须完全符合你的人设
                
                                # Theme:
                                这部短剧的整体主题是:{self.global_config["logline"]}

                                # Character:
                                你在剧中扮演的角色是:
                                {own_chara}
                                同时剧中还有其他角色:
                                {other_chara}
                                
                                # Episode:
                                当前你正处于第{episode}集,本集主要信息如下:
                                -[本集主线]:{planner_output["episodes"][episode-1]["global_plot"]}
                                -[主要场景]:{planner_output["episodes"][episode-1]["place"]}
                                -[矛盾爆发点]:{planner_output["episodes"][episode-1]["core_conflict"]}
                                -[本集钩子/悬念]:{planner_output["episodes"][episode-1]["plot_twist_or_hook"]}
                                -[角色本集专属指导]:{planner_output["episodes"][episode-1]["character_directives"].get(name,"根据已有信息灵活发挥")}

                                # Context:
                                你当前感知到的历史互动:
                                {history}
                                
                                # Task & Rules:
                                请根据以上信息,决定你下一步的反应
                                {current_rule}
                                2.杀青申请:如果你认为在你互动后当前的剧情已经完美达到了[本集高潮/悬念],你必须在 next_speaker 字段填写 ['end']
                                3.互动可见:如果你希望其他角色知道你的互动,使用 visible 字段指定这些角色名
                                4.标点要求:Dialogue必须使用标准的中文标点符号。

                                # Output Format(Strict JSON):
                                严格按照以下JSON结构输出(只能输出JSON格式,不要输出任何额外的解释性文字,也不要输出Markdown):
                                {{"(你扮演的角色名称)":{{"Inner_Thought":"(内心的算计或真实想法,必填)",
                                                      "Action":"(具体的肢体动作或神态,或者可填'null')",
                                                      "Dialogue":"(说出口的台词,或者可填'null')",
                                                      {current_format},
                                                      "visible":["(这是一个列表,包含所有能看到/听到你互动的角色,可以是一个或多个元素)"]}}}}
                                """).strip()

        return prompt