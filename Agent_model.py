import json
from openai import OpenAI
import os
from dotenv import load_dotenv
from typing import Union


def load_env():

    load_dotenv()

    base_url=os.getenv("base_url")
    api_key=os.getenv("api_key")
    model=os.getenv("model")

    if (not base_url):
        raise ValueError("找不到 base_url")
    elif (not api_key):
        raise ValueError("找不到 api_key")
    elif (not model):
        raise ValueError("找不到 model")
    
    return base_url,api_key,model
    

class Planner_Agent():

    def __init__(self,base_url,api_key,model):

        self.base_url=base_url
        self.api_key=api_key
        self.model=model
        self.client=OpenAI(base_url=self.base_url,api_key=self.api_key)

    def generate_outline(self,prompt):

        print(f"总策划Agent正在策划分集大纲,使用模型{self.model}")
        
        try:

            response=self.client.chat.completions.create(model=self.model,
                                                         messages=[{"role":"user","content":prompt}],
                                                         response_format={"type":"json_object"},
                                                         temperature=0.0)
            raw_text=response.choices[0].message.content
            
            try:

                raw_json=json.loads(raw_text)

                return raw_json
            
            except Exception as e:

                print(f"总策划Agent调用Api失败:{e}")

                return "format_error"
            
        except Exception as e:

            print(f"总策划Agent调用Api失败:{e}")
            
            return "api_error"
        

class Muilty_Agent_Box():

    def __init__(self,base_url,api_key,model):

        self.base_url=base_url
        self.api_key=api_key
        self.model=model 
        self.client=OpenAI(base_url=self.base_url,api_key=self.api_key)
        self.global_history={}

    def generate_prompt(self,global_config,name,planner_output,episode,temporary_feedback=None):
        
        chara=global_config["character_roster"][name]
        own_chara=""
        appearance="、".join(chara["appearance_tags"])
        personality="、".join(chara["personality_tags"])
        own_chara+=f"{name}（{chara['role_type']}）：\n"
        own_chara+=f"-【基础信息】：{chara['gender']}，{chara['age']}岁，{chara['identity']}\n"
        own_chara+=f"-【外貌】：{appearance}\n"
        own_chara+=f"-【性格】：{personality}\n"
        own_chara+=f"-【口头禅】：{chara['catchphrase']}\n"

        other_chara=""
        for names,info in global_config["character_roster"].items():
            
            if names!=name:
                
                other_chara+=f"{names}（{info['role_type']}）：{info['gender']}，{info['identity']}\n"

        history=""
        if episode in self.global_history.keys():
        
            for his in self.global_history[episode][-6:]:

                history+="\n".join([f"step:{his['step']}",f"role:{his['role']}",f"Inner_Thought:{his['Inner_Thought']}",f"Action:{his['Action']}",f"Dialogue:{his['Dialogue']}"])
                history+="\n\n"
        
        if temporary_feedback:

            history+=f"【来自场外用户的重拍指令】：{temporary_feedback}。请你根据场外用户的指导，接续上面的历史重新演！\n"

        return f"""
                # Role:
                你是一个演技精湛的专业短剧演员，你能综合考虑整部剧的主题、单集主线、角色设定、本集历史角色互动等因素，做出合理的角色反应，即节奏合适、举止合乎设定
                
                # Theme:
                目前你参与的这部短剧的整体主题是 {global_config["logline"]} ，这部短剧共有 {global_config["drama_settings"]["expected_episodes"]} 集

                # Character:
                你在剧中扮演的角色是：
                {own_chara}
                同时剧中还有其他角色：
                {other_chara}
                
                # Episode:
                当前你正处于第 {episode} 集，本集主要信息如下：
                -【本集主线】：{planner_output["episodes"][episode-1]["global_plot"]}，
                -【主要场景】：{planner_output["episodes"][episode-1]["place"]}
                -【矛盾爆发点】：{planner_output["episodes"][episode-1]["core_conflict"]}
                -【本集钩子/悬念】：{planner_output["episodes"][episode-1]["plot_twist_or_hook"]}
                -【角色本集指导】：{planner_output["episodes"][episode-1]["character_directives"].get(name,"根据已有信息灵活发挥")}
                -【历史互动】：{history}
                
                # Task:
                你的任务是根据以上信息，接续互动对话。
                补充：如果你认为当前的剧情已经完美达到了【本集高潮/悬念】，你必须在 next_speaker 字段输出"导演"，这代表你申请本集结束。

                # Output Format (JSON):
                输出格式为严格的JSON格式，结构如下：
                {{"（你扮演的角色的名字）":{{"Inner_Thought":"（具体内心想法）",
                                          "Action":"（具体行为动作）",
                                          "Dialogue":"（具体发言）",
                                          "next_speaker":"（根据剧中其他角色，指定下一个互动对象，如果希望结束本集输出'end'）"}}}}
                """  
    
    def generate_reaction(self,name:str,message:list[dict[str,str]],episode:int) -> str: 

        print(f"角色{name}的Agent正在调用中...")

        if episode not in self.global_history.keys():

            self.global_history[episode]=[]
        
        try:

            response=self.client.chat.completions.create(model=self.model,
                                                         messages=message,
                                                         response_format={"type":"json_object"},
                                                         temperature=0.0)
            raw_text=response.choices[0].message.content

            try:
                
                raw_json=json.loads(raw_text)

                if name in raw_json.keys() and all(k in raw_json[name] for k in ["Inner_Thought","Action","Dialogue","next_speaker"]):

                    reaction={}
                    reaction["step"]=len(self.global_history[episode])+1
                    reaction["role"]=name
                    reaction["Inner_Thought"]=raw_json[name]["Inner_Thought"]   
                    reaction["Action"]=raw_json[name]["Action"]
                    reaction["Dialogue"]=raw_json[name]["Dialogue"]

                    self.global_history[episode].append(reaction)

                    return raw_json[name]["next_speaker"]
                
                elif name not in raw_json.keys():

                    print(f"角色{name}的Agent输出格式不正确,是JSON格式,但是名字错误,应该是{name}")
                    
                    return "name_error"

                else:

                    print(f"角色{name}的Agent输出格式不正确,是JSON格式,但是字段不是Inner_Thought、Action、Dialogue、next_speaker")

                    return "key_error"

            except Exception as e:

                print(f"角色{name}的Agent输出格式不正确,不是JSON格式")

                return "format_error"

        except Exception as e:

            print(f"角色{name}的Agent的Api调用失败:{e}")

            return "api_error"
        
    def roll_back(self,step,episode):

        if episode in self.global_history:
        
            if len(self.global_history[episode])>=step:

                print(f"触发回档，用户选择撤销{step}步")
                
                self.global_history[episode]=self.global_history[episode][:-step]
                
                return "success"

            else:

                print(f"step超过最大历史互动次数")

                return "step_error"    
            
        else:

            return "success"


if __name__=="__main__":

    from global_config import global_config
    from prompt import build_chara,chara_text,planner_agent_prompt

    base_url,api_key,model=load_env()
    planner_agent=Planner_Agent(base_url,api_key,model)
    output=planner_agent.generate_outline(planner_agent_prompt)
    print(type(output))