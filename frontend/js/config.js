(function attachPlayletConfig(global) {
const options = {
  genre: ["重生复仇", "豪门虐恋", "逆袭爽文", "先婚后爱", "职场博弈", "悬疑反转"],
  runMode: [
    { value: "planned", label: "大纲驱动" },
    { value: "free", label: "自由开场" }
  ],
  scene: ["总裁办公室", "家族晚宴", "发布会后台", "直播间", "医院走廊", "董事会会议室"]
};

const roleTemplateCatalog = {
  heroine: [
    {
      id: "reborn-heiress",
      label: "重生真千金",
      draft: {
        name: "林若雪",
        role_type: "主角",
        gender: "女",
        age: 22,
        identity: "真千金",
        appearance_tags: ["美艳御姐", "冰霜美人"],
        personality_tags: ["毒舌", "冷静缜密", "杀伐果断"],
        catchphrase: "属于我的东西，连本带利都要拿回来！"
      }
    },
    {
      id: "ice-lawyer",
      label: "冷感律师女主",
      draft: {
        name: "沈书意",
        role_type: "主角",
        gender: "女",
        age: 29,
        identity: "金牌律师",
        appearance_tags: ["利落短发", "冷白皮", "锋利眼神"],
        personality_tags: ["克制", "聪明", "反击心强"],
        catchphrase: "要讲规矩，就先把证据摆上桌。"
      }
    }
  ],
  hero: [
    {
      id: "capital-heir",
      label: "京圈太子爷",
      draft: {
        name: "顾寒霆",
        role_type: "主角",
        gender: "男",
        age: 28,
        identity: "京圈太子爷",
        appearance_tags: ["高大霸气", "西装暴徒"],
        personality_tags: ["霸道", "自傲", "暴脾气"],
        catchphrase: "女人，别无理取闹，你在玩火。"
      }
    },
    {
      id: "hidden-investor",
      label: "隐忍投资人",
      draft: {
        name: "陆沉舟",
        role_type: "主角",
        gender: "男",
        age: 31,
        identity: "神秘投资人",
        appearance_tags: ["黑衬衫", "疏离感", "冷峻轮廓"],
        personality_tags: ["沉稳", "控制欲", "善于布局"],
        catchphrase: "我不做赔本交易，包括感情。"
      }
    }
  ],
  villain: [
    {
      id: "false-heiress",
      label: "假千金反派",
      draft: {
        name: "林白莲",
        role_type: "反派",
        gender: "女",
        age: 21,
        identity: "假千金",
        appearance_tags: ["小白花", "楚楚可怜", "柔情似水"],
        personality_tags: ["绿茶", "心机", "嫉妒心强"],
        catchphrase: "姐姐，都是我的错，你别怪寒霆哥哥。"
      }
    },
    {
      id: "queen-rival",
      label: "名媛对手盘",
      draft: {
        name: "苏晚棠",
        role_type: "反派",
        gender: "女",
        age: 27,
        identity: "顶流名媛",
        appearance_tags: ["红唇高跟", "锋利妆容", "高定礼服"],
        personality_tags: ["强势", "讥讽", "善于操控舆论"],
        catchphrase: "你以为翻盘了？我只是让你多喘两口气。"
      }
    }
  ],
  support: [
    {
      id: "wingwoman",
      label: "闺蜜军师",
      draft: {
        name: "沈知意",
        role_type: "配角",
        gender: "女",
        age: 25,
        identity: "女主闺蜜兼军师",
        appearance_tags: ["明艳", "利落穿搭"],
        personality_tags: ["嘴快", "护短", "执行力强"],
        catchphrase: "你只管往前冲，脏活我来补刀。"
      }
    },
    {
      id: "assistant",
      label: "总裁助理",
      draft: {
        name: "周砚",
        role_type: "配角",
        gender: "男",
        age: 26,
        identity: "总裁助理",
        appearance_tags: ["金丝眼镜", "西装笔挺"],
        personality_tags: ["谨慎", "机灵", "站队快"],
        catchphrase: "顾总，这件事恐怕已经压不住了。"
      }
    },
    {
      id: "elder",
      label: "家族长辈",
      draft: {
        name: "林夫人",
        role_type: "配角",
        gender: "女",
        age: 48,
        identity: "家族长辈",
        appearance_tags: ["珍珠耳环", "端庄旗袍"],
        personality_tags: ["强势", "护短", "重体面"],
        catchphrase: "家丑不外扬，谁都别想砸了这个家。"
      }
    },
    {
      id: "reporter",
      label: "媒体记者",
      draft: {
        name: "唐梨",
        role_type: "配角",
        gender: "女",
        age: 24,
        identity: "娱乐记者",
        appearance_tags: ["短发", "相机包"],
        personality_tags: ["敏锐", "爱八卦", "追热点"],
        catchphrase: "这个爆点一出来，全网今晚都别睡了。"
      }
    }
  ]
};

const rolePositionCatalog = [
  { value: "male_lead_1", label: "男一号", type: "主角", priority: 1, unique: true, lockedGender: "男" },
  { value: "female_lead_1", label: "女一号", type: "主角", priority: 2, unique: true, lockedGender: "女" },
  { value: "chief_villain", label: "大反派", type: "反派", priority: 3, unique: true },
  { value: "male_lead_2", label: "男二号", type: "主角", priority: 4, unique: true, lockedGender: "男" },
  { value: "female_lead_2", label: "女二号", type: "主角", priority: 5, unique: true, lockedGender: "女" },
  { value: "minor_villain", label: "小反派", type: "反派", priority: 6, unique: false },
  { value: "supporting", label: "配角", type: "配角", priority: 99, unique: false }
];

const rolePositionMap = Object.fromEntries(rolePositionCatalog.map((item) => [item.value, item]));

const defaultRolePositionByGroup = {
  heroine: "female_lead_1",
  hero: "male_lead_1",
  villain: "chief_villain",
  support: "supporting"
};

const starterRoleDefinitions = [
  { group: "heroine", templateId: "reborn-heiress", rolePosition: "female_lead_1" },
  { group: "hero", templateId: "capital-heir", rolePosition: "male_lead_1" },
  { group: "villain", templateId: "false-heiress", rolePosition: "chief_villain" }
];

const allRoleTemplateGroups = ["heroine", "hero", "villain", "support"];

const roleGroupLabels = {
  heroine: "女主模板",
  hero: "男主模板",
  villain: "反派模板",
  support: "配角模板"
};

const promptMap = {
  重生复仇: "首场戏直接触发上一世遗留的信息差，前三句必须听得出人物带着旧账而来。",
  豪门虐恋: "对话要短，压迫感要强，尽量把情绪藏在动作和停顿里。",
  逆袭爽文: "每轮都让主角更占上风，避免重复争吵，优先抛出证据或权力转换。",
  先婚后爱: "冲突中保留暧昧缝隙，让表面针锋相对和潜在互相试探同时存在。",
  职场博弈: "每句台词都尽量带目标感，不说空话，优先围绕利益和职位关系推进。",
  悬疑反转: "动作描写要留白，让观众知道事情不对劲，但不要一次性把底牌掀完。"
};

  global.PLAYLET_CONFIG = {
    options,
    roleTemplateCatalog,
    rolePositionCatalog,
    rolePositionMap,
    defaultRolePositionByGroup,
    starterRoleDefinitions,
    allRoleTemplateGroups,
    roleGroupLabels,
    promptMap
  };
})(window);
