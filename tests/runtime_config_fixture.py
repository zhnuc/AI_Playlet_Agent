"""Shared runtime config fixture for tests."""

global_config = {
    "drama_settings": {
        "theme": "复仇",
        "target_audience": "女性向",
        "expected_episodes": 5,
    },
    "logline": "真千金归来，手撕绿茶假千金和渣男，夺回家族产业。",
    "character_roster": {
        "林若雪": {
            "char_id": 1,
            "role_type": "主角",
            "gender": "女",
            "age": 22,
            "identity": "真千金",
            "appearance_tags": ["美艳御姐", "冰霜美人"],
            "personality_tags": ["毒舌", "冷静缜密", "杀伐果断"],
            "catchphrase": "属于我的东西，连本带利都要拿回来。",
        },
        "顾寒霆": {
            "char_id": 2,
            "role_type": "主角",
            "gender": "男",
            "age": 28,
            "identity": "京圈太子爷",
            "appearance_tags": ["高大霸气", "西装暴徒"],
            "personality_tags": ["霸道", "自傲", "暴脾气"],
            "catchphrase": "女人，别无理取闹，你在玩火。",
        },
        "林白莲": {
            "char_id": 3,
            "role_type": "反派",
            "gender": "女",
            "age": 21,
            "identity": "假千金",
            "appearance_tags": ["小白花", "楚楚可怜", "柔情似水"],
            "personality_tags": ["绿茶", "心机", "嫉妒心强"],
            "catchphrase": "姐姐，都是我的错，你别怪寒霆哥哥……",
        },
    },
}

