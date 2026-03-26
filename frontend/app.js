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

const coreRoleSlots = [
  { slot: "heroine", label: "女主", title: "女主角色卡", group: "heroine", defaultTemplateId: "reborn-heiress" },
  { slot: "hero", label: "男主", title: "男主角色卡", group: "hero", defaultTemplateId: "capital-heir" },
  { slot: "villain", label: "反派", title: "反派角色卡", group: "villain", defaultTemplateId: "false-heiress" }
];

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

const state = {
  selectedGenre: options.genre[0],
  runMode: "planned",
  sessionId: null,
  plannerOutput: null,
  outlineApproved: false,
  snapshot: null,
  shouldContinue: false,
  isLooping: false,
  initialInspirationHeight: null,
  roleDrafts: [],
  roleCounter: 1,
  roleDesignerOpen: false
};

const dom = {
  genreResult: document.querySelector("#genreResult"),
  runModeResult: document.querySelector("#runModeResult"),
  sceneResult: document.querySelector("#sceneResult"),
  modeBadge: document.querySelector("#modeBadge"),
  sessionBadge: document.querySelector("#sessionBadge"),
  statusBadge: document.querySelector("#statusBadge"),
  streamStatus: document.querySelector("#streamStatus"),
  outlineStatus: document.querySelector("#outlineStatus"),
  outlineTree: document.querySelector("#outlineTree"),
  inspirationPanel: document.querySelector(".inspiration-panel"),
  outlinePanel: document.querySelector(".outline-panel"),
  chatFeed: document.querySelector("#chatFeed"),
  monitorFeed: document.querySelector("#monitorFeed"),
  turnBadge: document.querySelector("#turnBadge"),
  promptPreview: document.querySelector("#promptPreview"),
  plotInput: document.querySelector("#plotInput"),
  sceneInput: document.querySelector("#sceneInput"),
  mainRoleCards: document.querySelector("#mainRoleCards"),
  roleSummary: document.querySelector("#roleSummary"),
  openRoleDesignerBtn: document.querySelector("#openRoleDesignerBtn"),
  roleDesignerModal: document.querySelector("#roleDesignerModal"),
  closeRoleDesignerBtn: document.querySelector("#closeRoleDesignerBtn"),
  rolePresetSelect: document.querySelector("#rolePresetSelect"),
  addPresetRoleBtn: document.querySelector("#addPresetRoleBtn"),
  addCustomRoleBtn: document.querySelector("#addCustomRoleBtn"),
  roleDesignerList: document.querySelector("#roleDesignerList"),
  roleDesignerStats: document.querySelector("#roleDesignerStats"),
  customTagInput: document.querySelector("#customTagInput"),
  episodeCount: document.querySelector("#episodeCount"),
  episodeCountValue: document.querySelector("#episodeCountValue"),
  roundLimit: document.querySelector("#roundLimit"),
  roundValue: document.querySelector("#roundValue"),
  timelineSlider: document.querySelector("#timelineSlider"),
  timelineValue: document.querySelector("#timelineValue"),
  nextEpisodeBtn: document.querySelector("#nextEpisodeBtn"),
  outlineFeedback: document.querySelector("#outlineFeedback"),
  directorCommand: document.querySelector("#directorCommand"),
  targetRole: document.querySelector("#targetRole"),
  scriptOutput: document.querySelector("#scriptOutput"),
  apiSnippet: document.querySelector("#apiSnippet"),
  apiHint: document.querySelector("#apiHint"),
  messageTemplate: document.querySelector("#messageTemplate")
};

function escapeMarkup(text) {
  return String(text ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function nextRoleId() {
  const id = `role-${state.roleCounter}`;
  state.roleCounter += 1;
  return id;
}

function cloneTemplateDraft(group, templateId) {
  const template = roleTemplateCatalog[group]?.find((item) => item.id === templateId);
  if (!template) {
    throw new Error(`unknown role template: ${group}/${templateId}`);
  }
  return {
    templateGroup: group,
    templateId,
    ...template.draft,
    appearance_tags: [...template.draft.appearance_tags],
    personality_tags: [...template.draft.personality_tags]
  };
}

function createRoleDraft(group, templateId, overrides = {}) {
  return {
    id: overrides.id || nextRoleId(),
    slot: overrides.slot || null,
    isCore: Boolean(overrides.slot),
    ...cloneTemplateDraft(group, templateId),
    ...overrides
  };
}

function createCustomRoleDraft() {
  return {
    id: nextRoleId(),
    slot: null,
    isCore: false,
    templateGroup: "support",
    templateId: null,
    name: `新角色${state.roleDrafts.length + 1}`,
    role_type: "配角",
    gender: "未设定",
    age: 24,
    identity: "待设定身份",
    appearance_tags: ["待补充"],
    personality_tags: ["待补充"],
    catchphrase: ""
  };
}

function normalizeTagList(value) {
  if (Array.isArray(value)) {
    return value.map((item) => String(item).trim()).filter(Boolean);
  }
  return String(value || "")
    .split(/[\n,，、;；]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function buildRoleSummary(role) {
  const personality = normalizeTagList(role.personality_tags).slice(0, 3);
  return [role.identity, ...personality, role.catchphrase].filter(Boolean).join("，");
}

function applySummaryToRole(role, summary) {
  const parts = String(summary || "")
    .split(/[\n，。；;、]/)
    .map((item) => item.trim())
    .filter(Boolean);

  const next = { ...role };
  if (parts[0]) {
    next.identity = parts[0];
  }
  if (parts.length >= 3) {
    next.personality_tags = parts.slice(1, parts.length - 1).slice(0, 3);
    next.catchphrase = parts[parts.length - 1];
  } else if (parts.length === 2) {
    next.catchphrase = parts[1];
  }
  return next;
}

function formatRoleBadge(role) {
  const chunks = [role.role_type || "角色", role.gender || "未设定"];
  if (role.age) {
    chunks.push(`${role.age} 岁`);
  }
  return chunks.join(" · ");
}

function initializeRoleDrafts() {
  state.roleDrafts = coreRoleSlots.map((slot) => createRoleDraft(slot.group, slot.defaultTemplateId, { slot: slot.slot }));
}

function getRoleDraftBySlot(slotName) {
  return state.roleDrafts.find((role) => role.slot === slotName) || null;
}

function getRoleDraftById(roleId) {
  return state.roleDrafts.find((role) => role.id === roleId) || null;
}

function replaceRoleDraft(roleId, nextDraft) {
  state.roleDrafts = state.roleDrafts.map((role) => (role.id === roleId ? nextDraft : role));
}

function updateRoleDraft(roleId, updater) {
  state.roleDrafts = state.roleDrafts.map((role) => {
    if (role.id !== roleId) return role;
    return updater(role);
  });
}

function buildTemplateOptions(groups, selectedValue) {
  return groups
    .map((group) => {
      const optionsHtml = roleTemplateCatalog[group]
        .map((template) => {
          const value = `${group}:${template.id}`;
          const selected = value === selectedValue ? " selected" : "";
          return `<option value="${value}"${selected}>${escapeMarkup(template.label)}</option>`;
        })
        .join("");
      return `<optgroup label="${escapeMarkup(roleGroupLabels[group])}">${optionsHtml}</optgroup>`;
    })
    .join("");
}

function getCurrentRoleTemplateValue(role) {
  return role.templateId ? `${role.templateGroup}:${role.templateId}` : "custom";
}

function renderRolePresetOptions() {
  dom.rolePresetSelect.innerHTML = roleTemplateCatalog.support
    .map((template) => `<option value="support:${template.id}">${escapeMarkup(template.label)}</option>`)
    .join("");
}

function updateRoleSummaryText() {
  const counts = state.roleDrafts.reduce(
    (acc, role) => {
      const key = role.role_type || "配角";
      acc[key] = (acc[key] || 0) + 1;
      return acc;
    },
    {}
  );
  dom.roleSummary.textContent = `当前 ${counts["主角"] || 0} 名主角、${counts["反派"] || 0} 名反派、${counts["配角"] || 0} 名配角。主视图仅固定展示女主、男主、反派三张核心角色卡。`;
  dom.roleDesignerStats.textContent = `已配置 ${state.roleDrafts.length} 个角色。你可以继续添加模板角色，或新增完全自定义角色。`;
}

function renderMainRoleCards() {
  dom.mainRoleCards.innerHTML = coreRoleSlots
    .map((slotConfig) => {
      const role = getRoleDraftBySlot(slotConfig.slot);
      if (!role) return "";
      return `
        <article class="role-card" data-role-slot="${slotConfig.slot}">
          <div class="role-card-head">
            <div>
              <p class="prompt-title">${escapeMarkup(slotConfig.title)}</p>
              <h3>${escapeMarkup(role.name)}</h3>
            </div>
            <span class="role-badge">${escapeMarkup(formatRoleBadge(role))}</span>
          </div>
          <label>
            模板
            <select data-role-slot="${slotConfig.slot}" data-field="template">
              ${buildTemplateOptions([slotConfig.group], getCurrentRoleTemplateValue(role))}
            </select>
          </label>
          <label>
            角色名
            <input type="text" value="${escapeMarkup(role.name)}" data-role-slot="${slotConfig.slot}" data-field="name">
          </label>
          <label>
            角色速写
            <textarea rows="4" data-role-slot="${slotConfig.slot}" data-field="summary">${escapeMarkup(buildRoleSummary(role))}</textarea>
          </label>
          <p class="role-card-hint">这里保留主角卡的快速编辑。完整字段和扩展角色数量请在“角色设计器”中维护。</p>
        </article>
      `;
    })
    .join("");
}

function renderRoleDesignerList() {
  dom.roleDesignerList.innerHTML = state.roleDrafts
    .map((role) => {
      const allowedGroups = role.slot ? [coreRoleSlots.find((item) => item.slot === role.slot).group] : ["support", "heroine", "hero", "villain"];
      const templateOptions = `${buildTemplateOptions(allowedGroups, getCurrentRoleTemplateValue(role))}<option value="custom"${role.templateId ? "" : " selected"}>保留当前自定义设定</option>`;
      const removeAction = role.isCore
        ? `<span class="role-badge">固定展示位</span>`
        : `<button class="danger-btn small" type="button" data-action="delete-role" data-role-id="${role.id}">删除角色</button>`;
      return `
        <article class="role-editor" data-role-id="${role.id}">
          <div class="role-editor-head">
            <div>
              <p class="prompt-title">${escapeMarkup(role.isCore ? "核心角色" : "扩展角色")}</p>
              <h3>${escapeMarkup(role.name)}</h3>
              <p>${escapeMarkup(formatRoleBadge(role))}</p>
            </div>
            ${removeAction}
          </div>
          <div class="role-editor-grid">
            <label>
              预设模板
              <select data-role-id="${role.id}" data-field="template">
                ${templateOptions}
              </select>
            </label>
            <label>
              角色名
              <input type="text" value="${escapeMarkup(role.name)}" data-role-id="${role.id}" data-field="name">
            </label>
            <label>
              角色定位
              <select data-role-id="${role.id}" data-field="role_type">
                <option value="主角"${role.role_type === "主角" ? " selected" : ""}>主角</option>
                <option value="反派"${role.role_type === "反派" ? " selected" : ""}>反派</option>
                <option value="配角"${role.role_type === "配角" ? " selected" : ""}>配角</option>
              </select>
            </label>
            <label>
              性别
              <select data-role-id="${role.id}" data-field="gender">
                <option value="女"${role.gender === "女" ? " selected" : ""}>女</option>
                <option value="男"${role.gender === "男" ? " selected" : ""}>男</option>
                <option value="未设定"${role.gender === "未设定" ? " selected" : ""}>未设定</option>
              </select>
            </label>
            <label>
              年龄
              <input type="text" value="${escapeMarkup(role.age)}" data-role-id="${role.id}" data-field="age">
            </label>
            <label>
              身份
              <input type="text" value="${escapeMarkup(role.identity)}" data-role-id="${role.id}" data-field="identity">
            </label>
            <label class="role-editor-span">
              外形标签
              <input type="text" value="${escapeMarkup(normalizeTagList(role.appearance_tags).join("，"))}" data-role-id="${role.id}" data-field="appearance_tags">
            </label>
            <label class="role-editor-span">
              性格标签
              <input type="text" value="${escapeMarkup(normalizeTagList(role.personality_tags).join("，"))}" data-role-id="${role.id}" data-field="personality_tags">
            </label>
            <label class="role-editor-span">
              口头禅
              <textarea rows="2" data-role-id="${role.id}" data-field="catchphrase">${escapeMarkup(role.catchphrase)}</textarea>
            </label>
          </div>
        </article>
      `;
    })
    .join("");
}

function openRoleDesigner() {
  state.roleDesignerOpen = true;
  dom.roleDesignerModal.classList.remove("hidden");
  dom.roleDesignerModal.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
  renderRoleDesignerList();
}

function closeRoleDesigner() {
  state.roleDesignerOpen = false;
  dom.roleDesignerModal.classList.add("hidden");
  dom.roleDesignerModal.setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-open");
}

function refreshRoleUI(options = {}) {
  updateRoleSummaryText();
  syncRoleOptions(getCurrentRoleNames());
  if (!options.skipMainCards) {
    renderMainRoleCards();
  }
  if (state.roleDesignerOpen && !options.skipDesignerList) {
    renderRoleDesignerList();
  }
}

function syncTopPanelHeights() {
  const inspirationPanel = dom.inspirationPanel;
  const outlinePanel = dom.outlinePanel;
  if (!inspirationPanel || !outlinePanel) return;

  const fixedHeight = state.initialInspirationHeight;
  const fallbackHeight = inspirationPanel.offsetHeight;
  const targetHeight = fixedHeight && fixedHeight > 0 ? fixedHeight : fallbackHeight;
  if (targetHeight > 0) {
    outlinePanel.style.maxHeight = `${targetHeight}px`;
  }
}

function captureInitialTopPanelHeight() {
  if (state.initialInspirationHeight) return;
  const inspirationPanel = dom.inspirationPanel;
  if (!inspirationPanel) return;

  requestAnimationFrame(() => {
    if (state.initialInspirationHeight) return;
    const initialHeight = inspirationPanel.offsetHeight;
    if (initialHeight > 0) {
      state.initialInspirationHeight = initialHeight;
      syncTopPanelHeights();
    }
  });
}

function initializeDefaults() {
  dom.genreResult.textContent = state.selectedGenre;
  dom.runModeResult.textContent = "大纲驱动";
  dom.modeBadge.textContent = "大纲驱动";
  dom.sceneResult.textContent = options.scene[0];
  dom.plotInput.value = "真千金归来，当场撕开假千金和渣男联手设局的第一层伪装。";
  dom.sceneInput.value = options.scene[0];
  dom.promptPreview.textContent = promptMap[state.selectedGenre];
  dom.scriptOutput.textContent = "还没有导出结果。先生成大纲并跑完一轮推演。";
  initializeRoleDrafts();
  renderRolePresetOptions();
  renderMainRoleCards();
  updateEpisodeCountDisplay();
  updateRoundDisplay();
  updateRoleSummaryText();
  syncRoleOptions(getCurrentRoleNames());
  renderAllChips();
  renderOutline();
  renderMessages();
  renderMonitorFeed();
  captureInitialTopPanelHeight();
  syncTopPanelHeights();
}

function renderChipGroup(field, values, selectedValue) {
  const container = document.querySelector(`.chip-list[data-field="${field}"]`);
  container.innerHTML = "";

  values.forEach((item) => {
    const value = typeof item === "string" ? item : item.value;
    const label = typeof item === "string" ? item : item.label;
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = `chip${value === selectedValue ? " active" : ""}`;
    chip.textContent = label;
    chip.addEventListener("click", () => {
      if (field === "genre") {
        state.selectedGenre = value;
        dom.genreResult.textContent = value;
        dom.promptPreview.textContent = promptMap[value] || promptMap[options.genre[0]];
      }
      if (field === "runMode") {
        state.runMode = value;
        const labelText = label;
        dom.runModeResult.textContent = labelText;
        dom.modeBadge.textContent = labelText;
      }
      renderAllChips();
    });
    container.appendChild(chip);
  });
}

function renderAllChips() {
  renderChipGroup("genre", options.genre, state.selectedGenre);
  renderChipGroup("runMode", options.runMode, state.runMode);
}

function sample(list) {
  return list[Math.floor(Math.random() * list.length)];
}

function randomizeAll() {
  const genre = sample(options.genre);
  const scene = sample(options.scene);
  state.selectedGenre = genre;
  dom.genreResult.textContent = genre;
  dom.sceneResult.textContent = scene;
  dom.sceneInput.value = scene;
  dom.plotInput.value = `围绕“${genre}”展开，开场直接爆发公开冲突，并在结尾抛出能钩住下一场的关键证据。`;
  dom.promptPreview.textContent = promptMap[genre] || promptMap[options.genre[0]];
  renderAllChips();
}

function optimizeInput() {
  const customTag = dom.customTagInput.value.trim();
  if (!customTag) {
    dom.promptPreview.textContent = "给我一个附加标签，我就会把它压缩成更好喂给 planner 的剧情提示。";
    return;
  }

  dom.promptPreview.textContent = `输入优化建议：把“${customTag}”写进冲突触发器，而不是背景说明。优先让它在第 1 集第 1 场直接发生。`;
}

function updateEpisodeCountDisplay() {
  dom.episodeCountValue.textContent = `${dom.episodeCount.value} 集`;
}

function updateRoundDisplay() {
  dom.roundValue.textContent = `${dom.roundLimit.value} 轮目标`;
}

function updateTimelineDisplay() {
  dom.timelineValue.textContent = `第 ${dom.timelineSlider.value} 句`;
}

function setStatus(text) {
  dom.statusBadge.textContent = text;
  dom.streamStatus.textContent = text;
}

function setApiPreview(title, payload) {
  const text = typeof payload === "string" ? payload : JSON.stringify(payload, null, 2);
  dom.apiSnippet.textContent = text;
  dom.apiHint.textContent = title;
}

function buildCharacterRoster() {
  const usedNames = new Set();
  const roster = {};

  state.roleDrafts.forEach((role, index) => {
    const baseName = String(role.name || `角色${index + 1}`).trim() || `角色${index + 1}`;
    let finalName = baseName;
    let counter = 2;
    while (usedNames.has(finalName)) {
      finalName = `${baseName}${counter}`;
      counter += 1;
    }
    usedNames.add(finalName);

    const appearance = normalizeTagList(role.appearance_tags);
    const personality = normalizeTagList(role.personality_tags);
    roster[finalName] = {
      char_id: index + 1,
      name: finalName,
      role_type: role.role_type || "配角",
      gender: role.gender || "未设定",
      age: Number(role.age) || 0,
      identity: String(role.identity || "待设定身份").trim() || "待设定身份",
      appearance_tags: appearance.length ? appearance : ["待补充"],
      personality_tags: personality.length ? personality : ["待补充"],
      catchphrase: String(role.catchphrase || "暂未设定口头禅。")
    };
  });

  return roster;
}

function getCurrentRoleNames() {
  return Object.keys(buildCharacterRoster());
}

function buildConfigOverride() {
  const logline = dom.plotInput.value.trim() || "真千金归来，手撕绿茶假千金和渣男，夺回家族产业。";
  const scene = dom.sceneInput.value.trim() || options.scene[0];
  dom.sceneResult.textContent = scene;

  const config = {
    drama_settings: {
      theme: state.selectedGenre,
      target_audience: "女性向",
      expected_episodes: Number(dom.episodeCount.value)
    },
    logline,
    character_roster: buildCharacterRoster()
  };

  const extraTag = dom.customTagInput.value.trim();
  if (extraTag) {
    config.logline = `${config.logline} 关键词：${extraTag}`;
  }

  return config;
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    method: options.method || "GET",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    body: options.body ? JSON.stringify(options.body) : undefined
  });

  const text = await response.text();
  const payload = text ? JSON.parse(text) : {};

  if (!response.ok) {
    const detail = payload?.detail || response.statusText || "请求失败";
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return payload;
}

function handleMainRoleCardChange(event) {
  const target = event.target;
  const slotName = target.dataset.roleSlot;
  if (!slotName) return;

  const role = getRoleDraftBySlot(slotName);
  if (!role) return;

  if (target.dataset.field === "template") {
    const [group, templateId] = String(target.value).split(":");
    const nextDraft = createRoleDraft(group, templateId, {
      id: role.id,
      slot: role.slot
    });
    replaceRoleDraft(role.id, nextDraft);
    refreshRoleUI();
    return;
  }
}

function handleMainRoleCardInput(event) {
  const target = event.target;
  const slotName = target.dataset.roleSlot;
  if (!slotName) return;

  const role = getRoleDraftBySlot(slotName);
  if (!role) return;

  if (target.dataset.field === "name") {
    updateRoleDraft(role.id, (current) => ({ ...current, name: target.value }));
    updateRoleSummaryText();
    syncRoleOptions(getCurrentRoleNames());
    const roleCard = target.closest(".role-card");
    if (roleCard) {
      const title = roleCard.querySelector("h3");
      if (title) title.textContent = target.value || slotName;
    }
    return;
  }

  if (target.dataset.field === "summary") {
    updateRoleDraft(role.id, (current) => applySummaryToRole(current, target.value));
    const badge = target.closest(".role-card")?.querySelector(".role-badge");
    const nextRole = getRoleDraftBySlot(slotName);
    if (badge && nextRole) {
      badge.textContent = formatRoleBadge(nextRole);
    }
  }
}

function handleRoleDesignerInput(event) {
  const target = event.target;
  const roleId = target.dataset.roleId;
  if (!roleId) return;

  const field = target.dataset.field;
  if (!field || field === "template") return;

  updateRoleDraft(roleId, (current) => {
    const next = { ...current };
    if (field === "appearance_tags" || field === "personality_tags") {
      next[field] = normalizeTagList(target.value);
    } else if (field === "age") {
      next.age = target.value;
    } else {
      next[field] = target.value;
    }
    return next;
  });

  updateRoleSummaryText();
  syncRoleOptions(getCurrentRoleNames());

  const updatedRole = getRoleDraftById(roleId);
  if (updatedRole?.slot) {
    renderMainRoleCards();
  }

  const roleEditor = target.closest(".role-editor");
  if (roleEditor && updatedRole) {
    const title = roleEditor.querySelector("h3");
    const badgeText = roleEditor.querySelector(".role-editor-head p:last-child");
    if (title) title.textContent = updatedRole.name;
    if (badgeText) badgeText.textContent = formatRoleBadge(updatedRole);
  }
}

function handleRoleDesignerChange(event) {
  const target = event.target;
  const roleId = target.dataset.roleId;
  if (!roleId || target.dataset.field !== "template") return;

  if (target.value === "custom") {
    updateRoleDraft(roleId, (current) => ({ ...current, templateId: null }));
    updateRoleSummaryText();
    return;
  }

  const [group, templateId] = String(target.value).split(":");
  const current = getRoleDraftById(roleId);
  if (!current) return;
  const nextDraft = createRoleDraft(group, templateId, {
    id: current.id,
    slot: current.slot
  });
  replaceRoleDraft(roleId, nextDraft);
  refreshRoleUI();
}

function handleRoleDesignerClick(event) {
  const button = event.target.closest("button[data-action='delete-role']");
  if (!button) return;
  const roleId = button.dataset.roleId;
  state.roleDrafts = state.roleDrafts.filter((role) => role.id !== roleId);
  refreshRoleUI();
}

function addPresetRole() {
  const [group, templateId] = String(dom.rolePresetSelect.value || "support:wingwoman").split(":");
  state.roleDrafts = [...state.roleDrafts, createRoleDraft(group, templateId)];
  refreshRoleUI();
}

function addCustomRole() {
  state.roleDrafts = [...state.roleDrafts, createCustomRoleDraft()];
  refreshRoleUI();
}

function syncRoleOptions(roleNames) {
  const resolvedRoles = roleNames?.length ? roleNames : getCurrentRoleNames();
  dom.targetRole.innerHTML = "";

  const sceneOption = document.createElement("option");
  sceneOption.value = "";
  sceneOption.textContent = "整场指令";
  dom.targetRole.appendChild(sceneOption);

  resolvedRoles.forEach((name) => {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name;
    dom.targetRole.appendChild(option);
  });
}

function renderOutline() {
  const episodes = state.plannerOutput?.episodes || [];
  dom.outlineTree.innerHTML = "";

  if (!episodes.length) {
    const li = document.createElement("li");
    li.innerHTML = "<strong>等待大纲</strong><small>点击“生成大纲”后，这里会展示分集规划与角色 directive。</small>";
    dom.outlineTree.appendChild(li);
    dom.outlineStatus.textContent = "还没有可用大纲";
    return;
  }

  dom.outlineStatus.textContent = state.outlineApproved ? "大纲已审核通过，可直接开跑" : "大纲待审核，可先调整再确认";
  episodes.forEach((episode) => {
    const li = document.createElement("li");
    const roles = (episode.scene_roles || []).join(" / ");
    const directives = Object.entries(episode.character_directives || {})
      .map(([name, note]) => `${name}：${note}`)
      .join("；");

    li.innerHTML = `
      <strong>第 ${episode.episode_number} 集 · ${episode.place || "未命名场景"}</strong>
      <small>主线：${episode.global_plot || "无"}</small>
      <small>冲突：${episode.core_conflict || "无"}</small>
      <small>角色：${roles || "无"}</small>
      <small>首位发言：${episode.first_speaker || "无"}</small>
      <small>钩子：${episode.plot_twist_or_hook || "无"}</small>
      <small>Directive：${directives || "无"}</small>
    `;
    dom.outlineTree.appendChild(li);
  });

  syncTopPanelHeights();
}

function formatEventLabel(event) {
  const kindMap = {
    thought: "Inner_Thought",
    action: "Action",
    dialogue: "Dialogue",
    monitor: "Monitor",
    director: "Director",
    system: "System"
  };
  return `${event.speaker || "SYSTEM"} · ${kindMap[event.kind] || event.kind || "Event"}`;
}

function escapeHtml(text) {
  return String(text ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function groupEventsForChat(events) {
  const groups = [];
  const tripleKinds = new Set(["thought", "action", "dialogue"]);
  let i = 0;

  while (i < events.length) {
    const current = events[i];
    const currentKind = current?.kind;
    if (!tripleKinds.has(currentKind)) {
      groups.push({ type: "single", event: current });
      i += 1;
      continue;
    }

    const speaker = current.speaker || "";
    const step = current.step;
    const lines = [];
    let j = i;

    while (j < events.length) {
      const evt = events[j];
      if (!evt || !tripleKinds.has(evt.kind)) break;
      if ((evt.speaker || "") !== speaker) break;
      if (evt.step !== step) break;
      lines.push(evt);
      j += 1;
      if (lines.length >= 3) break;
    }

    if (lines.length > 1) {
      groups.push({
        type: "compound",
        speaker,
        step,
        lines
      });
      i = j;
    } else {
      groups.push({ type: "single", event: current });
      i += 1;
    }
  }

  return groups;
}

function renderMessages() {
  dom.chatFeed.innerHTML = "";
  const events = state.snapshot?.event_log || [];

  if (!events.length) {
    const node = dom.messageTemplate.content.firstElementChild.cloneNode(true);
    node.classList.add("system");
    node.querySelector(".message-role").textContent = "SYSTEM";
    node.querySelector(".message-body").textContent = "这里会按真实 runtime snapshot 展示角色 thought / action / dialogue。";
    dom.chatFeed.appendChild(node);
    return;
  }

  const groups = groupEventsForChat(events);

  groups.forEach((group) => {
    const node = dom.messageTemplate.content.firstElementChild.cloneNode(true);
    const roleEl = node.querySelector(".message-role");
    const bodyEl = node.querySelector(".message-body");

    if (group.type === "compound") {
      node.classList.add("dialogue");
      roleEl.textContent = `${group.speaker || "SYSTEM"} · Turn ${group.step ?? "-"}`;
      bodyEl.classList.add("compact");

      const orderMap = { thought: 0, action: 1, dialogue: 2 };
      const labelMap = {
        thought: "Inner_Thought",
        action: "Action",
        dialogue: "Dialogue"
      };
      const sortedLines = [...group.lines].sort((a, b) => (orderMap[a.kind] ?? 99) - (orderMap[b.kind] ?? 99));
      bodyEl.innerHTML = sortedLines
        .map((line) => `
          <div class="compound-line">
            <span class="compound-label">${labelMap[line.kind] || line.kind}</span>
            <span class="compound-text">${escapeHtml(line.content || "")}</span>
          </div>
        `)
        .join("");
    } else {
      const event = group.event;
      node.classList.add(event.kind || "system");
      roleEl.textContent = formatEventLabel(event);
      bodyEl.textContent = event.content || "";
    }

    dom.chatFeed.appendChild(node);
  });

  dom.chatFeed.scrollTop = dom.chatFeed.scrollHeight;
}

function renderMonitorFeed() {
  dom.monitorFeed.innerHTML = "";

  const notes = [];
  const turnTrace = state.snapshot?.turn_trace || [];
  const eventLog = state.snapshot?.event_log || [];
  const softTurnLimit = state.snapshot?.soft_turn_limit;
  const hardTurnLimit = state.snapshot?.hard_turn_limit;
  const beatState = state.snapshot?.beat_state;

  if (typeof softTurnLimit === "number") {
    const hardText = hardTurnLimit == null ? "无硬截断" : `硬上限 ${hardTurnLimit}`;
    notes.push(`节奏控制：软目标 ${softTurnLimit}，${hardText}`);
  }
  if (beatState?.beats?.length) {
    const beat = beatState.beats[Math.min(Math.max(beatState.active_index ?? 0, 0), beatState.beats.length - 1)];
    if (beat) {
      notes.push(`当前 Beat：${beat.label}（需落点：${beat.must_land || "未设定"}）`);
    }
  }

  eventLog
    .filter((event) => ["monitor", "director", "system"].includes(event.kind))
    .slice(-6)
    .forEach((event) => {
      notes.push(`${formatEventLabel(event)}：${event.content}`);
    });

  turnTrace.slice(-4).forEach((item) => {
    const nextSpeaker = Array.isArray(item.resolved_next_speaker)
      ? item.resolved_next_speaker.join(", ")
      : item.resolved_next_speaker || "无";
    notes.push(`路由追踪：第 ${item.step} 句由 ${item.speaker} 发起，状态 ${item.status}，下一位 ${nextSpeaker}`);
  });

  if (!notes.length) {
    notes.push("监制观察会显示 monitor event、director command 与最近几轮的路由状态。");
  }

  notes.forEach((note) => {
    const li = document.createElement("li");
    li.textContent = note;
    dom.monitorFeed.appendChild(li);
  });
}

function getCurrentEpisodeNumber(snapshot) {
  if (!snapshot) return 1;
  const fromPlan = Number(snapshot?.episode_plan?.episode_number);
  if (Number.isInteger(fromPlan) && fromPlan > 0) return fromPlan;
  const fromResult = Number(snapshot?.result?.runtime_state?.story?.current_episode);
  if (Number.isInteger(fromResult) && fromResult > 0) return fromResult;
  return 1;
}

function updateNextEpisodeButton() {
  if (!dom.nextEpisodeBtn) return;
  const episodes = state.plannerOutput?.episodes || [];
  const totalEpisodes = Array.isArray(episodes) ? episodes.length : 0;
  const currentEpisode = getCurrentEpisodeNumber(state.snapshot);
  const canStartNext = Boolean(state.snapshot?.result) && currentEpisode < totalEpisodes;
  dom.nextEpisodeBtn.classList.toggle("hidden", !canStartNext);
  dom.nextEpisodeBtn.disabled = !canStartNext;
}

function applySnapshot(snapshot) {
  state.snapshot = snapshot || null;
  if (snapshot?.planner_output) {
    state.plannerOutput = snapshot.planner_output;
  }
  if (typeof snapshot?.outline_approved === "boolean") {
    state.outlineApproved = snapshot.outline_approved;
  }
  if (snapshot?.session_id) {
    state.sessionId = snapshot.session_id;
  }
  if (snapshot?.role_names) {
    syncRoleOptions(snapshot.role_names);
  }

  const currentTurn = snapshot?.current_turn ?? 0;
  dom.turnBadge.textContent = `第 ${currentTurn} 句`;
  dom.timelineSlider.max = String(currentTurn);
  if (Number(dom.timelineSlider.value) > currentTurn) {
    dom.timelineSlider.value = String(currentTurn);
  }
  updateTimelineDisplay();

  renderOutline();
  renderMessages();
  renderMonitorFeed();
  updateNextEpisodeButton();
}

function resetSessionState() {
  state.sessionId = null;
  state.plannerOutput = null;
  state.outlineApproved = false;
  state.snapshot = null;
  state.shouldContinue = false;
  state.isLooping = false;
  dom.sessionBadge.textContent = "未创建";
  setStatus("待机中");
  dom.outlineStatus.textContent = "还没有可用大纲";
  dom.scriptOutput.textContent = "还没有导出结果。先生成大纲并跑完一轮推演。";
  setApiPreview("当前还没有 session。", "等待请求...");
  renderOutline();
  renderMessages();
  renderMonitorFeed();
  updateNextEpisodeButton();
  dom.timelineSlider.max = "0";
  dom.timelineSlider.value = "0";
  updateTimelineDisplay();
  dom.turnBadge.textContent = "第 0 句";
}

async function createSession(force = false) {
  if (state.sessionId && !force) {
    return state.sessionId;
  }

  const configOverride = buildConfigOverride();

  if (state.runMode === "free") {
    const payload = await request("/sessions/free", {
      method: "POST",
      body: {
        config_override: configOverride,
        opening_scene: dom.sceneInput.value.trim(),
        scene_roles: Object.keys(configOverride.character_roster),
        story_hook: dom.plotInput.value.trim()
      }
    });
    state.sessionId = payload.session_id;
    state.plannerOutput = payload.planner_output;
    state.outlineApproved = true;
    dom.sessionBadge.textContent = payload.session_id;
    setStatus("free session 已创建");
    renderOutline();
    setApiPreview("已创建 free session。", payload);
    return payload.session_id;
  }

  const payload = await request("/sessions/planned", {
    method: "POST",
    body: {
      config_override: configOverride
    }
  });

  state.sessionId = payload.session_id;
  state.plannerOutput = null;
  state.outlineApproved = false;
  dom.sessionBadge.textContent = payload.session_id;
  setStatus("planned session 已创建");
  setApiPreview("已创建 planned session。", payload);
  return payload.session_id;
}

async function generateOutline() {
  if (state.runMode === "free") {
    await createSession(true);
    renderOutline();
    setStatus("free 模式已生成最小 episode plan");
    return;
  }

  const sessionId = await createSession(true);
  const payload = await request(`/sessions/${sessionId}/outline/generate`, {
    method: "POST"
  });
  const episodes = payload?.planner_output?.episodes;
  if (!Array.isArray(episodes) || episodes.length === 0) {
    state.plannerOutput = null;
    state.outlineApproved = false;
    renderOutline();
    setStatus("大纲生成失败");
    setApiPreview("outline 生成失败", payload);
    return;
  }
  state.plannerOutput = payload.planner_output;
  state.outlineApproved = false;
  renderOutline();
  setStatus("大纲已生成，等待审核");
  setApiPreview("planner_output 已生成。", payload);
}

async function reviewOutline() {
  if (state.runMode === "free") {
    setStatus("free 模式不需要大纲审稿，可直接开跑");
    return;
  }
  if (!state.sessionId) {
    await generateOutline();
  }
  const feedback = dom.outlineFeedback.value.trim();
  if (!feedback) {
    setStatus("先写一条审稿意见");
    return;
  }
  const payload = await request(`/sessions/${state.sessionId}/outline/review`, {
    method: "POST",
    body: { feedback }
  });
  state.plannerOutput = payload.planner_output;
  state.outlineApproved = false;
  renderOutline();
  setStatus("大纲已按审稿意见重生成");
  setApiPreview("大纲 review 完成。", payload);
}

async function approveOutline() {
  if (state.runMode === "free") {
    state.outlineApproved = true;
    setStatus("free 模式默认已批准");
    return;
  }
  if (!state.sessionId || !state.plannerOutput) {
    await generateOutline();
  }
  const payload = await request(`/sessions/${state.sessionId}/outline/approve`, {
    method: "POST"
  });
  state.plannerOutput = payload.planner_output;
  state.outlineApproved = true;
  renderOutline();
  setStatus("大纲已审核通过");
  setApiPreview("大纲已审核通过。", payload);
}

async function startEpisode() {
  if (state.runMode === "planned") {
    if (!state.plannerOutput) {
      await generateOutline();
    }
    if (!state.outlineApproved) {
      await approveOutline();
    }
  } else if (!state.sessionId) {
    await createSession(true);
  }

  const payload = await request(`/sessions/${state.sessionId}/episode/start`, {
    method: "POST",
    body: {
      episode: 1
    }
  });

  applySnapshot(payload);
  setStatus("runtime 已启动");
  setApiPreview("episode runtime 已创建。", payload);
}

async function stepEpisode() {
  const payload = await request(`/sessions/${state.sessionId}/episode/step`, {
    method: "POST"
  });
  applySnapshot(payload.snapshot);
  setApiPreview("推进了一轮 episode step。", payload);

  const stepStatus = payload.step_result?.status;
  if (state.snapshot?.result) {
    const statusMap = {
      ended: "剧情自然收束",
      director_cut: "导演切断",
      max_turns_reached: "达到轮数预算",
      handoff: "路由移交",
      api_error: "模型调用失败",
      format_error: "模型格式错误",
      key_error: "模型字段错误"
    };
    const resolved = statusMap[state.snapshot.result.status] || state.snapshot.result.status;
    setStatus(`已结束：${resolved}`);
    state.shouldContinue = false;
  } else if (stepStatus === "paused") {
    setStatus("已暂停");
    state.shouldContinue = false;
  } else {
    setStatus(`进行中：第 ${state.snapshot?.current_turn ?? 0} 句`);
  }
}

async function driveEpisodeLoop() {
  if (state.isLooping || !state.sessionId) {
    return;
  }

  state.isLooping = true;
  try {
    while (state.shouldContinue) {
      await stepEpisode();
      if (!state.shouldContinue || state.snapshot?.result || state.snapshot?.episode_status === "paused") {
        break;
      }
      await new Promise((resolve) => setTimeout(resolve, 400));
    }
  } finally {
    state.isLooping = false;
  }
}

async function quickStart() {
  try {
    await startEpisode();
    state.shouldContinue = true;
    await driveEpisodeLoop();
  } catch (error) {
    state.shouldContinue = false;
    setStatus("启动失败");
    setApiPreview("启动推演失败。", { error: error.message });
  }
}

async function continueScene() {
  try {
    if (!state.sessionId || !state.snapshot) {
      await quickStart();
      return;
    }

    if (state.snapshot.episode_status === "paused") {
      const payload = await request(`/sessions/${state.sessionId}/director`, {
        method: "POST",
        body: { command: "resume" }
      });
      applySnapshot(payload.snapshot);
      setApiPreview("已恢复 episode runtime。", payload);
    }

    state.shouldContinue = true;
    await driveEpisodeLoop();
  } catch (error) {
    setStatus("继续失败");
    setApiPreview("继续推演失败。", { error: error.message });
  }
}

async function startNextEpisode() {
  try {
    if (!state.sessionId || !state.snapshot || !state.plannerOutput?.episodes?.length) {
      setStatus("先完成当前集初始化");
      return;
    }
    const currentEpisode = getCurrentEpisodeNumber(state.snapshot);
    const nextEpisode = currentEpisode + 1;
    if (nextEpisode > state.plannerOutput.episodes.length) {
      setStatus("已是最后一集");
      return;
    }

    const payload = await request(`/sessions/${state.sessionId}/episode/start`, {
      method: "POST",
      body: { episode: nextEpisode }
    });
    applySnapshot(payload);
    setStatus(`已开始第 ${nextEpisode} 集`);
    setApiPreview("已切换到下一集", payload);
  } catch (error) {
    setApiPreview("启动下一集失败。", { error: error.message });
  }
}

async function cutScene() {
  if (!state.sessionId || !state.snapshot) {
    setStatus("还没有运行中的场景");
    return;
  }
  try {
    state.shouldContinue = false;
    const payload = await request(`/sessions/${state.sessionId}/director`, {
      method: "POST",
      body: { command: "cut" }
    });
    applySnapshot(payload.snapshot);
    setStatus("导演已 Cut 当前场景");
    setApiPreview("已执行 cut 指令。", payload);
  } catch (error) {
    setApiPreview("cut 指令失败。", { error: error.message });
  }
}

async function sendDirective() {
  if (!state.sessionId || !state.snapshot) {
    setStatus("先启动一轮推演");
    return;
  }
  const instruction = dom.directorCommand.value.trim();
  if (!instruction) {
    setStatus("先写导演指令");
    return;
  }
  try {
    const payload = await request(`/sessions/${state.sessionId}/director`, {
      method: "POST",
      body: {
        command: "inject_instruction",
        instruction,
        target_role: dom.targetRole.value || null
      }
    });
    applySnapshot(payload.snapshot);
    setStatus("导演指令已写入下一轮 prompt");
    setApiPreview("已注入导演指令。", payload);
  } catch (error) {
    setApiPreview("注入导演指令失败。", { error: error.message });
  }
}

async function rollbackScene() {
  if (!state.sessionId || !state.snapshot) {
    setStatus("还没有可回档的 runtime");
    return;
  }
  try {
    state.shouldContinue = false;
    const payload = await request(`/sessions/${state.sessionId}/director`, {
      method: "POST",
      body: {
        command: "rollback",
        step: Number(dom.timelineSlider.value)
      }
    });
    applySnapshot(payload.snapshot);
    setStatus(`已回档到第 ${dom.timelineSlider.value} 句`);
    setApiPreview("已执行 rollback。", payload);
  } catch (error) {
    setApiPreview("rollback 失败。", { error: error.message });
  }
}

async function exportArtifacts() {
  if (!state.sessionId) {
    setStatus("还没有 session");
    return;
  }
  try {
    const payload = await request(`/sessions/${state.sessionId}/export`, {
      method: "POST"
    });
    dom.scriptOutput.textContent = payload.script || "没有 script 输出。";
    setApiPreview("导出 artifacts 成功。", payload.shotlist || payload);
    setStatus("已导出台本与分镜");
  } catch (error) {
    setApiPreview("导出失败。", { error: error.message });
  }
}

function previewCurrentState() {
  setApiPreview("当前前端状态快照。", {
    sessionId: state.sessionId,
    runMode: state.runMode,
    outlineApproved: state.outlineApproved,
    plannerOutput: state.plannerOutput,
    snapshot: state.snapshot
  });
}

async function refreshStage() {
  if (!state.snapshot) {
    renderMessages();
    renderMonitorFeed();
    return;
  }
  applySnapshot(state.snapshot);
  setStatus("已刷新当前快照");
}

dom.randomizeAll = document.querySelector("#randomizeAll");
document.querySelector("#randomizeAll").addEventListener("click", randomizeAll);
document.querySelector("#optimizeInput").addEventListener("click", optimizeInput);
document.querySelector("#episodeCount").addEventListener("input", updateEpisodeCountDisplay);
document.querySelector("#roundLimit").addEventListener("input", updateRoundDisplay);
document.querySelector("#timelineSlider").addEventListener("input", updateTimelineDisplay);
dom.mainRoleCards.addEventListener("change", handleMainRoleCardChange);
dom.mainRoleCards.addEventListener("input", handleMainRoleCardInput);
dom.openRoleDesignerBtn.addEventListener("click", openRoleDesigner);
dom.closeRoleDesignerBtn.addEventListener("click", closeRoleDesigner);
dom.roleDesignerModal.addEventListener("click", (event) => {
  if (event.target instanceof HTMLElement && event.target.dataset.closeRoleModal === "true") {
    closeRoleDesigner();
  }
});
dom.addPresetRoleBtn.addEventListener("click", addPresetRole);
dom.addCustomRoleBtn.addEventListener("click", addCustomRole);
dom.roleDesignerList.addEventListener("input", handleRoleDesignerInput);
dom.roleDesignerList.addEventListener("change", handleRoleDesignerChange);
dom.roleDesignerList.addEventListener("click", handleRoleDesignerClick);
document.querySelector("#generateOutlineBtn").addEventListener("click", () => generateOutline().catch((error) => setApiPreview("生成大纲失败。", { error: error.message })));
document.querySelector("#reviewOutlineBtn").addEventListener("click", () => reviewOutline().catch((error) => setApiPreview("审稿失败。", { error: error.message })));
document.querySelector("#approveOutlineBtn").addEventListener("click", () => approveOutline().catch((error) => setApiPreview("审核通过失败。", { error: error.message })));
document.querySelector("#buildFreePlanBtn").addEventListener("click", () => {
  state.runMode = "free";
  dom.runModeResult.textContent = "自由开场";
  dom.modeBadge.textContent = "自由开场";
  renderAllChips();
  generateOutline().catch((error) => setApiPreview("生成最小 episode plan 失败。", { error: error.message }));
});
document.querySelector("#startDemo").addEventListener("click", quickStart);
document.querySelector("#continueScene").addEventListener("click", continueScene);
document.querySelector("#nextEpisodeBtn").addEventListener("click", startNextEpisode);
document.querySelector("#cutScene").addEventListener("click", cutScene);
document.querySelector("#sendDirective").addEventListener("click", sendDirective);
document.querySelector("#rollbackBtn").addEventListener("click", rollbackScene);
document.querySelector("#formatScript").addEventListener("click", exportArtifacts);
document.querySelector("#previewStateBtn").addEventListener("click", previewCurrentState);
document.querySelector("#refreshStageBtn").addEventListener("click", refreshStage);
document.querySelector("#resetSessionBtn").addEventListener("click", resetSessionState);
window.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && state.roleDesignerOpen) {
    closeRoleDesigner();
  }
});

initializeDefaults();
resetSessionState();
window.addEventListener("resize", syncTopPanelHeights);
window.addEventListener("load", captureInitialTopPanelHeight);