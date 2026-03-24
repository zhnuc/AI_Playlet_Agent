import json
from openai import OpenAI
import os
from dotenv import load_dotenv
from typing import Union


from prompt import Actor_Agent_Prompt,Director_Agent_Prompt

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

# ---------- 清洗模型输出JSON附带的Markdown ----------
def clean_json_markdown(raw_json_text):

    clean_json_text=raw_json_text.strip()
    if clean_json_text.startswith("```json"):
        clean_json_text=clean_json_text[7:]
    elif clean_json_text.startswith("```"):
        clean_json_text=clean_json_text[3:]
    if clean_json_text.endswith("```"):
        clean_json_text=clean_json_text[:-3]
    return clean_json_text.strip()

class Planner_Agent():

    def __init__(self,base_url,api_key,model,global_config):

        self.base_url=base_url
        self.api_key=api_key
        self.model=model
        self.client=OpenAI(base_url=self.base_url,api_key=self.api_key)
        self.global_config=global_config

    def generate_outline(self,prompt):

        print(f"\n总策划Agent正在策划分集大纲,使用模型{self.model}\n")
        
        try:
            response=self.client.chat.completions.create(model=self.model,
                                                         messages=[{"role":"user","content":prompt}],
                                                         response_format={"type":"json_object"},
                                                         temperature=0.0)
            raw_text=response.choices[0].message.content
            # 清洗Markdown
            raw_text=clean_json_markdown(raw_text)
            
            try:
                raw_json=json.loads(raw_text)
                
                for i in range(len(raw_json["episodes"])):
                    first_name=raw_json["episodes"][i]["first_speaker"]
                    dire_name=raw_json["episodes"][i]["character_directives"].keys()
                    if first_name not in self.global_config["character_roster"].keys():
                        return "name_error"
                    for dire_n in dire_name:
                        if dire_n not in self.global_config["character_roster"].keys():
                            return "name_error"

                return raw_json
            
            # 展示模型错误输出
            except Exception as e:
                print(f"总策划Agent输出格式错误:{e}")
                print(f"[Debug]模型输出:{repr(raw_text)}")
                return "json_error"
            
        except Exception as e:
            print(f"总策划Agent调用Api失败:{e}")
            return "api_error"
        

class Actor_Agent_Box():

    def __init__(self,base_url,api_key,model,global_config):

        self.base_url=base_url
        self.api_key=api_key
        self.model=model 
        self.client=OpenAI(base_url=self.base_url,api_key=self.api_key)
        self.global_config=global_config
        self.global_history={}
        # 引入提示词构建器实例
        self.actor_agent_prompt=Actor_Agent_Prompt(self.global_config)       
    
    # ---------- 创建角色Agent提示词 ----------
    def generate_prompt(self,planner_output,name,episode,user_feedback=None,agent_feedback=None,force_speaker=None,error=None) -> str :

        history=""
        if episode not in self.global_history:
            self.global_history[episode]=[]

        visible_history=[]
        for epi in range(1,episode+1):
            if epi in self.global_history:
                for his in self.global_history[epi]:
                    if name==his["role"]:
                        visible_history.append(his)
                    else:
                        visible_list=his["visible"]
                        if (isinstance(visible_list,list)) and (name in visible_list):
                            visible_history.append(his)

        # 截取部分历史互动,且Inner_Thought进行保密操作
        for vis_his in visible_history[-6:]:        
            history+="\n".join([f"role:{vis_his['role']}",f"Action:{vis_his['Action']}",f"Dialogue:{vis_his['Dialogue']}"])
            history+="\n\n"
        
        # 处理角色面临历史信息为空的状况
        if not history.strip():
            history="(当前无历史互动,你直接开场行动)"
        
        return self.actor_agent_prompt.generate_prompt(planner_output,name,episode,history,user_feedback,agent_feedback,force_speaker,error)

    # ---------- 调用角色Agent输出 ----------
    def generate_reaction(self,name,message:list[dict[str,str]],episode) -> Union[list,str] : 

        print(f"扮演角色{name}的Agent正在调用中...")

        if episode not in self.global_history:
            self.global_history[episode]=[]
        
        try:
            response=self.client.chat.completions.create(model=self.model,
                                                         messages=message,
                                                         response_format={"type":"json_object"},
                                                         temperature=0.0)
            raw_text=response.choices[0].message.content

            try:
                raw_json=json.loads(raw_text)
                
                # ----- 检验name/next_speaker/关键字段 ----- 
                if name in raw_json and all(k in raw_json[name] for k in ["Inner_Thought","Action","Dialogue","next_speaker","visible"]):
                    
                    next_speaker_list=raw_json[name]["next_speaker"]
                    valid_names=list(self.global_config["character_roster"].keys())
                    valid_end=["end","'end'",'"end"',"‘end’",'“end”']

                    if not isinstance(next_speaker_list,list):
                        print("角色Agent的 next_speaker 输出不是 list 格式")
                        print(f"[Debug]:角色Agent错误输出:{repr(raw_json)}")
                        return "next_speaker_format_error"

                    for speaker in next_speaker_list:
                        if (speaker.strip() not in valid_names) and (speaker.strip() not in valid_end):
                            print("角色Agent的 next_speaker 输出内容错误,不在角色库,也不是 end ")
                            print(f"[Debug]:角色Agent错误输出:{repr(raw_json)}")
                            return "next_speaker_name_error"

                    reaction={}
                    reaction["step"]=len(self.global_history[episode])+1
                    reaction["role"]=name
                    reaction["Inner_Thought"]=raw_json[name]["Inner_Thought"]   
                    reaction["Action"]=raw_json[name]["Action"]
                    reaction["Dialogue"]=raw_json[name]["Dialogue"]
                    reaction["next_speaker"]=raw_json[name]["next_speaker"]
                    reaction["visible"]=raw_json[name]["visible"]
                    self.global_history[episode].append(reaction)
                    return raw_json[name]["next_speaker"]
                
                elif name not in raw_json.keys():
                    print(f"角色Agent输出自身角色名错误,不是{name}")
                    print(f"[Debug]:角色Agent错误输出:{repr(raw_json)}")
                    return "name_error"
                
                elif not(all(k in raw_json[name] for k in ["Inner_Thought","Action","Dialogue","next_speaker","visible"])):
                    print(f"角色Agent输出关键字段错误,不是 Inner_Thought / Action / Dialogue / next_speaker / visible ")
                    print(f"[Debug]:角色Agent错误输出:{repr(raw_json)}")
                    return "key_error"

            except Exception as e:
                print(f"角色Agent的输出不是 JSON 格式")
                print(f"[Debug]:角色Agent错误输出:{repr(raw_text)}")
                return "json_error"

        except Exception as e:
            print(f"扮演角色{name}的Agent的Api调用失败:{e}")
            return "api_error"
        
    # ---------- 用户回档功能 ----------       
    def roll_back(self,episode,step) -> str :

        if episode in self.global_history:
            if step in range(1,len(self.global_history[episode])+1):
                temp={}
                for epi in range(1,episode+1):
                    if epi!=episode:
                        temp[epi]=self.global_history[epi]
                    else:
                        temp[epi]=self.global_history[episode][:step]
                self.global_history=temp
                return "success"
            else:
                return "step_error"    
        else:
            return "episode_error"
        

class Director_Agent_Box():

    def __init__(self,base_url,api_key,model,global_config):

        self.base_url=base_url
        self.api_key=api_key
        self.model=model
        self.client=OpenAI(base_url=self.base_url,api_key=self.api_key)
        self.director_agent_prompt=Director_Agent_Prompt(global_config)

    def generate_direction(self,prompt,pattern):

        print(f"\n{pattern}:总监制正在审查与指导中,使用模型{self.model}\n")

        try:
            response=self.client.chat.completions.create(model=self.model,
                                                         messages=[{"role":"user","content":prompt}],
                                                         response_format={"type":"json_object"},
                                                         temperature=0.0)

            raw_text=response.choices[0].message.content
            # 清洗Markdown
            raw_text=clean_json_markdown(raw_text)
            
            try:
                raw_json=json.loads(raw_text)
                return raw_json
            
            # 展示模型错误输出
            except Exception as e:
                print(f"总监制Agent输出格式错误:{e}")
                print(f"[Debug]模型输出:{repr(raw_text)}")
                return "format_error"
                
        except Exception as e:
            print(f"总监制Agent调用Api失败:{e}")
            return "api_error" 
    
    # 模式1:前中期巡视 
    def patrol(self,planner_output,episode,history,name,name_list):
        
        prompt = self.director_agent_prompt.generate_patrol_prompt(planner_output,episode,history,name,name_list)
        return self.generate_direction(prompt,pattern="[总监制-前中期巡视模式]")
    
    # ---------- 模式2:中后期强制收网 ----------
    def converge(self, planner_output, episode, history, name, name_list, next_first_speaker):

        prompt = self.director_agent_prompt.generate_convergence_prompt(planner_output,episode,history,name,name_list,next_first_speaker)
        return self.generate_direction(prompt,pattern="[总监制-中后期收网模式]")
    
    # ---------- 模式3:杀青审核模式 ----------
    def audit_end(self, planner_output, episode, history, next_first_speaker):
        
        prompt=self.director_agent_prompt.generate_audit_prompt(planner_output,episode,history,next_first_speaker)
        return self.generate_direction(prompt,pattern="[总监制-杀青审核模式]")