# AI_Playlet_Agent 架构升级实施计划

## 概述

基于七牛云多Agent协作架构和TechCamp Mini Claude Code的最佳实践，本文档提供了AI_Playlet_Agent系统架构升级的具体实施方案。

---

## Phase 1: 架构重构 (2-3周)

### 1.1 职责分离架构设计

#### 目标
将当前单一角色Agent拆分为三个专门化Agent，实现职责分离。

#### 具体实施

**步骤1: 创建规划层Agent**
```python
# 新文件: plot_planner.py
class PlotPlannerAgent:
    """剧情规划Agent - 使用强推理模型"""
    
    def __init__(self):
        self.model = "deepseek-r1"  # 强推理能力
        self.instructions = """
        你是剧情总策划，负责：
        1. 分析当前剧情状态
        2. 规划下一步剧情走向
        3. 分配角色任务
        4. 确保剧情连贯性
        """
    
    def plan_scene_development(self, runtime_state: RuntimeState) -> PlotPlan:
        """规划场景发展"""
        pass
    
    def assign_character_goals(self, plot_plan: PlotPlan) -> Dict[str, str]:
        """分配角色目标"""
        pass
```

**步骤2: 重构执行层Agent**
```python
# 修改: Agent_model.py
class RoleExecutorAgent:
    """角色执行Agent - 使用工具调用模型"""
    
    def __init__(self):
        self.model = "deepseek-v3-tool"  # 支持工具调用
        self.instructions = """
        你是角色扮演者，负责：
        1. 根据规划执行具体角色行为
        2. 生成符合人设的对话
        3. 调用相关工具推进剧情
        """
    
    def execute_role_action(self, role: str, context: RoleContext) -> RoleAction:
        """执行角色动作"""
        pass
```

**步骤3: 创建反思层Agent**
```python
# 新文件: story_reflector.py
class StoryReflectorAgent:
    """剧情反思Agent - 错误检测与重试"""
    
    def __init__(self):
        self.model = "deepseek-r1"
        self.instructions = """
        你是剧情质量检查员，负责：
        1. 检测剧情逻辑问题
        2. 验证角色行为一致性
        3. 决定是否需要重试
        4. 分析错误原因
        """
    
    def validate_story_coherence(self, runtime_state: RuntimeState) -> ValidationResult:
        """验证剧情连贯性"""
        pass
    
    def suggest_improvements(self, validation_result: ValidationResult) -> List[str]:
        """提供改进建议"""
        pass
```

#### 实施时间表
- **Week 1**: 创建新Agent类，完成基础框架
- **Week 2**: 实现核心逻辑，集成到现有系统
- **Week 3**: 测试调试，优化性能

### 1.2 统一接口设计

#### 目标
建立Agent间标准化通信协议。

#### 具体实施
```python
# 新文件: agent_protocol.py
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class AgentMessage:
    """Agent间通信消息格式"""
    sender: str
    receiver: str
    message_type: str  # "plan", "execute", "reflect"
    content: Dict
    timestamp: str

@dataclass
class PlotPlan:
    """剧情规划结果"""
    scene_id: str
    main_conflict: str
    character_goals: Dict[str, str]
    expected_outcome: str
    next_steps: List[str]

@dataclass
class RoleAction:
    """角色执行结果"""
    character: str
    inner_thought: str
    action: str
    dialogue: str
    next_character: Optional[str]
    tools_used: List[str]

@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    issues: List[str]
    suggestions: List[str]
    retry_count: int
```

---

## Phase 2: 工具优化 (1-2周)

### 2.1 精简工具集

#### 目标
将复杂工具集精简为4-6个核心工具。

#### 具体实施

**步骤1: 分析现有工具**
```bash
# 分析当前工具使用频率
grep -r "def.*(" . --include="*.py" | grep "tool" | wc -l
```

**步骤2: 定义核心工具集**
```python
# 新文件: core_tools.py
class CoreStoryTools:
    """核心剧情工具集"""
    
    @staticmethod
    def read_context(context_id: str) -> Dict:
        """读取剧情上下文"""
        pass
    
    @staticmethod
    def advance_plot(plot_point: str, characters: List[str]) -> PlotUpdate:
        """推进剧情发展"""
        pass
    
    @staticmethod
    def character_action(character: str, action: str) -> ActionResult:
        """执行角色动作"""
        pass
    
    @staticmethod
    def generate_dialogue(character: str, context: str) -> DialogueResult:
        """生成角色对话"""
        pass
    
    @staticmethod
    def check_consistency(state: RuntimeState) -> ConsistencyCheck:
        """检查一致性"""
        pass
```

**步骤3: 工具映射表**
```python
# 工具映射关系
TOOL_MAPPING = {
    "context_builder.read_role_context": "read_context",
    "event_committer.commit_turn_result": "advance_plot", 
    "director.should_end_episode": "check_consistency",
    "scheduler.resolve_next_speaker": "character_action"
}
```

### 2.2 标准化输出格式

#### 目标
统一所有Agent的ReAct输出格式。

#### 具体实施
```python
# 新文件: output_formatter.py
class StandardOutputFormatter:
    """标准化输出格式化器"""
    
    @staticmethod
    def format_planner_output(thought: str, plan: PlotPlan) -> str:
        """格式化规划Agent输出"""
        return f"""
<thought>{thought}</thought>
<action tool="create_plan">
{json.dumps(plan.__dict__, ensure_ascii=False)}
</action>
<final>剧情规划完成</final>
"""
    
    @staticmethod
    def format_executor_output(thought: str, action: RoleAction) -> str:
        """格式化执行Agent输出"""
        return f"""
<thought>{thought}</thought>
<action tool="character_action">
{json.dumps(action.__dict__, ensure_ascii=False)}
</action>
<final>角色执行完成</final>
"""
    
    @staticmethod
    def format_reflector_output(thought: str, validation: ValidationResult) -> str:
        """格式化反思Agent输出"""
        if validation.is_valid:
            return f"<final>剧情验证通过</final>"
        else:
            return f"""
<thought>{thought}</thought>
<action tool="retry_plan">
{json.dumps(validation.__dict__, ensure_ascii=False)}
</action>
<final>需要重试</final>
"""
```

### 2.3 增强错误处理

#### 目标
完善异常检测和恢复机制。

#### 具体实施
```python
# 新文件: error_handler.py
class StoryErrorHandler:
    """剧情错误处理器"""
    
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.retry_count = 0
    
    def handle_error(self, error: Exception, context: Dict) -> ErrorAction:
        """处理错误"""
        if self.retry_count >= self.max_retries:
            return ErrorAction.ABORT
        
        if isinstance(error, CharacterInconsistencyError):
            return ErrorAction.REFLECT_AND_RETRY
        
        if isinstance(error, PlotLogicError):
            return ErrorAction.REPLAN_SCENE
        
        return ErrorAction.GENERIC_RETRY
    
    def log_error(self, error: Exception, context: Dict):
        """记录错误日志"""
        pass
```

---

## Phase 3: 能力提升 (2-3周)

### 3.1 模型能力匹配

#### 目标
根据任务特点选择最适合的模型。

#### 具体实施

**步骤1: 模型能力评估**
```python
# 新文件: model_selector.py
class ModelSelector:
    """模型选择器"""
    
    MODEL_CAPABILITIES = {
        "deepseek-r1": {
            "strengths": ["reasoning", "planning", "analysis"],
            "weaknesses": ["function_calling"],
            "cost": "medium"
        },
        "deepseek-v3-tool": {
            "strengths": ["function_calling", "structured_output"],
            "weaknesses": ["complex_reasoning"],
            "cost": "low"
        },
        "claude-3.5-sonnet": {
            "strengths": ["creative_writing", "dialogue"],
            "weaknesses": ["cost"],
            "cost": "high"
        }
    }
    
    def select_model(self, task_type: str) -> str:
        """根据任务类型选择模型"""
        task_requirements = {
            "plot_planning": ["reasoning", "planning"],
            "character_execution": ["function_calling", "creative_writing"],
            "dialogue_generation": ["creative_writing"],
            "consistency_check": ["reasoning", "analysis"]
        }
        
        required_capabilities = task_requirements.get(task_type, [])
        
        for model, capabilities in self.MODEL_CAPABILITIES.items():
            if all(cap in capabilities["strengths"] for cap in required_capabilities):
                return model
        
        return "deepseek-r1"  # 默认选择
```

**步骤2: 动态模型切换**
```python
# 修改: main_loop.py
def execute_task(task_type: str, input_data: Dict) -> Dict:
    """执行任务，自动选择模型"""
    model_name = model_selector.select_model(task_type)
    agent = get_agent_for_model(model_name)
    
    return agent.execute(input_data)
```

### 3.2 上下文管理优化

#### 目标
优化长对话的上下文压缩和管理。

#### 具体实施
```python
# 新文件: context_manager.py
class ContextManager:
    """上下文管理器"""
    
    def __init__(self, max_tokens: int = 8000):
        self.max_tokens = max_tokens
        self.compression_threshold = 0.8
    
    def should_compress(self, messages: List[Dict]) -> bool:
        """判断是否需要压缩上下文"""
        total_tokens = sum(len(msg.get("content", "")) for msg in messages)
        return total_tokens > self.max_tokens * self.compression_threshold
    
    def compress_context(self, messages: List[Dict]) -> List[Dict]:
        """压缩上下文"""
        # 保留最近10轮对话
        recent_messages = messages[-10:]
        
        # 压缩更早的对话为摘要
        early_messages = messages[:-10]
        if early_messages:
            summary = self.summarize_messages(early_messages)
            summary_message = {
                "role": "system",
                "content": f"早期对话摘要: {summary}"
            }
            return [summary_message] + recent_messages
        
        return recent_messages
    
    def summarize_messages(self, messages: List[Dict]) -> str:
        """摘要消息"""
        # 调用摘要模型
        pass
```

### 3.3 性能监控

#### 目标
增加系统运行指标监控。

#### 具体实施
```python
# 新文件: performance_monitor.py
class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics = {
            "agent_calls": defaultdict(int),
            "response_times": defaultdict(list),
            "error_rates": defaultdict(float),
            "token_usage": defaultdict(int)
        }
    
    def track_agent_call(self, agent_name: str, response_time: float, 
                        token_count: int, success: bool):
        """跟踪Agent调用"""
        self.metrics["agent_calls"][agent_name] += 1
        self.metrics["response_times"][agent_name].append(response_time)
        self.metrics["token_usage"][agent_name] += token_count
        
        if not success:
            self.metrics["error_rates"][agent_name] += 1
    
    def generate_report(self) -> Dict:
        """生成性能报告"""
        report = {}
        for agent_name in self.metrics["agent_calls"]:
            calls = self.metrics["agent_calls"][agent_name]
            avg_time = sum(self.metrics["response_times"][agent_name]) / calls
            error_rate = self.metrics["error_rates"][agent_name] / calls
            total_tokens = self.metrics["token_usage"][agent_name]
            
            report[agent_name] = {
                "total_calls": calls,
                "avg_response_time": avg_time,
                "error_rate": error_rate,
                "total_tokens": total_tokens
            }
        
        return report
```

---

## 实施时间表

### 总体时间安排 (6-8周)

| 阶段 | 时间 | 主要任务 | 交付物 |
|------|------|----------|--------|
| Phase 1 | Week 1-3 | 架构重构 | 新Agent类、统一接口 |
| Phase 2 | Week 4-5 | 工具优化 | 精简工具集、标准化格式 |
| Phase 3 | Week 6-8 | 能力提升 | 模型匹配、性能监控 |

### 里程碑检查点

**Week 1 结束**: 
- [ ] PlotPlannerAgent 基础框架完成
- [ ] AgentMessage 协议定义完成

**Week 3 结束**:
- [ ] 三个新Agent全部实现
- [ ] 基础集成测试通过

**Week 5 结束**:
- [ ] 工具集精简完成
- [ ] 错误处理机制上线

**Week 8 结束**:
- [ ] 性能监控系统运行
- [ ] 完整系统测试通过

---

## 风险评估与应对

### 主要风险

1. **兼容性风险**: 新架构可能与现有代码不兼容
   - **应对**: 保持向后兼容，逐步迁移

2. **性能风险**: 多Agent协作可能影响性能
   - **应对**: 实施性能监控，及时优化

3. **复杂性风险**: 系统复杂度增加
   - **应对**: 完善文档，加强测试

### 回滚计划

如果新架构出现问题，可以：
1. 切换回原分支 `dev-wzw`
2. 保留新代码在独立分支
3. 问题解决后再重新集成

---

## 成功指标

### 技术指标
- **响应时间**: 平均响应时间 < 2秒
- **错误率**: 系统错误率 < 5%
- **成功率**: 剧情生成成功率 > 90%

### 业务指标
- **剧情质量**: 角色一致性评分 > 8/10
- **用户体验**: 用户满意度 > 85%
- **系统稳定性**: 7x24小时稳定运行

---

## 总结

本实施计划通过三个阶段的系统性升级，将AI_Playlet_Agent从单一Agent架构升级为职责分离、工具精简、性能优化的多Agent协作系统。每个阶段都有明确的目标、具体的实施步骤和可衡量的交付物，确保升级过程的可控性和可追溯性。

通过这次架构升级，系统将获得：
- ✅ 更强的剧情规划能力
- ✅ 更好的错误处理机制  
- ✅ 更优的性能表现
- ✅ 更高的系统稳定性

为后续的功能扩展和性能优化奠定坚实基础。
