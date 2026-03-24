class Planner_Agent_Error():

    def __init__(self):
        
        pass

    def generate_error_prompt(self,error,valid_names):

        self.error=error
        error_prompt=""

        if self.error=="name_error":
            
            error_prompt+="# Warning:\n"
            error_prompt+=f"⚠️:你的 first_speaker 仅能从 {valid_names} 中选择!\n"
            error_prompt+=f"⚠️:你的 character_directives 必须且仅能包含 {valid_names} 中每一个人!\n"
            error_prompt+=f"⚠️:不要输出不在 {valid_names} 中的NPC(如路人、客人、旁观者、警察等)!\n"

        elif self.error=="json_error":
            error_prompt+="# Warning:\n"
            error_prompt+=f"⚠️:你最终的输出必须是严格的 JSON 格式,你要注意输出格式闭合性等问题(确保字段和字符串的引号是成对出现,不要缺少冒号/引号/逗号,且应该是英文版符号)!\n"

        elif self.error=="api_error":
            pass

        else:
            pass

        return error_prompt
    


class Actor_Agent_Error():

    def __init__(self):

        pass

    def generate_error_prompt(self,error,valid_names):

        self.error=error
        error_prompt=""

        if self.error=="next_speaker_format_error":
            error_prompt+="# Warning:\n"
            error_prompt+=f"⚠️:你的 next_speaker 输出格式必须是一个列表!"

        elif self.error=="next_speaker_name_error":
            error_prompt+="# Warning:\n"
            error_prompt+=f"⚠️:若你决定继续本集角色互动,你的 next_speaker 字段对应的列表只能包含{valid_names}中的角色名(不要输出不在其中的NPC,如路人、客人、旁观者、警察等)!\n"
            error_prompt+=f"⚠️:若你申请结束本集(杀青),你的 next_speaker 字段必须输出 ['end'] !"

        elif self.error=="name_error":
            error_prompt+="# Warning:\n"
            error_prompt+=f"⚠️:请注意当前扮演的角色名,不要在生成的 JSON 中填错了!\n"

        elif self.error=="key_error":
            error_prompt+="# Warning:\n"
            error_prompt+=f"⚠️:你输出的 JSON 必须且仅能包含 {['Inner_Thought','Action','Dialogue','next_speaker','visible']} 中每一个字段!\n"

        elif self.error=="json_error":
            error_prompt+="# Warning:\n"
            error_prompt+=f"⚠️:你最终的输出必须是严格的 JSON 格式,你要注意输出格式闭合性等问题(确保字段和字符串的引号是成对出现,不要缺少冒号/引号/逗号,且应该是英文版符号)!"

        elif self.error=="api_error":
            pass

        else:
            pass

        return error_prompt
    

class Director_Agent_Error():

    def __init__(self):
        
        pass

    def generate_error_prompt(self,pattern,error,valid_names):
        
        self.pattern=pattern
        self.error=error
        error_prompt=""

        if self.pattern=="[总监制-前中期巡视模式]":

            if self.error=="key_error":
                error_prompt+="# Warning:\n"
                error_prompt+=f"⚠️:你输出的 JSON 必须且仅能包含 {['Analysis','Action_Type','Target_Role','Directive']} 中每一个字段!\n"
            
            elif self.error=="action_type_error":
                error_prompt+="# Warning:\n"
                error_prompt+=f"⚠️:你的 Action_Type 字段必须且仅能从 {['Pass','Current','Override']} 中选择一个!\n"

            elif self.error=="target_role_error":
                error_prompt+="# Warning:\n"
                error_prompt+=f"⚠️:你的 Target_Role 字段必须且仅能从 {valid_names} 中选择一个!\n"

            elif self.error=="json_error":
                error_prompt+="# Warning:\n"
                error_prompt+=f"⚠️:你最终的输出必须是严格的 JSON 格式,你要注意输出格式闭合性等问题(确保字段和字符串的引号是成对出现,不要缺少冒号/引号/逗号,且应该是英文版符号)!"
            
            elif self.error=="api_error":
                pass

            else:
                pass

            return error_prompt
    
        elif self.pattern=="[总监制-中后期收网模式]":
            
            if self.error=="key_error":
                error_prompt+="# Warning:\n"
                error_prompt+=f"⚠️:你输出的 JSON 必须且仅能包含 {['Analysis','Action_Type','Target_Role','Directive']} 中每一个字段!\n"
            
            elif self.error=="action_type_error":
                error_prompt+="# Warning:\n"
                error_prompt+=f"⚠️:你的 Action_Type 字段必须且仅能从 {['Current','Override']} 中选择一个!\n"

            elif self.error=="target_role_error":
                error_prompt+="# Warning:\n"
                error_prompt+=f"⚠️:你的 Target_Role 字段必须且仅能从 {valid_names} 中选择一个!\n"

            elif self.error=="json_error":
                error_prompt+="# Warning:\n"
                error_prompt+=f"⚠️:你最终的输出必须是严格的 JSON 格式,你要注意输出格式闭合性等问题(确保字段和字符串的引号是成对出现,不要缺少冒号/引号/逗号,且应该是英文版符号)!"
            
            elif self.error=="api_error":
                pass

            else:
                pass

            return error_prompt

        elif self.pattern=="[总监制-杀青审核模式]":
                    
            if self.error=="key_error":
                error_prompt+="# Warning:\n"
                error_prompt+=f"⚠️:你输出的 JSON 必须且仅能包含 {['Analysis','Approved','Rejected_Feedback']} 中每一个字段!\n"
            
            elif self.error=="approved_error":
                error_prompt+="# Warning:\n"
                error_prompt+=f"⚠️:你的 Approved 字段必须且仅能从 {['true','false']} 中选择一个!\n"

            elif self.error=="target_role_error":
                error_prompt+="# Warning:\n"
                error_prompt+=f"⚠️:如果 Approved 为 true ,你的 Target_Role 字段必须且仅能从 {valid_names} 中选择一个!\n"

            elif self.error=="json_error":
                error_prompt+="# Warning:\n"
                error_prompt+=f"⚠️:你最终的输出必须是严格的 JSON 格式,你要注意输出格式闭合性等问题(确保字段和字符串的引号是成对出现,不要缺少冒号/引号/逗号,且应该是英文版符号)!"
            
            elif self.error=="api_error":
                pass

            else:
                pass

            return error_prompt