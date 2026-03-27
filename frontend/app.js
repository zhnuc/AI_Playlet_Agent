const {
  options,
  roleTemplateCatalog,
  rolePositionCatalog,
  rolePositionMap,
  defaultRolePositionByGroup,
  starterRoleDefinitions,
  allRoleTemplateGroups,
  roleGroupLabels,
  promptMap
} = window.PLAYLET_CONFIG;

const state = {
  selectedGenre: options.genre[0],
  runMode: "planned",
  sessionId: null,
  plannerOutput: null,
  outlineApproved: false,
  snapshot: null,
  shouldContinue: false,
  isLooping: false,
  roleDrafts: [],
  roleCounter: 1,
  roleDesignerOpen: false,
  hasOpenedRoleDesignerOnce: true,
  showInitialRoleHints: true,
  currentStage: 1,
  hasExportedArtifacts: false,
  hasTriggeredStartDemo: false,
  loadingDepth: 0
};

const dom = {
  workspaceGrid: document.querySelector(".workspace-grid"),
  stageSteps: Array.from(document.querySelectorAll(".stage-step")),
  stagePrevBtn: document.querySelector("#stagePrevBtn"),
  stageNextBtn: document.querySelector("#stageNextBtn"),
  stageHint: document.querySelector("#stageHint"),
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
  backgroundSetupCard: document.querySelector("#backgroundSetupCard"),
  roleSetupCard: document.querySelector("#roleSetupCard"),
  plotInput: document.querySelector("#plotInput"),
  sceneInput: document.querySelector("#sceneInput"),
  roleEntryHint: document.querySelector("#roleEntryHint"),
  roleComposerDisplay: document.querySelector("#roleComposerDisplay"),
  mainRoleCards: document.querySelector("#mainRoleCards"),
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
  startDemoBtn: document.querySelector("#startDemo"),
  runToggleBtn: document.querySelector("#runToggleBtn"),
  nextEpisodeBtn: document.querySelector("#nextEpisodeBtn"),
  outlineFeedback: document.querySelector("#outlineFeedback"),
  directorCommand: document.querySelector("#directorCommand"),
  targetRole: document.querySelector("#targetRole"),
  scriptOutput: document.querySelector("#scriptOutput"),
  apiSnippet: document.querySelector("#apiSnippet"),
  apiHint: document.querySelector("#apiHint"),
  messageTemplate: document.querySelector("#messageTemplate"),
  loadingMask: document.querySelector("#loadingMask"),
  loadingTitle: document.querySelector("#loadingTitle"),
  loadingHint: document.querySelector("#loadingHint"),
  loadingTips: document.querySelector("#loadingTips"),
  configSetupModal: document.querySelector("#configSetupModal"),
  configSetupHint: document.querySelector("#configSetupHint"),
  configBaseUrlInput: document.querySelector("#configBaseUrlInput"),
  configApiKeyInput: document.querySelector("#configApiKeyInput"),
  configModelInput: document.querySelector("#configModelInput"),
  saveConfigBtn: document.querySelector("#saveConfigBtn")
};

const stagePanels = {
  1: [".inspiration-panel"],
  2: [".outline-panel"],
  3: [".sandbox-panel", ".control-panel", ".monitor-panel"],
  4: [".output-panel"]
};

const stageHints = {
  1: "阶段 1：先完成输入配置与角色设定。",
  2: "阶段 2：生成并确认大纲结构。",
  3: "阶段 3：推进演绎并执行导演控制。",
  4: "阶段 4：查看并导出台本与分镜。"
};

function isStage1Ready() {
  return state.roleDrafts.length > 0 && Boolean(dom.plotInput.value.trim());
}

function isStage2Ready() {
  if (state.runMode === "free") {
    return Boolean(state.sessionId && state.plannerOutput?.episodes?.length);
  }
  return Boolean(state.outlineApproved);
}

function isStage3Ready() {
  return Boolean(state.snapshot || state.hasExportedArtifacts);
}

function stageBlockReason(targetStage) {
  if (targetStage <= 1) return "";
  if (targetStage >= 2 && !isStage1Ready()) {
    return "先完成阶段 1 的基础输入。";
  }
  if (targetStage >= 3 && !isStage2Ready()) {
    return state.runMode === "planned"
      ? "先完成大纲审核通过，再进入阶段 3。"
      : "先生成 free 开场，再进入阶段 3。";
  }
  if (targetStage >= 4 && !isStage3Ready()) {
    return "先完成至少一轮推演，再进入阶段 4。";
  }
  return "";
}

function canEnterStage(targetStage) {
  return !stageBlockReason(targetStage);
}

function syncStagePanels() {
  if (!dom.workspaceGrid) return;
  dom.workspaceGrid.classList.add("stage-focus");
  dom.workspaceGrid.classList.toggle("stage-focus-3", state.currentStage === 3);
  const panels = Array.from(dom.workspaceGrid.querySelectorAll(".panel"));
  panels.forEach((panel) => panel.classList.add("stage-hidden"));
  (stagePanels[state.currentStage] || []).forEach((selector) => {
    const panel = dom.workspaceGrid.querySelector(selector);
    if (panel) panel.classList.remove("stage-hidden");
  });
}

function syncStageNav() {
  const maxStage = 4;
  if (dom.stageHint) {
    dom.stageHint.textContent = stageHints[state.currentStage] || "";
  }
  if (dom.stagePrevBtn) {
    dom.stagePrevBtn.disabled = state.currentStage <= 1;
  }
  if (dom.stageNextBtn) {
    dom.stageNextBtn.disabled = state.currentStage >= maxStage;
    dom.stageNextBtn.textContent = state.currentStage >= maxStage ? "已到最后阶段" : "下一步";
  }

  dom.stageSteps.forEach((button) => {
    const target = Number(button.dataset.stageTarget || "1");
    const active = target === state.currentStage;
    const done = target < state.currentStage;
    const locked = !canEnterStage(target);
    button.classList.toggle("active", active);
    button.classList.toggle("done", done);
    button.classList.toggle("locked", locked);
    button.disabled = locked;
    button.setAttribute("aria-current", active ? "step" : "false");
  });
}

function setStage(targetStage, options = {}) {
  const stage = Math.min(4, Math.max(1, Number(targetStage) || 1));
  const blockReason = stageBlockReason(stage);
  if (blockReason && !options.force) {
    setStatus(blockReason);
    return false;
  }
  state.currentStage = stage;
  syncStagePanels();
  syncStageNav();
  if (typeof window.__onStageChanged === "function") {
    Promise.resolve(window.__onStageChanged(stage)).catch(() => {});
  }
  requestAnimationFrame(syncTopPanelHeights);
  return true;
}

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

function getRolePositionMeta(position) {
  return rolePositionMap[position] || rolePositionMap.supporting;
}

function inferRoleTypeFromPosition(position) {
  return getRolePositionMeta(position).type;
}

function inferGenderFromPosition(position, gender) {
  const meta = getRolePositionMeta(position);
  return meta.lockedGender || gender || "未设定";
}

function normalizeRoleDraft(role) {
  const resolvedPosition = getRolePositionMeta(role.role_position).value;
  return {
    ...role,
    role_position: resolvedPosition,
    role_type: inferRoleTypeFromPosition(resolvedPosition),
    gender: inferGenderFromPosition(resolvedPosition, role.gender)
  };
}

function sortRolesByImportance(roles) {
  return [...roles].sort((left, right) => {
    const priorityDiff = getRolePositionMeta(left.role_position).priority - getRolePositionMeta(right.role_position).priority;
    if (priorityDiff !== 0) return priorityDiff;
    return state.roleDrafts.findIndex((item) => item.id === left.id) - state.roleDrafts.findIndex((item) => item.id === right.id);
  });
}

function buildRoleTemplateHint(role) {
  const summary = buildRoleSummary(role);
  return `${role.name} · ${getRolePositionMeta(role.role_position).label} · ${summary || "保留默认设定"}`;
}

function buildRolePositionOptions(role) {
  const enabledOptions = [];
  const disabledOptions = [];

  rolePositionCatalog.forEach((position) => {
    const selected = role.role_position === position.value ? " selected" : "";
    const occupied = position.unique && state.roleDrafts.some((item) => item.id !== role.id && item.role_position === position.value);
    const disabled = occupied && !selected ? " disabled" : "";
    const optionHtml = `<option value="${position.value}"${selected}${disabled}>${escapeMarkup(position.label)}${occupied && !selected ? "（已占用）" : ""}</option>`;
    if (occupied && !selected) {
      disabledOptions.push(optionHtml);
    } else {
      enabledOptions.push(optionHtml);
    }
  });

  return [...enabledOptions, ...disabledOptions].join("");
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
  return normalizeRoleDraft({
    id: overrides.id || nextRoleId(),
    isStarter: Boolean(overrides.isStarter),
    ...cloneTemplateDraft(group, templateId),
    ...overrides,
    templateGroup: group,
    templateId,
    role_position: overrides.role_position || defaultRolePositionByGroup[group] || "supporting"
  });
}

function createCustomRoleDraft() {
  return normalizeRoleDraft({
    id: nextRoleId(),
    isStarter: false,
    templateGroup: "support",
    templateId: null,
    name: `新角色${state.roleDrafts.length + 1}`,
    role_type: "配角",
    role_position: "supporting",
    gender: "未设定",
    age: 24,
    identity: "待设定身份",
    appearance_tags: ["待补充"],
    personality_tags: ["待补充"]
  });
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
  return [role.identity, ...personality].filter(Boolean).join("，");
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
  if (parts.length >= 2) {
    next.personality_tags = parts.slice(1).slice(0, 3);
  }
  return next;
}

function formatRoleBadge(role) {
  const chunks = [getRolePositionMeta(role.role_position).label, inferRoleTypeFromPosition(role.role_position), inferGenderFromPosition(role.role_position, role.gender)];
  if (role.age) {
    chunks.push(`${role.age} 岁`);
  }
  return chunks.join(" · ");
}

function formatRoleCardBadge(role) {
  const chunks = [inferGenderFromPosition(role.role_position, role.gender)];
  if (role.age) {
    chunks.push(`${role.age} 岁`);
  }
  return chunks.join(" · ");
}

function initializeRoleDrafts() {
  state.roleDrafts = [];
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
  dom.rolePresetSelect.innerHTML = allRoleTemplateGroups
    .map((group) => {
      const optionsHtml = roleTemplateCatalog[group]
        .map((template) => `<option value="${group}:${template.id}">${escapeMarkup(template.label)}</option>`)
        .join("");
      return `<optgroup label="${escapeMarkup(roleGroupLabels[group])}">${optionsHtml}</optgroup>`;
    })
    .join("");
}

function updateRoleSummaryText() {
  const counts = state.roleDrafts.reduce(
    (acc, role) => {
      const key = inferRoleTypeFromPosition(role.role_position);
      acc[key] = (acc[key] || 0) + 1;
      return acc;
    },
    {}
  );
  dom.roleDesignerStats.textContent = `已配置 ${state.roleDrafts.length} 个角色。男一、女一、男二、女二和大反派各只能存在 1 位；不可选项会自动灰置并沉到列表底部。`;
}

function renderMainRoleCards() {
  const visibleRoles = sortRolesByImportance(state.roleDrafts)
    .filter((role) => getRolePositionMeta(role.role_position).priority < 99)
    .slice(0, 3);

  if (!visibleRoles.length) {
    dom.mainRoleCards.innerHTML = '<div class="main-role-empty">当前还没有被识别为核心展示位的角色。先在角色设计器中设置男一、女一、大反派或二番位。</div>';
    return;
  }

  dom.mainRoleCards.innerHTML = visibleRoles
    .map((role, index) => `
      <article class="role-card" data-role-id="${role.id}">
        <div class="role-card-topline">
          <p class="prompt-title">核心角色 ${index + 1}</p>
          <span class="role-position-pill">${escapeMarkup(getRolePositionMeta(role.role_position).label)}</span>
        </div>
        <div class="role-card-head">
          <div class="role-card-title-block">
            <h3 class="role-card-name">${escapeMarkup(role.name || `角色${index + 1}`)}</h3>
          </div>
          <span class="role-badge">${escapeMarkup(formatRoleCardBadge(role))}</span>
        </div>
        <p class="role-summary-preview">${escapeMarkup(buildRoleSummary(role) || "还没有角色速写，请在角色设计器中补充身份与性格。")}</p>
      </article>
    `)
    .join("");
}

function renderRoleDesignerList() {
  dom.roleDesignerList.innerHTML = state.roleDrafts
    .map((role) => {
      const templateOptions = `${buildTemplateOptions(allRoleTemplateGroups, getCurrentRoleTemplateValue(role))}<option value="custom"${role.templateId ? "" : " selected"}>保留当前自定义设定</option>`;
      const positionMeta = getRolePositionMeta(role.role_position);
      const lockedGender = Boolean(positionMeta.lockedGender);
      const templateHint = state.showInitialRoleHints && role.isStarter
        ? `<p class="role-template-hint">默认模板参考：${escapeMarkup(buildRoleTemplateHint(role))}。如果现在直接关闭设计器，这套默认信息会作为真实角色保留。</p>`
        : "";
      return `
        <article class="role-editor" data-role-id="${role.id}">
          <div class="role-editor-head">
            <div>
              <p class="prompt-title">${escapeMarkup(positionMeta.label)}</p>
              <h3>${escapeMarkup(role.name)}</h3>
              <p>${escapeMarkup(formatRoleBadge(role))}</p>
            </div>
            <button class="danger-btn small" type="button" data-action="delete-role" data-role-id="${role.id}">删除角色</button>
          </div>
          ${templateHint}
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
              <select data-role-id="${role.id}" data-field="role_position">
                ${buildRolePositionOptions(role)}
              </select>
              <p class="role-position-note">男一、女一、男二、女二和大反派只能存在 1 位。已占用的席位会自动灰置并移动到下方。</p>
            </label>
            <label>
              性别
              <select data-role-id="${role.id}" data-field="gender"${lockedGender ? " disabled" : ""}>
                <option value="女"${inferGenderFromPosition(role.role_position, role.gender) === "女" ? " selected" : ""}>女</option>
                <option value="男"${inferGenderFromPosition(role.role_position, role.gender) === "男" ? " selected" : ""}>男</option>
                <option value="未设定"${inferGenderFromPosition(role.role_position, role.gender) === "未设定" ? " selected" : ""}>未设定</option>
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
          </div>
        </article>
      `;
    })
    .join("");
}

function openRoleDesigner() {
  state.roleDesignerOpen = true;
  state.hasOpenedRoleDesignerOnce = true;
  dom.roleDesignerModal.classList.remove("hidden");
  dom.roleDesignerModal.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
  dom.roleComposerDisplay.classList.remove("hidden");
  renderMainRoleCards();
  renderRoleDesignerList();
  requestAnimationFrame(syncTopPanelHeights);
}

function closeRoleDesigner() {
  state.roleDesignerOpen = false;
  state.showInitialRoleHints = false;
  dom.roleDesignerModal.classList.add("hidden");
  dom.roleDesignerModal.setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-open");
  requestAnimationFrame(syncTopPanelHeights);
}

function refreshRoleUI(options = {}) {
  updateRoleSummaryText();
  syncRoleOptions(getCurrentRoleNames());
  dom.roleEntryHint.classList.add("hidden");
  dom.roleComposerDisplay.classList.remove("hidden");
  if (!options.skipMainCards) {
    renderMainRoleCards();
  }
  if (state.roleDesignerOpen && !options.skipDesignerList) {
    renderRoleDesignerList();
  }
  requestAnimationFrame(syncTopPanelHeights);
}

function syncTopPanelHeights() {
  const inspirationPanel = dom.inspirationPanel;
  const outlinePanel = dom.outlinePanel;
  if (!inspirationPanel || !outlinePanel) return;

  const targetHeight = inspirationPanel.offsetHeight;
  if (targetHeight > 0) {
    outlinePanel.style.height = `${targetHeight}px`;
  }
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
  dom.roleComposerDisplay.classList.remove("hidden");
  renderMainRoleCards();
  updateEpisodeCountDisplay();
  updateRoundDisplay();
  updateRoleSummaryText();
  syncRoleOptions(getCurrentRoleNames());
  renderAllChips();
  syncStageNav();
  renderOutline();
  renderMessages();
  renderMonitorFeed();
  requestAnimationFrame(syncTopPanelHeights);
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
      syncStageNav();
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
  const roleSetupVisible = dom.roleSetupCard && !dom.roleSetupCard.classList.contains("hidden");
  if (roleSetupVisible) {
    if (!state.roleDrafts.length) {
      initializeRoleDrafts();
    }
    state.roleDrafts = state.roleDrafts.map((role) => {
      const group = roleTemplateCatalog[role.templateGroup] ? role.templateGroup : "support";
      const list = roleTemplateCatalog[group] || [];
      if (!list.length) return role;
      const picked = sample(list);
      return createRoleDraft(group, picked.id, {
        id: role.id,
        isStarter: role.isStarter,
        role_position: role.role_position
      });
    });
    refreshRoleUI();
    setStatus("已随机刷新角色卡");
    return;
  }

  const genre = sample(options.genre);
  const scene = sample(options.scene);
  state.selectedGenre = genre;
  dom.genreResult.textContent = genre;
  dom.sceneResult.textContent = scene;
  dom.sceneInput.value = scene;
  dom.plotInput.value = `围绕“${genre}”展开，开场直接爆发公开冲突，并在结尾抛出能钩住下一场的关键证据。`;
  dom.promptPreview.textContent = promptMap[genre] || promptMap[options.genre[0]];
  renderAllChips();
  setStatus("已随机选择基础设定");
}

function optimizeInput() {
  randomizeAll();
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

function showLoading(options = {}) {
  if (!dom.loadingMask) return;
  state.loadingDepth += 1;
  const title = String(options.title || "正在处理，请稍等几分钟");
  const hint = String(options.hint || "大纲生成和导演指令需要调用模型，通常会有一点等待时间。");
  const tips = Array.isArray(options.tips) && options.tips.length
    ? options.tips
    : [
        "你可以先看下角色卡，回来结果会自动更新。",
        "通常几十秒到几分钟完成，取决于当前任务复杂度。",
        "如果等待较久，可先暂停当前操作再试一次。"
      ];

  if (dom.loadingTitle) dom.loadingTitle.textContent = title;
  if (dom.loadingHint) dom.loadingHint.textContent = hint;
  if (dom.loadingTips) {
    const tip = tips[Math.floor(Math.random() * tips.length)];
    dom.loadingTips.textContent = tip;
  }

  dom.loadingMask.classList.remove("hidden");
  dom.loadingMask.setAttribute("aria-busy", "true");
}

function hideLoading() {
  if (!dom.loadingMask) return;
  state.loadingDepth = Math.max(0, state.loadingDepth - 1);
  if (state.loadingDepth > 0) return;
  dom.loadingMask.classList.add("hidden");
  dom.loadingMask.setAttribute("aria-busy", "false");
}

function openConfigSetupModal(hintText) {
  if (!dom.configSetupModal) return;
  if (dom.configSetupHint && hintText) {
    dom.configSetupHint.textContent = hintText;
  }
  dom.configSetupModal.classList.remove("hidden");
  dom.configSetupModal.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
}

function closeConfigSetupModal() {
  if (!dom.configSetupModal) return;
  dom.configSetupModal.classList.add("hidden");
  dom.configSetupModal.setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-open");
}

async function requestJson(path, options = {}) {
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
    const detail = payload?.detail || response.statusText || "Request failed";
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return payload;
}

async function ensureApiConfig() {
  try {
    const status = await requestJson("/config/status");
    if (!status?.needs_setup) {
      closeConfigSetupModal();
      return;
    }
    openConfigSetupModal("检测到缺少 .env 或关键字段（base_url / api_key / model），请先完成配置。");
    setStatus("请先完成 API 配置");
  } catch (error) {
    openConfigSetupModal(`无法读取配置状态：${error.message}`);
    setStatus("配置检查失败，请手动填写后继续");
  }
}

async function saveApiConfigFromModal() {
  const base_url = String(dom.configBaseUrlInput?.value || "").trim();
  const api_key = String(dom.configApiKeyInput?.value || "").trim();
  const model = String(dom.configModelInput?.value || "").trim();
  if (!base_url || !api_key || !model) {
    if (dom.configSetupHint) {
      dom.configSetupHint.textContent = "请完整填写 base_url、api_key、model。";
    }
    return;
  }
  if (dom.saveConfigBtn) dom.saveConfigBtn.disabled = true;
  showLoading({
    title: "正在保存配置",
    hint: "保存后会立即生效，无需重启页面。"
  });
  try {
    await requestJson("/config/save", {
      method: "POST",
      body: { base_url, api_key, model }
    });
    closeConfigSetupModal();
    setStatus("API 配置已保存");
  } catch (error) {
    if (dom.configSetupHint) {
      dom.configSetupHint.textContent = `保存失败：${error.message}`;
    }
  } finally {
    if (dom.saveConfigBtn) dom.saveConfigBtn.disabled = false;
    hideLoading();
  }
}

function syncRuntimeStatus() {
  if (!state.sessionId) {
    setStatus("待机中");
    return;
  }
  if (!state.snapshot) {
    setStatus(state.outlineApproved ? "大纲已通过，等待开始推演" : "会话已创建");
    return;
  }

  const resultStatus = state.snapshot?.result?.status;
  if (resultStatus) {
    const statusMap = {
      ended: "自然收束",
      director_cut: "导演Cut",
      max_turns_reached: "达到上限",
      handoff: "交接",
      api_error: "模型错误",
      format_error: "格式错误",
      key_error: "字段错误"
    };
    setStatus(`本集结束：${statusMap[resultStatus] || resultStatus}`);
    return;
  }

  if (state.snapshot?.episode_status === "paused") {
    setStatus("当前暂停");
    return;
  }

  const episode = getCurrentEpisodeNumber(state.snapshot);
  const turn = state.snapshot?.current_turn ?? 0;
  setStatus(`第 ${episode} 集进行中 · 第 ${turn} 轮`);
}

function updateStartDemoButton() {
  if (!dom.startDemoBtn) return;
  dom.startDemoBtn.disabled = state.hasTriggeredStartDemo;
}

function updateRunToggleButton() {
  if (!dom.runToggleBtn) return;
  dom.runToggleBtn.disabled = false;
  dom.runToggleBtn.classList.remove("warning-btn");
  dom.runToggleBtn.classList.add("primary-btn");
  dom.runToggleBtn.textContent = "继续推演";

  if (!state.snapshot) {
    return;
  }
  if (state.snapshot?.result) {
    dom.runToggleBtn.disabled = true;
    dom.runToggleBtn.textContent = "本集已结束";
    return;
  }
  if (state.snapshot?.episode_status === "paused") {
    dom.runToggleBtn.textContent = "继续推演";
    return;
  }

  dom.runToggleBtn.classList.remove("primary-btn");
  dom.runToggleBtn.classList.add("warning-btn");
  dom.runToggleBtn.textContent = "暂停推演";
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
    const resolvedPosition = getRolePositionMeta(role.role_position);
    roster[finalName] = {
      char_id: index + 1,
      name: finalName,
      role_type: inferRoleTypeFromPosition(role.role_position),
      role_position: resolvedPosition.label,
      gender: inferGenderFromPosition(role.role_position, role.gender),
      age: Number(role.age) || 0,
      identity: String(role.identity || "待设定身份").trim() || "待设定身份",
      appearance_tags: appearance.length ? appearance : ["待补充"],
      personality_tags: personality.length ? personality : ["待补充"]
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

function handleRoleDesignerInput(event) {
  const target = event.target;
  const roleId = target.dataset.roleId;
  if (!roleId) return;

  const field = target.dataset.field;
  if (!field || field === "template" || field === "role_position" || field === "gender") return;

  updateRoleDraft(roleId, (current) => {
    const next = { ...current };
    if (field === "appearance_tags" || field === "personality_tags") {
      next[field] = normalizeTagList(target.value);
    } else if (field === "age") {
      next.age = target.value;
    } else {
      next[field] = target.value;
    }
    return normalizeRoleDraft(next);
  });

  const updatedRole = getRoleDraftById(roleId);
  refreshRoleUI({ skipDesignerList: true });

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
  if (!roleId) return;

  const field = target.dataset.field;

  if (field === "role_position" || field === "gender") {
    updateRoleDraft(roleId, (current) => normalizeRoleDraft({ ...current, [field]: target.value }));
    refreshRoleUI();
    return;
  }

  if (field !== "template") return;

  if (target.value === "custom") {
    updateRoleDraft(roleId, (current) => normalizeRoleDraft({ ...current, templateId: null }));
    refreshRoleUI({ skipDesignerList: true });
    return;
  }

  const [group, templateId] = String(target.value).split(":");
  const current = getRoleDraftById(roleId);
  if (!current) return;
  const nextDraft = createRoleDraft(group, templateId, {
    id: current.id,
    isStarter: current.isStarter,
    role_position: current.role_position
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
  state.roleDrafts = [createCustomRoleDraft(), ...state.roleDrafts];
  refreshRoleUI();
}

function syncRoleOptions(roleNames) {
  const resolvedRoles = roleNames?.length ? roleNames : getCurrentRoleNames();
  const currentValue = dom.targetRole.value;
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

  dom.targetRole.value = resolvedRoles.includes(currentValue) ? currentValue : "";
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
  if (snapshot) {
    state.hasTriggeredStartDemo = true;
  }
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
  syncRuntimeStatus();
  updateStartDemoButton();
  updateRunToggleButton();
  updateNextEpisodeButton();
  syncStageNav();
}

function resetSessionState() {
  state.sessionId = null;
  state.plannerOutput = null;
  state.outlineApproved = false;
  state.snapshot = null;
  state.shouldContinue = false;
  state.isLooping = false;
  state.hasExportedArtifacts = false;
  state.hasTriggeredStartDemo = false;
  dom.sessionBadge.textContent = "未创建";
  setStatus("待机中");
  dom.outlineStatus.textContent = "还没有可用大纲";
  dom.scriptOutput.textContent = "还没有导出结果。先生成大纲并跑完一轮推演。";
  setApiPreview("当前还没有 session。", "等待请求...");
  renderOutline();
  renderMessages();
  renderMonitorFeed();
  updateStartDemoButton();
  updateRunToggleButton();
  updateNextEpisodeButton();
  dom.timelineSlider.max = "0";
  dom.timelineSlider.value = "0";
  updateTimelineDisplay();
  setStage(1, { force: true });
  dom.turnBadge.textContent = "第 0 句";
  updateRunToggleButton();
}

const runtimeActions = window.createRuntimeActions({
  state,
  dom,
  setStatus,
  setApiPreview,
  renderOutline,
  setStage,
  applySnapshot,
  syncRuntimeStatus,
  getCurrentEpisodeNumber,
  renderMessages,
  renderMonitorFeed,
  buildConfigOverride,
  showLoading,
  hideLoading
});

const raGenerateOutline = runtimeActions.generateOutline;
const raReviewOutline = runtimeActions.reviewOutline;
const raApproveOutline = runtimeActions.approveOutline;
const raQuickStart = runtimeActions.quickStart;
const raContinueScene = runtimeActions.continueScene;
const raToggleScene = runtimeActions.toggleScene;
const raStartNextEpisode = runtimeActions.startNextEpisode;
const raCutScene = runtimeActions.cutScene;
const raSendDirective = runtimeActions.sendDirective;
const raRollbackScene = runtimeActions.rollbackScene;
const raExportArtifacts = runtimeActions.exportArtifacts;
const raPreviewCurrentState = runtimeActions.previewCurrentState;
const raRefreshStage = runtimeActions.refreshStage;

window.bindFrontendEvents({
  state,
  dom,
  randomizeAll,
  optimizeInput,
  updateEpisodeCountDisplay,
  updateRoundDisplay,
  updateTimelineDisplay,
  openRoleDesigner,
  closeRoleDesigner,
  addPresetRole,
  addCustomRole,
  handleRoleDesignerInput,
  handleRoleDesignerChange,
  handleRoleDesignerClick,
  setApiPreview,
  syncStageNav,
  renderAllChips,
  resetSessionState,
  setStage,
  raGenerateOutline,
  raReviewOutline,
  raApproveOutline,
  raQuickStart,
  raContinueScene,
  raToggleScene,
  raStartNextEpisode,
  raCutScene,
  raSendDirective,
  raRollbackScene,
  raExportArtifacts,
  raPreviewCurrentState,
  raRefreshStage
});

if (typeof window.initWorkflowMode === "function") {
  window.initWorkflowMode({
    state,
    dom,
    setStage,
    setStatus,
    setApiPreview,
    renderAllChips,
    refreshRoleUI,
    updateEpisodeCountDisplay,
    raExportArtifacts,
    showLoading,
    hideLoading
  });
}

if (dom.saveConfigBtn) {
  dom.saveConfigBtn.addEventListener("click", () => {
    saveApiConfigFromModal().catch(() => {});
  });
}

initializeDefaults();
resetSessionState();
ensureApiConfig().catch(() => {});
window.addEventListener("resize", syncTopPanelHeights);
window.addEventListener("load", syncTopPanelHeights);
