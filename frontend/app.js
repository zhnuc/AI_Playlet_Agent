const options = {
  genre: ["重生复仇", "豪门虐恋", "逆袭爽文", "先婚后爱", "职场博弈", "悬疑反转"],
  runMode: [
    { value: "planned", label: "大纲驱动" },
    { value: "free", label: "自由开场" }
  ],
  scene: ["总裁办公室", "家族晚宴", "发布会后台", "直播间", "医院走廊", "董事会会议室"]
};

const roleDefaults = {
  林若雪: {
    char_id: 1,
    role_type: "主角",
    gender: "女",
    age: 22,
    identity: "真千金",
    appearance_tags: ["美艳御姐", "冰霜美人"],
    personality_tags: ["毒舌", "冷静缜密", "杀伐果断"],
    catchphrase: "属于我的东西，连本带利都要拿回来！"
  },
  顾寒霆: {
    char_id: 2,
    role_type: "主角",
    gender: "男",
    age: 28,
    identity: "京圈太子爷",
    appearance_tags: ["高大霸气", "西装暴徒"],
    personality_tags: ["霸道", "自傲", "暴脾气"],
    catchphrase: "女人，别无理取闹，你在玩火。"
  },
  林白莲: {
    char_id: 3,
    role_type: "反派",
    gender: "女",
    age: 21,
    identity: "假千金",
    appearance_tags: ["小白花", "楚楚可怜", "柔情似水"],
    personality_tags: ["绿茶", "心机", "嫉妒心强"],
    catchphrase: "姐姐，都是我的错，你别怪寒霆哥哥。"
  }
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
  isLooping: false
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
  chatFeed: document.querySelector("#chatFeed"),
  monitorFeed: document.querySelector("#monitorFeed"),
  turnBadge: document.querySelector("#turnBadge"),
  promptPreview: document.querySelector("#promptPreview"),
  plotInput: document.querySelector("#plotInput"),
  sceneInput: document.querySelector("#sceneInput"),
  heroineInput: document.querySelector("#heroineInput"),
  leadInput: document.querySelector("#leadInput"),
  villainInput: document.querySelector("#villainInput"),
  customTagInput: document.querySelector("#customTagInput"),
  episodeCount: document.querySelector("#episodeCount"),
  episodeCountValue: document.querySelector("#episodeCountValue"),
  roundLimit: document.querySelector("#roundLimit"),
  roundValue: document.querySelector("#roundValue"),
  timelineSlider: document.querySelector("#timelineSlider"),
  timelineValue: document.querySelector("#timelineValue"),
  outlineFeedback: document.querySelector("#outlineFeedback"),
  directorCommand: document.querySelector("#directorCommand"),
  targetRole: document.querySelector("#targetRole"),
  scriptOutput: document.querySelector("#scriptOutput"),
  apiSnippet: document.querySelector("#apiSnippet"),
  apiHint: document.querySelector("#apiHint"),
  messageTemplate: document.querySelector("#messageTemplate")
};

function initializeDefaults() {
  dom.genreResult.textContent = state.selectedGenre;
  dom.runModeResult.textContent = "大纲驱动";
  dom.modeBadge.textContent = "大纲驱动";
  dom.sceneResult.textContent = options.scene[0];
  dom.plotInput.value = "真千金归来，当场撕开假千金和渣男联手设局的第一层伪装。";
  dom.sceneInput.value = options.scene[0];
  dom.heroineInput.value = "真千金，毒舌冷静，认准了就一定要拿回家族产业。";
  dom.leadInput.value = "京圈太子爷，强控制欲，先稳场再表态，但被逼到墙角时会失控。";
  dom.villainInput.value = "假千金，擅长装无辜和操控舆论，在众人面前最会倒打一耙。";
  dom.promptPreview.textContent = promptMap[state.selectedGenre];
  dom.scriptOutput.textContent = "还没有导出结果。先生成大纲并跑完一轮推演。";
  updateEpisodeCountDisplay();
  updateRoundDisplay();
  syncRoleOptions(Object.keys(roleDefaults));
  renderAllChips();
  renderOutline();
  renderMessages();
  renderMonitorFeed();
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

function cloneRoleConfig(base, cardText) {
  const parts = cardText
    .split(/[\n，。；;、]/)
    .map((item) => item.trim())
    .filter(Boolean);

  const next = { ...base };
  if (parts[0]) {
    next.identity = parts[0];
  }
  if (parts.length > 1) {
    next.personality_tags = parts.slice(1, 4);
  }
  if (parts.length > 4) {
    next.catchphrase = parts.slice(4).join("，");
  }
  return next;
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
    character_roster: {
      林若雪: cloneRoleConfig(roleDefaults.林若雪, dom.heroineInput.value.trim()),
      顾寒霆: cloneRoleConfig(roleDefaults.顾寒霆, dom.leadInput.value.trim()),
      林白莲: cloneRoleConfig(roleDefaults.林白莲, dom.villainInput.value.trim())
    }
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

function syncRoleOptions(roleNames) {
  const resolvedRoles = roleNames?.length ? roleNames : Object.keys(roleDefaults);
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
}

function formatEventLabel(event) {
  const kindMap = {
    thought: "Inner Thought",
    action: "Action",
    dialogue: "Dialogue",
    monitor: "Monitor",
    director: "Director",
    system: "System"
  };
  return `${event.speaker || "SYSTEM"} · ${kindMap[event.kind] || event.kind || "Event"}`;
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

  events.forEach((event) => {
    const node = dom.messageTemplate.content.firstElementChild.cloneNode(true);
    node.classList.add(event.kind || "system");
    node.querySelector(".message-role").textContent = formatEventLabel(event);
    node.querySelector(".message-body").textContent = event.content || "";
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
      episode: 1,
      max_turns: Number(dom.roundLimit.value)
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
document.querySelector("#cutScene").addEventListener("click", cutScene);
document.querySelector("#sendDirective").addEventListener("click", sendDirective);
document.querySelector("#rollbackBtn").addEventListener("click", rollbackScene);
document.querySelector("#formatScript").addEventListener("click", exportArtifacts);
document.querySelector("#previewStateBtn").addEventListener("click", previewCurrentState);
document.querySelector("#refreshStageBtn").addEventListener("click", refreshStage);
document.querySelector("#resetSessionBtn").addEventListener("click", resetSessionState);

initializeDefaults();
resetSessionState();
