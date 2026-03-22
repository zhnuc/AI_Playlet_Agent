import copy
import json
import tempfile
import unittest
from pathlib import Path

from context_builder import build_role_context
from event_committer import append_event, finalize_role_memories_for_next_episode
from global_config import global_config
from main_loop import run_episode, run_season
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

    def test_run_episode_falls_back_to_valid_first_speaker_when_planner_is_invalid(self):
        """验证 planner 给出非法 first_speaker 时，运行时会降级到场内合法首发角色。"""
        planner_output = copy.deepcopy(self.planner_output)
        planner_output["episodes"][0]["first_speaker"] = "拍卖师"
        role_agent = FakeRoleAgent(
            [
                {
                    "Inner_Thought": "林若雪先把场子稳住。",
                    "Action": "林若雪抬眼看向顾寒霆。",
                    "Dialogue": "今天谁都别想装作没看到。",
                    "next_speaker": "顾寒霆",
                }
            ]
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_episode(
                planner_output,
                role_agent,
                1,
                summary_agent=None,
                max_turns=1,
                log_dir=temp_dir,
            )

        self.assertEqual(role_agent.prompts[0][0], "林若雪")
        self.assertEqual(result["status"], "max_turns_reached")
        self.assertEqual(result["turn_trace"][0]["speaker"], "林若雪")

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

    def test_run_episode_retries_once_when_next_speaker_invalid_then_succeeds(self):
        """验证 next_speaker 非法时会先重试一次，合法后继续推进。"""
        role_agent = FakeRoleAgent(
            [
                {
                    "Inner_Thought": "先把顾寒霆的注意力拉回来。",
                    "Action": "林若雪将证据推到桌前。",
                    "Dialogue": "你别装作什么都不知道。",
                    "next_speaker": "手下",
                },
                {
                    "Inner_Thought": "这次不能再乱跳路由。",
                    "Action": "林若雪继续逼近顾寒霆。",
                    "Dialogue": "现在轮到你回答我。",
                    "next_speaker": "顾寒霆",
                },
            ]
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_episode(
                self.planner_output,
                role_agent,
                1,
                summary_agent=None,
                max_turns=1,
                log_dir=temp_dir,
            )

        self.assertEqual(result["status"], "max_turns_reached")
        self.assertEqual(result["turn_trace"][0]["route_retry_count"], 1)
        self.assertEqual(result["runtime_state"].story.current_turn, 1)
        self.assertEqual(len(result["runtime_state"].story.event_log), 3)
        self.assertEqual(len(role_agent.prompts), 2)
        retry_prompt = role_agent.prompts[1][1]
        self.assertIn("你上一轮的 `next_speaker` 为 `手下`", retry_prompt)
        self.assertIn("顾寒霆", retry_prompt)
        self.assertIn("先保证路由合理，再继续推进本集核心冲突", retry_prompt)

    def test_run_episode_handoff_when_next_speaker_invalid_after_retry(self):
        """验证 next_speaker 连续非法两次后会直接进入 handoff。"""
        role_agent = FakeRoleAgent(
            [
                {
                    "Inner_Thought": "先制造一点压力。",
                    "Action": "林若雪把文件拍在桌上。",
                    "Dialogue": "你最好现在就给我解释。",
                    "next_speaker": "手下",
                },
                {
                    "Inner_Thought": "路由还是不对。",
                    "Action": "林若雪不肯退让。",
                    "Dialogue": "别找场外的人来搪塞我。",
                    "next_speaker": "医生",
                },
            ]
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_episode(
                self.planner_output,
                role_agent,
                1,
                summary_agent=None,
                max_turns=1,
                log_dir=temp_dir,
            )

        self.assertEqual(result["status"], "handoff")
        self.assertEqual(result["runtime_state"].story.current_turn, 0)
        self.assertEqual(len(result["runtime_state"].story.event_log), 0)
        self.assertEqual(result["turn_trace"], [])
        self.assertEqual(len(role_agent.prompts), 2)
        retry_prompt = role_agent.prompts[1][1]
        self.assertIn("你上一轮的 `next_speaker` 为 `手下`", retry_prompt)
        self.assertIn("你本轮只能从以下值中选择：顾寒霆、end", retry_prompt)

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
        self.assertNotIn("Retry Note", first_turn["prompt"])
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

    def test_run_season_defaults_to_cross_episode_continuity(self):
        """验证 run_season 默认承接上一集角色记忆，并让第二集 prompt 看到跨集摘要。"""
        role_agent = FakeRoleAgent(
            [
                {
                    "Inner_Thought": "我先试探顾寒霆的反应。",
                    "Action": "林若雪把文件放到桌上。",
                    "Dialogue": "你最好现在就给我一个态度。",
                    "next_speaker": "顾寒霆",
                },
                {
                    "Inner_Thought": "上一集已经把他逼到犹豫边缘。",
                    "Action": "林若雪继续前压。",
                    "Dialogue": "这一次，你没有退路了。",
                    "next_speaker": "顾寒霆",
                },
            ]
        )
        summary_agent = FakeSummaryAgent(
            {
                "林若雪": {
                    "carryover_summary": "林若雪已经逼出顾寒霆的迟疑。",
                    "current_goal": "继续逼顾寒霆公开站队。",
                    "beliefs_about_others": {"顾寒霆": "已经开始松动"},
                    "unresolved_hook": "顾寒霆何时公开翻脸",
                },
                "顾寒霆": {
                    "carryover_summary": "顾寒霆意识到林若雪并非虚张声势。",
                    "current_goal": "继续观察林若雪手里的证据。",
                    "beliefs_about_others": {"林若雪": "手里确实有筹码"},
                    "unresolved_hook": "是否要私下调查林白莲",
                },
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            season_result = run_season(
                self.planner_output,
                role_agent,
                summary_agent=summary_agent,
                max_turns=1,
                log_dir=temp_dir,
            )
            self.assertEqual(season_result["status"], "completed")
            self.assertTrue(season_result["run_id"])
            self.assertEqual(season_result["completed_episode_numbers"], [1, 2])
            self.assertEqual(len(season_result["episode_results"]), 2)
            season_log_dir = Path(season_result["season_log_dir"])
            self.assertTrue((season_log_dir / "planner_output.json").exists())
            self.assertTrue((season_log_dir / "season_context.json").exists())
            self.assertTrue((season_log_dir / "season_summary.json").exists())
            self.assertTrue((season_log_dir / "episode_01_trace.json").exists())
            self.assertTrue((season_log_dir / "episode_02_trace.json").exists())
            self.assertTrue((season_log_dir / "checkpoints" / "episode_01_checkpoint.json").exists())
            self.assertTrue((season_log_dir / "checkpoints" / "episode_02_checkpoint.json").exists())
            season_context_payload = json.loads(
                (season_log_dir / "season_context.json").read_text(encoding="utf-8")
            )
            season_summary_payload = json.loads(
                (season_log_dir / "season_summary.json").read_text(encoding="utf-8")
            )
            episode_one_checkpoint = json.loads(
                (season_log_dir / "checkpoints" / "episode_01_checkpoint.json").read_text(encoding="utf-8")
            )
            self.assertEqual(season_result["season_context"]["completed_episode_numbers"], [1, 2])
            self.assertEqual(
                season_result["season_context"]["season_stats"]["episode_status_map"],
                {"1": "max_turns_reached", "2": "max_turns_reached"},
            )
            self.assertEqual(
                season_context_payload["season_stats"]["episode_status_map"],
                {"1": "max_turns_reached", "2": "max_turns_reached"},
            )
            self.assertEqual(season_summary_payload["successful_episode_count"], 2)
            self.assertEqual(season_summary_payload["failed_episode_count"], 0)
            self.assertTrue(season_summary_payload["completed_all_planned_episodes"])
            self.assertEqual(episode_one_checkpoint["completed_episode"], 1)
            self.assertEqual(episode_one_checkpoint["remaining_episode_numbers"], [2])
            self.assertIn("replan_context_stub", episode_one_checkpoint)
            self.assertIn("planner_baseline", season_result["season_context"])
            self.assertNotIn("carryover_summary", season_result["season_context"])
        second_prompt = role_agent.prompts[1][1]
        self.assertIn("林若雪已经逼出顾寒霆的迟疑", second_prompt)
        self.assertIn("已经开始松动", second_prompt)
        self.assertNotIn("Fallback Memory", second_prompt)

    def test_run_season_stops_after_failed_episode(self):
        """验证某一集失败后，run_season 会停止后续集执行并返回失败原因。"""
        planner_output = copy.deepcopy(self.planner_output)
        planner_output["episodes"].append(
            {
                "episode_number": 3,
                "place": "林家花园",
                "scene_roles": ["林若雪", "顾寒霆"],
                "first_speaker": "林若雪",
                "global_plot": "第三集不应被执行。",
                "core_conflict": "该集只用于验证失败后停止。",
                "plot_twist_or_hook": "不应进入该集。",
                "character_directives": {
                    "林若雪": "如果进入这一集，说明 season 没有正确停止。",
                    "顾寒霆": "如果进入这一集，说明 season 没有正确停止。",
                },
            }
        )
        role_agent = FakeRoleAgent(
            [
                {
                    "Inner_Thought": "第一集先把气势拿住。",
                    "Action": "林若雪直视顾寒霆。",
                    "Dialogue": "我给你最后一次选择。",
                    "next_speaker": "顾寒霆",
                },
                "api_error",
            ]
        )
        summary_agent = FakeSummaryAgent(
            {
                "林若雪": {
                    "carryover_summary": "林若雪已经建立了压迫感。",
                    "current_goal": "继续逼顾寒霆表态。",
                    "beliefs_about_others": {"顾寒霆": "会继续观察，但已不再绝对强硬"},
                    "unresolved_hook": "顾寒霆何时会松口",
                },
                "顾寒霆": {
                    "carryover_summary": "顾寒霆感受到局势失控。",
                    "current_goal": "重新判断真假千金局势。",
                    "beliefs_about_others": {"林若雪": "并不简单"},
                    "unresolved_hook": "是否继续站在林白莲一边",
                },
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            season_result = run_season(
                planner_output,
                role_agent,
                summary_agent=summary_agent,
                max_turns=1,
                log_dir=temp_dir,
            )
            season_log_dir = Path(season_result["season_log_dir"])
            season_summary_payload = json.loads(
                (season_log_dir / "season_summary.json").read_text(encoding="utf-8")
            )
            self.assertTrue((season_log_dir / "checkpoints" / "episode_01_checkpoint.json").exists())
            self.assertTrue((season_log_dir / "checkpoints" / "episode_02_checkpoint.json").exists())
            self.assertFalse((season_log_dir / "checkpoints" / "episode_03_checkpoint.json").exists())
            self.assertEqual(season_result["status"], "stopped")
            self.assertEqual(season_result["stop_reason"], "api_error")
            self.assertEqual(season_result["completed_episode_count"], 2)
            self.assertEqual(season_result["completed_episode_numbers"], [1, 2])
            self.assertEqual(len(season_result["episode_results"]), 2)
            self.assertEqual(season_result["episode_results"][1]["status"], "api_error")
            self.assertEqual(
                season_result["season_context"]["season_stats"]["episode_status_map"],
                {"1": "max_turns_reached", "2": "api_error"},
            )
            self.assertEqual(season_summary_payload["failed_episode_count"], 1)
            self.assertEqual(season_summary_payload["episode_status_counts"]["api_error"], 1)
            self.assertFalse(season_summary_payload["completed_all_planned_episodes"])
        self.assertEqual(len(role_agent.prompts), 2)

    def test_run_season_creates_isolated_log_directories_for_multiple_runs(self):
        """验证同一日志根目录下多次 season 运行会生成不同 run 目录，不会互相覆盖。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            first_role_agent = FakeRoleAgent(
                [
                {
                    "Inner_Thought": "第一轮第一集。",
                    "Action": "林若雪先发制人。",
                    "Dialogue": "你现在就回答我。",
                    "next_speaker": "顾寒霆",
                },
                {
                    "Inner_Thought": "第一轮第二集。",
                    "Action": "林若雪继续逼问。",
                    "Dialogue": "你还想拖到什么时候？",
                    "next_speaker": "顾寒霆",
                },
            ]
        )
            second_role_agent = FakeRoleAgent(
                [
                {
                    "Inner_Thought": "第二轮第一集。",
                    "Action": "林若雪换了说法。",
                    "Dialogue": "这次你必须表态。",
                    "next_speaker": "顾寒霆",
                },
                {
                    "Inner_Thought": "第二轮第二集。",
                    "Action": "林若雪压低声音。",
                    "Dialogue": "你已经没有退路了。",
                    "next_speaker": "顾寒霆",
                },
            ]
        )

            first_result = run_season(
                self.planner_output,
                first_role_agent,
                summary_agent=None,
                max_turns=1,
                log_dir=temp_dir,
            )
            second_result = run_season(
                self.planner_output,
                second_role_agent,
                summary_agent=None,
                max_turns=1,
                log_dir=temp_dir,
            )

            season_runs_dir = Path(temp_dir) / "season_runs"
            self.assertNotEqual(first_result["run_id"], second_result["run_id"])
            self.assertNotEqual(first_result["season_log_dir"], second_result["season_log_dir"])
            self.assertTrue((Path(first_result["season_log_dir"]) / "planner_output.json").exists())
            self.assertTrue((Path(second_result["season_log_dir"]) / "planner_output.json").exists())
            self.assertTrue((Path(first_result["season_log_dir"]) / "episode_01_trace.json").exists())
            self.assertTrue((Path(second_result["season_log_dir"]) / "episode_01_trace.json").exists())
            self.assertEqual(len(list(season_runs_dir.iterdir())), 2)


if __name__ == "__main__":
    unittest.main()
