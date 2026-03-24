import json
import os


from global_config import global_config
from prompt import Planner_Agent_Prompt
from agent_model import load_env,Planner_Agent,Actor_Agent_Box,Director_Agent_Box


def run():

    print("\n========== AI短剧系统启动 ==========\n")

    # ---------- 载入基本配置 ----------
    base_url,api_key,model=load_env()
    planner_prompt_factory=Planner_Agent_Prompt(global_config)
    planner_agent=Planner_Agent(base_url,api_key,model,global_config)
    actor_agent_box=Actor_Agent_Box(base_url,api_key,model,global_config)
    director_agent_box=Director_Agent_Box(base_url,api_key,model,global_config)

    # ========== 调用总策划Agent ==========
    # 错误统计变量
    error_step=0
    max_planner_error=3

    while (error_step<max_planner_error):
        prompt=planner_prompt_factory.generate_prompt(error=planner_output if error_step>0 else None)
        planner_output=planner_agent.generate_outline(prompt)

        # ----- 处理总策划Agent错误输出 -----
        if planner_output in ["json_error","api_error","name_error"]:
            error_step+=1
            if error_step==max_planner_error:
                print(f"\n总策划Agent输出错误{max_planner_error}次,强制退出系统\n")
                error_step=0
                planner_output=None
                return 
            else:
                print(f"\n总策划Agent输出错误,将进行第{error_step+1}次生成\n")
        else:
                error_step=0
                break

    print("\n========== 剧本大纲生成完成 ===========\n")
    print(json.dumps(planner_output,indent=2,ensure_ascii=False))
        
    while(True):
        user_input=input("\n剧本大纲已生成,你是否满意?\n(输入 yes 表示满意并进入下一阶段;或输入 no 将为您开启提意见功能)")
        
        # ----- 将用户满意的大纲保存 -----
        if user_input.strip().lower()=="yes":
            dirname=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            path=os.path.join(dirname,"AGENT_OUTPUT")
            os.makedirs(path,exist_ok=True)
            file=os.path.join(path,"planner_agent_output.json")
            with open(file,"w",encoding="utf-8") as f:
                json.dump(planner_output,f,indent=2,ensure_ascii=False)
            print(f"\n剧本大纲已确定,且大纲文件保存至{path}\n")
            print("\n下面角色Agent将开始演绎剧情\n")
            break

        # ----- 用户意见反馈 -----
        elif user_input.strip().lower()=="no":
            feedback=input("\n请提出您关于大纲的意见,这将作为总策划生成大纲的指导\n")
            print("\n总策划Agent将根据您的意见修改大纲\n")

            while(error_step<max_planner_error):
                prompt=planner_prompt_factory.generate_prompt(feedback,error=planner_output if error_step>0 else None)
                planner_output=planner_agent.generate_outline(prompt)

                # ----- 处理总策划Agent错误输出 -----
                if planner_output in ["json_error","api_error","name_error"]:
                    error_step+=1
                    if error_step==max_planner_error:
                        print(f"\n总策划Agent输出错误{max_planner_error}次,强制退出系统\n")
                        error_step=0
                        planner_output=None
                        return 
                    else:
                        print(f"\n总策划Agent输出错误,将进行第{error_step+1}次生成\n")
                else:
                        error_step=0
                        break
            
            print("\n========== 剧本大纲生成完成 ===========\n")
            print(json.dumps(planner_output,indent=2,ensure_ascii=False))
        
        # ----- 处理用户错误输入 -----
        else:
            print("\n输入错误:您的输入不是 yes 或者 no ,请重新输入\n")

    # ========== 每集剧情演绎(角色Agent+总监制Agent) ==========
    # 集数与片段
    episode_num=len(planner_output["episodes"])
    max_step=16
    episode=1
    step=1

    # 反馈变量
    user_feedback=None
    agent_feedback=None

    # 角色队列变量
    force_speaker=None
    recall_name=None
    name_list=[]

    # 错误统计变量
    error_step=0
    max_actor_error=3
    max_director_error=3

    while(episode<=episode_num):

        while(step<=max_step):

            if (step==1):
                name=planner_output["episodes"][episode-1]["first_speaker"]

            # ---------- 为总监制Agent提供上帝视角 ----------
            full_history=""
            if episode in actor_agent_box.global_history:
                for his in actor_agent_box.global_history[episode]:
                    full_history+=f"role:{his['role']}\nInner_Thought:{his['Inner_Thought']}\nAction:{his['Action']}\nDialogue:{his['Dialogue']}\n\n"
            if not full_history.strip():
                full_history="当前无历史互动,本集刚开场"
                
            next_first = None
            if episode < episode_num:
                next_first = planner_output["episodes"][episode]["first_speaker"]
            
            if step > 1:

                # ---------- 模式2:总监制Agent强制收尾 ----------
                if (max_step-step<= 2):
                    error_step=0
                    while(error_step<max_director_error):
                        director_output=director_agent_box.converge(planner_output,episode,full_history,name,name_list,next_first,error=director_output if error_step>0 else None)
                        if director_output in ["key_error","action_type_error","target_role_error","json_error","api_error"]:
                            error_step+=1
                            if error_step==max_director_error:
                                print(f"\n总监制Agent输出错误{max_director_error}次,强制退出系统\n")
                                error_step=0
                                director_output=None
                                return 
                            else:
                                print(f"\n总监制Agent输出错误,将进行第{error_step+1}次生成\n")
                        else:
                            error_step=0
                            break

                    if director_output["Action_Type"].strip() in ["Current","'Current'",'"Current"']:
                        agent_feedback=director_output["Directive"]

                    elif director_output["Action_Type"].strip() in ["Override","'Override'",'"Override"']:
                        name=director_output["Target_Role"].strip()
                        name_list=[]
                        force_speaker=None
                        agent_feedback=director_output["Directive"]

                # ---------- 模式1:总监制Agent前中期巡视 ----------
                elif step in [5,9]:
                    error_step=0
                    while(error_step<max_director_error):
                        director_output=director_agent_box.patrol(planner_output,episode,full_history,name,name_list,error=director_output if error_step>0 else None)
                        if director_output in ["key_error","action_type_error","target_role_error","json_error","api_error"]:
                            error_step+=1
                            if error_step==max_director_error:
                                print(f"\n总监制Agent输出错误{max_director_error}次,强制退出系统\n")
                                error_step=0
                                director_output=None
                                return 
                            else:
                                print(f"\n总监制Agent输出错误,将进行第{error_step+1}次生成\n")
                        else:
                            error_step=0
                            break

                    if director_output["Action_Type"].strip() in ["Pass","'Pass'",'"Pass"']:
                        pass

                    elif director_output["Action_Type"].strip() in ["Current","'Current'",'"Current"']:
                        agent_feedback=director_output["Directive"]

                    elif director_output["Action_Type"].strip() in ["Override","'Override'",'"Override"']:
                        name=director_output["Target_Role"].strip()
                        name_list=[]
                        force_speaker=None
                        agent_feedback=director_output["Directive"]

            # ---------- 角色Agent开始演绎互动 ----------
            error_step=0
            while(error_step<max_actor_error):
                prompt=actor_agent_box.generate_prompt(planner_output,name,episode,user_feedback,agent_feedback,force_speaker,error=actor_output if error_step>0 else None) 
                actor_output=actor_agent_box.generate_reaction(name,[{"role":"user","content":prompt}],episode)

                # ----- 处理角色Agent错误输出 -----
                if actor_output in ["next_speaker_format_error","next_speaker_name_error","name_error","key_error","json_error","api_error"]:
                    error_step+=1
                    if error_step==max_actor_error:
                        print(f"\n角色Agent已输出错误{max_actor_error}次,强制退出系统\n")
                        error_step=0
                        actor_output=None
                        return 
                    else:
                        print(f"\n角色Agent输出错误,将进行第{error_step+1}次生成\n")
                else:
                    error_step=0
                    break
            
            role=actor_agent_box.global_history[episode][-1]["role"]
            Inner_Thought=actor_agent_box.global_history[episode][-1]["Inner_Thought"]
            Action=actor_agent_box.global_history[episode][-1]["Action"]
            Dialogue=actor_agent_box.global_history[episode][-1]["Dialogue"]

            # ----- 及时处理场外指导(场外指导仅持续一次) -----
            if user_feedback!=None:
                user_feedback=None
            if agent_feedback!=None:
                agent_feedback=None

            if force_speaker==None:
                if isinstance(actor_output,list):
                    if len(actor_output)==1:
                        # ---------- 处理杀青申请 ----------
                        if actor_output[0].strip() in ["end","'end'",'"end"']:

                            # ----- 更新full_history ----- 
                            current_step_text=f"role:{role}\nInner_Thought:{Inner_Thought}\nAction:{Action}\nDialogue:{Dialogue}\n\n"
                            audit_history=full_history+current_step_text

                            # ----- 模式3:总监制Agent杀青审核 -----
                            error_step=0
                            while(error_step<max_director_error):
                                director_output=director_agent_box.audit_end(planner_output,episode,audit_history,next_first,error=director_output if error_step>0 else None)
                                if director_output in ["key_error","approved_error","target_role_error","json_error","api_error"]:
                                    error_step+=1
                                    if error_step==max_director_error:
                                        print(f"\n总监制Agent输出错误{max_director_error}次,强制退出系统\n")
                                        error_step=0
                                        director_output=None
                                        return 
                                    else:
                                        print(f"\n总监制Agent输出错误,将进行第{error_step+1}次生成\n")
                                else:
                                    error_step=0
                                    break

                            # ----- 杀青审核通过 -----
                            if str(director_output["Approved"]).strip() in ["true","'true'",'"true"']:
                                print(f"\n第{step}步:\n姓名:{role}\n内心想法:{Inner_Thought}\n动作:{Action}\n对话:{Dialogue}\n")
                                print(f"\n[总监制]:审核通过,本集完美杀青!")
                                break      

                            # ----- 杀青审核拒绝 -----
                            elif str(director_output["Approved"]).strip() in ["false","'false'",'"false"']:
                                print(f"\n[总监制]:审核驳回,将继续演绎剧情!\n")
                                reject_info=director_output["Rejected_Feedback"]
                                # ----- 如果导演指定了人去补救,就切镜头;否则让刚才说话的人继续找补 -----
                                name=reject_info["Target_Role"]
                                name_list=[]
                                force_speaker=None
                                agent_feedback=reject_info["Directive"]

                        else:
                            name=actor_output[0]
        
                    elif len(actor_output)>1:
                        recall_name=name
                        name_list=actor_output
                        name=name_list[0]
                        name_list=name_list[1:]
                        force_speaker=True

            else:
                if len(name_list)>=1:
                    name=name_list[0]
                    name_list=name_list[1:]
                    force_speaker=True
                    
                elif len(name_list)==0:
                    force_speaker=None
                    name=recall_name

            print(f"\n第{step}步:\n姓名:{role}\n内心想法:{Inner_Thought}\n动作:{Action}\n对话:{Dialogue}\n")
            
            step+=1
            
            # ========== 处理用户反馈 ===========
            while(True):
                user_input=input("\n你是否满意以上角色互动?\n(输入 yes 表示满意并继续角色Agent互动,或者输入 no 将为您提供回档功能与意见功能)")
                
                if user_input.strip().lower()=="yes":
                    break
                
                elif user_input.strip().lower()=="no":
                    print("\n下面请你依次输入回档到的集数、回档到的步数、指导意见\n")

                    user_episode=int(input("\n请输入回档到的集数(只输入数字,例如你想回档到第三集就输入3)\n").strip())
                    user_step=int(input("\n请输入回档到的步数(只输入数字,例如你想回档到某集第5步就输入5)\n").strip())
                    roll_back_output=actor_agent_box.roll_back(user_episode,user_step)

                    if roll_back_output=="success":
                        print(f"\n回档成功,回档到第{user_episode}集的第{user_step}步\n")
                        user_feedback=input(f"\n请输入你对第{user_episode}集第{user_step}步之后的互动的建议(您的建议仅能指导下一次互动,且不能随意指定互动的角色)\n")
                        step=user_step+1
                        episode=user_episode

                        # ----- 处理回档后name/name_list/force_speaker -----
                        if user_step==0:
                            name=planner_output["episodes"][episode-1]["first_speaker"]
                            force_speaker=None
                            name_list=[]

                        else:
                            next_speaker=actor_agent_box.global_history[episode][-1]["next_speaker"]
                            if isinstance(next_speaker,list):
                                if len(next_speaker)==0:
                                    cur_name=actor_agent_box.global_history[episode][-1]["role"]
                                    for epi in range(len(actor_agent_box.global_history[episode])):
                                        if isinstance(actor_agent_box.global_history[episode][epi]["next_speaker"],list) and \
                                            len(actor_agent_box.global_history[episode][epi]["next_speaker"])>1:
                                            cur_list=actor_agent_box.global_history[episode][epi]["next_speaker"]
                                            cur_recall=actor_agent_box.global_history[episode][epi]["role"]

                                    for j in range(len(cur_list)):
                                        if cur_list[j]==cur_name:
                                            if len(cur_list[j+1:])==0:
                                                name=cur_recall
                                                name_list=[]
                                                force_speaker=None
                                                
                                            elif len(cur_list[j+1:])>=1:
                                                name=cur_list[j+1]
                                                name_list=cur_list[j+2:]
                                                recall_name=cur_recall
                                                force_speaker=True

                                elif len(next_speaker)==1:
                                    name=next_speaker[0]
                                    force_speaker=None
                                    name_list=[]

                                elif len(next_speaker)>1:
                                    recall_name=actor_agent_box.global_history[episode][-1]["role"]
                                    name=next_speaker[0]
                                    name_list=next_speaker[1:]
                                    force_speaker=True

                        break

                    elif roll_back_output=="step_error":
                        print(f"\n回档失败:第{user_episode}集中不存在第{user_step}步\n")

                    else:
                        print(f"\n回档失败:第{user_episode}集不存在\n")


        # ----- 保存每一集互动文件 -----
        dirname=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path=os.path.join(dirname,"AGENT_OUTPUT")
        os.makedirs(path,exist_ok=True)
        file=os.path.join(path,f"actor_agent_output{episode}.json")
        with open(file,"w",encoding="utf-8") as f:
            json.dump(actor_agent_box.global_history,f,indent=4,ensure_ascii=False)

        step=1
        episode+=1  
        user_feedback=None
        agent_feedback=None
        force_speaker=None
        name_list=[]
        recall_name=None


if __name__=="__main__":

    run()