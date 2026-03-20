import copy
import json
import tempfile
import unittest
from pathlib import Path

from context_builder import build_role_context
from event_committer import append_event, finalize_role_memories_for_next_episode
from global_config import global_config
from main_loop import run_episode
from story_state import Event, RoleMemory, create_runtime_state


def build_test_planner_output() -> dict:
    """构造覆盖两集的最小 planner 输出。"""
    return {
        "episodes": [
            {
                "episode_number": 1,
                "place": "林家客厅",
                "scene_roles": ["林若雪", "顾寒霆"],
                "first_speaker": "林若雪",
                "global_plot": "真假千金冲突初次升级。",
                "core_conflict": "林若雪当众反击顾寒霆的偏见。",
                "plot_twist_or_hook": "顾寒霆开始怀疑林白莲。",
                "character_directives": {
                    "林若雪": "先压住情绪，再逼顾寒霆表态。",
                    "顾寒霆": "维持高位姿态，但开始观察林若雪。",
                },
            },
            {
                "episode_number": 2,
                "place": "顾氏办公室",
                "scene_roles": ["林若雪", "顾寒霆"],
                "first_speaker": "林若雪",
                "global_plot": "林若雪继续推进复仇计划。",
                "core_conflict": "顾寒霆被迫重新评估真假千金局势。",
                "plot_twist_or_hook": "林若雪掌握了新证据。",
                "character_directives": {
                    "林若雪": "逼顾寒霆公开站队。",
                    "顾寒霆": "在试探中重新判断局势。",
                },
            },
        ]
    }


def append_visible_event(
    runtime_state,
    event_id: str,
    step: int,
    speaker: str,
    content: str,
    visible_to: list[str],
    kind: str = "dialogue",
) -> None:
    """向测试运行时追加一条可见事件。"""
    append_event(
        runtime_state,
        Event(
            event_id=event_id,
            step=step,
            episode=runtime_state.story.current_episode,
            scene=runtime_state.story.current_scene,
            kind=kind,
            speaker=speaker,
            content=content,
            visible_to=visible_to,
        ),
    )


class FakeSummaryAgent:
    """测试用摘要 agent，返回预设摘要结果。"""

    def __init__(self, result):
        """初始化测试摘要 agent。"""
        self.result = result
        self.requests = []

    def generate_role_summaries(self, role_inputs):
        """记录输入并返回预设结果。"""
        self.requests.append(copy.deepcopy(role_inputs))
        return copy.deepcopy(self.result)


class FakeRoleAgent:
    """测试用角色 agent，按顺序返回预设输出。"""

    def __init__(self, responses):
        """初始化测试角色 agent。"""
        self.responses = list(responses)
        self.prompts = []

    def generate_role_response(self, role_name, prompt):
        """记录 prompt 并返回下一条测试响应。"""
        self.prompts.append((role_name, prompt))
        if not self.responses:
            return "api_error"
        response = self.responses.pop(0)
        return copy.deepcopy(response)


class PrivateSummaryFlowTest(unittest.TestCase):
    """覆盖 private summary 第一版主链路的单元测试。"""

    def setUp(self):
        """为每个测试准备独立输入。"""
        self.global_config = copy.deepcopy(global_config)
        self.planner_output = build_test_planner_output()

    def test_create_runtime_state_inherits_cross_episode_fields(self):
        """验证下一集初始化会继承跨集字段并清空集内临时字段。"""
        previous_role_memories = {
            "林若雪": RoleMemory(
                private_history=["e1", "e2"],
                private_summary="上一集已压缩摘要",
                summary_until_event_id="e2",
                carryover_summary="林若雪记得顾寒霆已经开始动摇。",
                carryover_event_tail=[
                    {
                        "event_id": "e1",
                        "step": 1,
                        "kind": "dialogue",
                        "speaker": "林若雪",
                        "content": "上一集尾部对话",
                    }
                ],
                current_goal="继续夺回家族产业",
                beliefs_about_others={"顾寒霆": "可以利用，但仍需防备"},
                unresolved_hook="顾寒霆尚未公开站队",
            ),
        }

        runtime_state = create_runtime_state(
            self.global_config,
            self.planner_output,
            2,
            previous_role_memories=previous_role_memories,
        )
        role_memory = runtime_state.role_memories["林若雪"]

        self.assertEqual(role_memory.private_history, [])
        self.assertEqual(role_memory.private_summary, "")
        self.assertIsNone(role_memory.summary_until_event_id)
        self.assertEqual(role_memory.carryover_summary, "林若雪记得顾寒霆已经开始动摇。")
        self.assertEqual(role_memory.carryover_event_tail[0]["content"], "上一集尾部对话")
        self.assertEqual(role_memory.unresolved_hook, "顾寒霆尚未公开站队")
        self.assertEqual(role_memory.beliefs_about_others["顾寒霆"], "可以利用，但仍需防备")
        self.assertIn("继续夺回家族产业", role_memory.current_goal)
        self.assertIn("逼顾寒霆公开站队", role_memory.current_goal)

    def test_build_role_context_uses_mixed_memory_and_fallback(self):
        """验证 prompt 会使用混合记忆结构，并保留 fallback 路径。"""
        runtime_state = create_runtime_state(self.global_config, self.planner_output, 1)
        role_memory = runtime_state.role_memories["林若雪"]
        role_memory.carryover_summary = "上一集最后，林若雪确认顾寒霆并非完全站在林白莲一边。"
        role_memory.private_summary = "本集前半段，林若雪已经连续试探顾寒霆。"
        role_memory.summary_until_event_id = "e2"
        role_memory.beliefs_about_others = {"顾寒霆": "表面强硬，实际开始犹豫"}
        role_memory.unresolved_hook = "顾寒霆是否会公开怀疑林白莲"

        for index in range(1, 8):
            append_visible_event(
                runtime_state,
                event_id=f"e{index}",
                step=index,
                speaker="林若雪" if index % 2 else "顾寒霆",
                content=f"测试事件{index}",
                visible_to=["林若雪", "顾寒霆"],
            )
        role_memory.carryover_event_tail = [
            {
                "event_id": "c1",
                "step": 99,
                "kind": "dialogue",
                "speaker": "顾寒霆",
                "content": "上一集尾巴事件A",
            },
            {
                "event_id": "c2",
                "step": 100,
                "kind": "action",
                "speaker": "林若雪",
                "content": "上一集尾巴事件B",
            },
        ]

        episode_plan = self.planner_output["episodes"][0]
        mixed_prompt = build_role_context("林若雪", runtime_state, episode_plan, tail_window=4)
        fallback_prompt = build_role_context(
            "林若雪",
            runtime_state,
            episode_plan,
            fallback_history_window=2,
            use_fallback_history=True,
        )

        self.assertIn("跨集记忆摘要", mixed_prompt)
        self.assertIn("当前集已压缩摘要", mixed_prompt)
        self.assertIn("测试事件3", mixed_prompt)
        self.assertIn("测试事件4", mixed_prompt)
        self.assertIn("测试事件7", mixed_prompt)
        self.assertNotIn("测试事件1", mixed_prompt)
        self.assertNotIn("测试事件2", mixed_prompt)

        self.assertIn("Fallback Memory", fallback_prompt)
        self.assertIn("上一集尾巴事件A", fallback_prompt)
        self.assertIn("上一集尾巴事件B", fallback_prompt)
        self.assertNotIn("测试事件7", fallback_prompt)

    def test_finalize_role_memories_for_next_episode_updates_valid_roles_only(self):
        """验证集末摘要会逐角色回写，并对非法角色结果单独降级。"""
        runtime_state = create_runtime_state(self.global_config, self.planner_output, 1)
        runtime_state.role_memories["顾寒霆"].current_goal = "继续试探林若雪"

        append_visible_event(runtime_state, "e1", 1, "林若雪", "林若雪冷声逼问。", ["林若雪", "顾寒霆"])
        append_visible_event(runtime_state, "e2", 2, "顾寒霆", "顾寒霆当众反击。", ["顾寒霆"])

        summary_agent = FakeSummaryAgent(
            {
                "林若雪": {
                    "carryover_summary": "林若雪确认顾寒霆已经动摇。",
                    "current_goal": "下一集继续逼顾寒霆站队。",
                    "beliefs_about_others": {"顾寒霆": "可继续施压"},
                    "unresolved_hook": "顾寒霆是否会公开翻脸",
                },
                "顾寒霆": {
                    "carryover_summary": "顾寒霆开始怀疑。",
                },
            }
        )

        summary_status = finalize_role_memories_for_next_episode(runtime_state, summary_agent)

        self.assertEqual(summary_status["林若雪"], "updated")
        self.assertEqual(summary_status["顾寒霆"], "schema_error")
        self.assertEqual(runtime_state.role_memories["林若雪"].private_summary, "林若雪确认顾寒霆已经动摇。")
        self.assertEqual(runtime_state.role_memories["林若雪"].carryover_summary, "林若雪确认顾寒霆已经动摇。")
        self.assertEqual(runtime_state.role_memories["林若雪"].carryover_event_tail[-1]["event_id"], "e1")
        self.assertEqual(runtime_state.role_memories["林若雪"].summary_until_event_id, "e1")
        self.assertEqual(runtime_state.role_memories["林若雪"].beliefs_about_others["顾寒霆"], "可继续施压")
        self.assertEqual(runtime_state.role_memories["顾寒霆"].current_goal, "继续试探林若雪")
        self.assertEqual(runtime_state.role_memories["顾寒霆"].carryover_summary, "")
        self.assertEqual(runtime_state.role_memories["顾寒霆"].carryover_event_tail[-1]["event_id"], "e2")

    def test_run_episode_uses_fallback_prompt_when_previous_episode_summary_missing(self):
        """验证上一集摘要失败后，下一集首轮会自动切到 fallback prompt。"""
        first_episode_role_agent = FakeRoleAgent(
            [
                {
                    "Inner_Thought": "我先记下顾寒霆的反应。",
                    "Action": "林若雪把证据按在桌上。",
                    "Dialogue": "你现在还敢说我没有准备吗？",
                    "next_speaker": "顾寒霆",
                }
            ]
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            first_result = run_episode(
                self.planner_output,
                first_episode_role_agent,
                1,
                summary_agent=None,
                max_turns=1,
                log_dir=temp_dir,
            )

            self.assertEqual(first_result["summary_status"]["林若雪"], "summary_agent_missing")
            previous_role_memories = first_result["runtime_state"].role_memories
            self.assertTrue(previous_role_memories["林若雪"].carryover_event_tail)
            self.assertEqual(previous_role_memories["林若雪"].carryover_summary, "")

            second_episode_role_agent = FakeRoleAgent(["api_error"])
            run_episode(
                self.planner_output,
                second_episode_role_agent,
                2,
                previous_role_memories=previous_role_memories,
                max_turns=1,
                log_dir=temp_dir,
            )

        first_prompt = second_episode_role_agent.prompts[0][1]
        self.assertIn("Fallback Memory", first_prompt)
        self.assertIn("林若雪把证据按在桌上", first_prompt)
        self.assertIn("你现在还敢说我没有准备吗", first_prompt)
        self.assertNotIn("跨集记忆摘要", first_prompt)

    def test_run_episode_carries_summary_into_next_episode_prompt(self):
        """验证 run_episode 会在收尾回写摘要，并在下一集 prompt 中继承。"""
        first_episode_role_agent = FakeRoleAgent(
            [
                {
                    "Inner_Thought": "我要先稳住局面。",
                    "Action": "林若雪向前一步。",
                    "Dialogue": "顾寒霆，你最好别再装糊涂。",
                    "next_speaker": "顾寒霆",
                },
                {
                    "Inner_Thought": "她比我预想中更强势。",
                    "Action": "顾寒霆收紧视线。",
                    "Dialogue": "证据拿出来，我才会信你。",
                    "next_speaker": "林若雪",
                },
            ]
        )
        summary_agent = FakeSummaryAgent(
            {
                "林若雪": {
                    "carryover_summary": "林若雪已经逼出顾寒霆的迟疑。",
                    "current_goal": "下一集继续逼顾寒霆公开站队。",
                    "beliefs_about_others": {"顾寒霆": "已经动摇，但还在嘴硬"},
                    "unresolved_hook": "顾寒霆何时会公开怀疑林白莲",
                },
                "顾寒霆": {
                    "carryover_summary": "顾寒霆开始意识到林若雪掌握了真凭实据。",
                    "current_goal": "下一集继续试探林若雪掌握了多少证据。",
                    "beliefs_about_others": {"林若雪": "并非空口指控"},
                    "unresolved_hook": "是否要亲自查林白莲",
                },
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            first_result = run_episode(
                self.planner_output,
                first_episode_role_agent,
                1,
                summary_agent=summary_agent,
                max_turns=2,
                log_dir=temp_dir,
            )

            self.assertEqual(first_result["summary_status"]["林若雪"], "updated")
            previous_role_memories = first_result["runtime_state"].role_memories

            second_episode_role_agent = FakeRoleAgent(["api_error"])
            second_result = run_episode(
                self.planner_output,
                second_episode_role_agent,
                2,
                previous_role_memories=previous_role_memories,
                max_turns=1,
                log_dir=temp_dir,
            )

        first_prompt = second_episode_role_agent.prompts[0][1]
        self.assertIn("林若雪已经逼出顾寒霆的迟疑", first_prompt)
        self.assertIn("已经动摇，但还在嘴硬", first_prompt)
        self.assertNotIn("Fallback Memory", first_prompt)
        self.assertEqual(second_result["status"], "api_error")

    def test_episode_log_includes_prompt_events_and_memory_snapshots(self):
        """验证日志会写入 prompt、提交事件和集初集末记忆快照。"""
        role_agent = FakeRoleAgent(
            [
                {
                    "Inner_Thought": "我要压住她的气势。",
                    "Action": "顾寒霆挡在林白莲身前。",
                    "Dialogue": "今天谁也别想在这里乱来。",
                    "next_speaker": "end",
                }
            ]
        )
        summary_agent = FakeSummaryAgent(
            {
                "林若雪": {
                    "carryover_summary": "",
                    "current_goal": "继续施压。",
                    "beliefs_about_others": {},
                    "unresolved_hook": "",
                },
                "顾寒霆": {
                    "carryover_summary": "顾寒霆决定先稳住局面。",
                    "current_goal": "继续保护林白莲。",
                    "beliefs_about_others": {"林若雪": "来者不善"},
                    "unresolved_hook": "要查清林若雪底细",
                },
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            run_episode(
                self.planner_output,
                role_agent,
                1,
                summary_agent=summary_agent,
                max_turns=1,
                log_dir=temp_dir,
            )

            log_payload = json.loads(
                Path(temp_dir, "episode_01_trace.json").read_text(encoding="utf-8")
            )

        self.assertIn("initial_role_memories", log_payload)
        self.assertIn("林若雪", log_payload["initial_role_memories"])
        self.assertEqual(len(log_payload["turns"]), 1)
        first_turn = log_payload["turns"][0]
        self.assertIn("prompt", first_turn)
        self.assertIn("strict json", first_turn["prompt"].lower())
        self.assertFalse(first_turn["use_fallback_history"])
        self.assertEqual(len(first_turn["committed_events"]), 3)
        self.assertEqual(first_turn["committed_events"][0]["kind"], "thought")
        self.assertEqual(first_turn["committed_events"][1]["kind"], "action")
        self.assertEqual(first_turn["committed_events"][2]["kind"], "dialogue")
        self.assertIn("final_role_memories", log_payload["result"])
        self.assertEqual(log_payload["result"]["summary_status"]["顾寒霆"], "updated")
        self.assertEqual(
            log_payload["result"]["final_role_memories"]["顾寒霆"]["carryover_summary"],
            "顾寒霆决定先稳住局面。",
        )


if __name__ == "__main__":
    unittest.main()
