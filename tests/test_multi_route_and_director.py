import copy
import tempfile
import unittest

from tests.runtime_config_fixture import global_config
from input_adapter import build_free_mode_planner_output
from main_loop import create_episode_session, run_episode
from planner_review import PlannerReviewState, approve_planner_outline, revise_planner_outline
from scheduler import extract_next_speakers


def build_three_role_planner_output() -> dict:
    return {
        "episodes": [
            {
                "episode_number": 1,
                "place": "林家客厅",
                "scene_roles": ["林若雪", "顾寒霆", "林白莲"],
                "first_speaker": "林若雪",
                "global_plot": "三人围绕真假千金当面对峙。",
                "core_conflict": "林若雪逼顾寒霆和林白莲同时表态。",
                "plot_twist_or_hook": "顾寒霆开始怀疑林白莲是否一直在撒谎。",
                "character_directives": {
                    "林若雪": "主动控场，逼两人当场给出答案。",
                    "顾寒霆": "保持强硬姿态，但被迫回应。",
                    "林白莲": "先装可怜，再尝试带偏节奏。",
                },
            }
        ]
    }


class FakePlannerAgent:
    def __init__(self, payload):
        self.payload = payload
        self.prompts = []

    def generate_outline(self, prompt):
        self.prompts.append(prompt)
        return copy.deepcopy(self.payload)


class FakeRoleAgent:
    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    def generate_role_response(self, role_name, prompt):
        self.prompts.append((role_name, prompt))
        if not self.responses:
            return "api_error"
        response = self.responses.pop(0)
        return copy.deepcopy(response)


class MultiRouteAndDirectorTest(unittest.TestCase):
    def test_extract_next_speakers_supports_legacy_and_new_fields(self):
        self.assertEqual(
            extract_next_speakers({"next_speaker": "顾寒霆"}),
            ["顾寒霆"],
        )
        self.assertEqual(
            extract_next_speakers({"next_speakers": ["顾寒霆", "林白莲", "顾寒霆", ""]}),
            ["顾寒霆", "林白莲"],
        )
        self.assertEqual(
            extract_next_speakers({"next_speaker": ["end"]}),
            ["end"],
        )

    def test_run_episode_supports_queue_mode(self):
        role_agent = FakeRoleAgent(
            [
                {
                    "Inner_Thought": "我要同时逼他们表态。",
                    "Action": "林若雪抬手指向两人。",
                    "Dialogue": "你们两个，今天都别想躲。",
                    "next_speakers": ["顾寒霆", "林白莲"],
                },
                {
                    "Inner_Thought": "先回她一句。",
                    "Action": "顾寒霆皱眉。",
                    "Dialogue": "你想逼我站队？",
                    "next_speakers": [],
                },
                {
                    "Inner_Thought": "我得先装委屈。",
                    "Action": "林白莲眼圈泛红。",
                    "Dialogue": "姐姐，你为什么要这样逼我们？",
                    "next_speakers": [],
                },
            ]
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_episode(
                build_three_role_planner_output(),
                role_agent,
                1,
                summary_agent=None,
                max_turns=3,
                log_dir=temp_dir,
            )

        self.assertEqual(result["status"], "max_turns_reached")
        self.assertEqual(result["last_speaker"], "林若雪")
        self.assertEqual(result["turn_trace"][0]["status"], "queue_open")
        self.assertEqual(result["turn_trace"][1]["status"], "queue_continue")
        self.assertEqual(result["turn_trace"][2]["status"], "queue_continue")

    def test_director_rollback_restores_previous_snapshot(self):
        role_agent = FakeRoleAgent(
            [
                {
                    "Inner_Thought": "第一步先逼问。",
                    "Action": "林若雪逼近一步。",
                    "Dialogue": "顾寒霆，你给我解释清楚。",
                    "next_speakers": ["顾寒霆"],
                },
                {
                    "Inner_Thought": "我先稳住场子。",
                    "Action": "顾寒霆冷下脸。",
                    "Dialogue": "你还没资格这样跟我说话。",
                    "next_speakers": ["林若雪"],
                },
            ]
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            session = create_episode_session(
                build_three_role_planner_output(),
                role_agent,
                1,
                max_turns=4,
                log_dir=temp_dir,
            )
            session.run_next_turn()
            session.run_next_turn()
            rollback_result = session.apply_director_command("rollback", step=1)

        self.assertEqual(rollback_result["status"], "rolled_back")
        self.assertEqual(session.runtime_state.story.current_turn, 1)
        self.assertEqual(len(session.turn_trace), 1)
        self.assertEqual(session.current_speaker, "顾寒霆")

    def test_free_mode_planner_output_creates_minimal_episode_plan(self):
        runtime_config = copy.deepcopy(global_config)
        planner_output = build_free_mode_planner_output(
            runtime_config,
            opening_scene="总裁办公室",
            scene_roles=["林若雪", "顾寒霆"],
            story_hook="一份足以翻盘的录音",
        )

        episode = planner_output["episodes"][0]
        self.assertEqual(episode["place"], "总裁办公室")
        self.assertEqual(episode["scene_roles"], ["林若雪", "顾寒霆"])
        self.assertEqual(episode["first_speaker"], "林若雪")
        self.assertIn("录音", episode["plot_twist_or_hook"])

    def test_planner_review_flow_replaces_outline_and_marks_approved(self):
        review_state = PlannerReviewState(
            planner_output={"episodes": [{"episode_number": 1, "global_plot": "旧版本"}]}
        )
        fake_planner = FakePlannerAgent(
            {"episodes": [{"episode_number": 1, "global_plot": "新版本"}]}
        )
        revised = revise_planner_outline(
            review_state,
            fake_planner,
            copy.deepcopy(global_config),
            "把第一集改成先公开打脸，再抛出假千金的谎言。",
        )
        approved = approve_planner_outline(review_state)

        self.assertEqual(revised["episodes"][0]["global_plot"], "新版本")
        self.assertEqual(approved["episodes"][0]["global_plot"], "新版本")
        self.assertTrue(review_state.approved)
        self.assertEqual(review_state.review_history[-1]["action"], "approve_outline")


if __name__ == "__main__":
    unittest.main()
