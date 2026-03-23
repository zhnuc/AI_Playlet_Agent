const options = {
  genre: ["重生复仇", "豪门虐恋", "逆袭爽文", "先婚后爱", "职场博弈", "悬疑反转"],
  mode: ["群聊推演", "结构优先", "爆点优先", "角色先行", "导演介入"],
  heroes: ["禁欲霸总", "清醒女主", "毒舌律师", "落魄千金", "黑化影帝", "天才医生"],
  villains: ["心机白月光", "伪善继母", "资本对手", "伪装闺蜜", "阴狠叔父", "幕后导演"]
};

const promptMap = {
  高冷: "语言风格：每句不超过 15 字，多用反问句，标点极简，情绪藏在动作里。",
  霸总: "行为逻辑：永远先控制局面，再表达情绪；台词短促，带命令感。",
  心机: "策略偏好：先试探，再递刀；习惯用温柔措辞包装恶意。",
  重生: "剧情目标：开局必须携带前世信息差，前三句就要埋下反杀钩子。"
};

const outlineSeed = [
  { title: "钩子开场", note: "重生回签字前，女主改写命运" },
  { title: "第一次对峙", note: "霸总拒绝离婚，白月光当场挑衅" },
  { title: "监制推进", note: "防止重复争吵，强制抛出证据" },
  { title: "反转收束", note: "女主亮出录音，推进下一集悬念" }
];

const demoScene = [
  { type: "action", role: "Action", text: "总裁办公室，文件散落，雨夜灯光切进玻璃幕墙。" },
  { type: "dialogue", role: "顾沉舟", text: `协议我不签。

你想走？

凭什么。

凭什么啊啊啊啊啊啊啊啊啊啊啊啊？` },
  { type: "inner", role: "林晚", text: "前世我在这一步输了，这次我要让每个人都付代价。" },
  { type: "dialogue", role: "白薇", text: "顾总，她不过是在演戏，你还真信了？" },
  { type: "action", role: "Action", text: "林晚把录音笔按在桌面上，红灯亮起。" },
  { type: "dialogue", role: "林晚", text: "继续说。我正好缺证据。" }
];

const monitorNotes = [
  "监制判断：冲突密度正常，建议第 4 句前抛出关键证据。",
  "Suggestion：@白薇 继续伪装冷静，但不要重复相同威胁。",
  "Cut 预警：若 6 轮内未出现利益交换，立即结束本场。"
];

const genreResult = document.querySelector("#genreResult");
const heroResult = document.querySelector("#heroResult");
const villainResult = document.querySelector("#villainResult");
const promptPreview = document.querySelector("#promptPreview");
const chatFeed = document.querySelector("#chatFeed");
const outlineTree = document.querySelector("#outlineTree");
const monitorFeed = document.querySelector("#monitorFeed");
const scriptOutput = document.querySelector("#scriptOutput");
const streamStatus = document.querySelector("#streamStatus");
const roundLimit = document.querySelector("#roundLimit");
const roundValue = document.querySelector("#roundValue");
const roundBadge = document.querySelector("#roundBadge");
const timelineSlider = document.querySelector("#timelineSlider");
const timelineValue = document.querySelector("#timelineValue");
const modeBadge = document.querySelector("#modeBadge");
const messageTemplate = document.querySelector("#messageTemplate");

const state = {
  selectedGenre: genreResult.textContent.trim() || options.genre[0],
  selectedMode: modeBadge.textContent.trim() || options.mode[0],
  isStreaming: false,
  messages: [...demoScene]
};

function initializeDefaults() {
  const heroInput = document.querySelector("#heroInput");
  const villainInput = document.querySelector("#villainInput");
  const plotInput = document.querySelector("#plotInput");

  if (!genreResult.textContent.trim()) {
    genreResult.textContent = state.selectedGenre;
  }
  if (!heroResult.textContent.trim()) {
    heroResult.textContent = options.heroes[0];
  }
  if (!villainResult.textContent.trim()) {
    villainResult.textContent = options.villains[0];
  }
  if (!promptPreview.textContent.trim()) {
    promptPreview.textContent = promptMap.高冷;
  }
  if (!heroInput.value.trim()) {
    heroInput.value = `${heroResult.textContent.trim()}，强控制欲，表面冷静，关键时刻会主动掀桌。`;
  }
  if (!villainInput.value.trim()) {
    villainInput.value = `${villainResult.textContent.trim()}，擅长操控他人判断，喜欢在众人面前制造误会。`;
  }
  if (!plotInput.value.trim()) {
    plotInput.value = `围绕“${genreResult.textContent.trim()}”展开，要求首场戏就发生公开冲突，并在本集结尾留下身份反转。`;
  }
  if (!scriptOutput.textContent.trim()) {
    createFormattedScript();
  }
}

function renderChips(field, values, selected) {
  const container = document.querySelector(`.chip-list[data-field="${field}"]`);
  container.innerHTML = "";

  values.forEach((value) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = `chip${value === selected ? " active" : ""}`;
    chip.textContent = value;
    chip.addEventListener("click", () => {
      if (field === "genre") {
        state.selectedGenre = value;
        genreResult.textContent = value;
      }
      if (field === "mode") {
        state.selectedMode = value;
        modeBadge.textContent = value;
      }
      renderAllChips();
    });
    container.appendChild(chip);
  });
}

function renderAllChips() {
  renderChips("genre", options.genre, state.selectedGenre);
  renderChips("mode", options.mode, state.selectedMode);
}

function renderOutline() {
  outlineTree.innerHTML = "";
  outlineSeed.forEach((item, index) => {
    const li = document.createElement("li");
    li.innerHTML = `<strong>${index + 1}. ${item.title}</strong><small>${item.note}</small>`;
    outlineTree.appendChild(li);
  });
}

function renderMonitorFeed() {
  monitorFeed.innerHTML = "";
  monitorNotes.forEach((note) => {
    const li = document.createElement("li");
    li.textContent = note;
    monitorFeed.appendChild(li);
  });
}

function appendMessage(message) {
  const node = messageTemplate.content.firstElementChild.cloneNode(true);
  node.classList.add(message.type);
  node.querySelector(".message-role").textContent = message.role;
  node.querySelector(".message-body").textContent = message.text;
  chatFeed.appendChild(node);
  chatFeed.scrollTop = chatFeed.scrollHeight;
}

function renderMessages() {
  chatFeed.innerHTML = "";
  state.messages.forEach(appendMessage);
}

function updateRoundDisplay() {
  const value = `${roundLimit.value} 轮`;
  roundValue.textContent = value;
  roundBadge.textContent = value;
}

function updateTimelineDisplay() {
  const current = Math.max(1, Math.round((timelineSlider.value / 100) * state.messages.length));
  timelineValue.textContent = `第 ${current} 句`;
}

function sample(values) {
  return values[Math.floor(Math.random() * values.length)];
}

function randomizeIdeas() {
  const genre = sample(options.genre);
  const hero = sample(options.heroes);
  const villain = sample(options.villains);

  state.selectedGenre = genre;
  genreResult.textContent = genre;
  heroResult.textContent = hero;
  villainResult.textContent = villain;
  promptPreview.textContent = promptMap[hero.includes("霸总") ? "霸总" : genre.includes("重生") ? "重生" : "高冷"];

  document.querySelector("#heroInput").value = `${hero}，强控制欲，表面冷静，关键时刻会主动掀桌。`;
  document.querySelector("#villainInput").value = `${villain}，擅长操控他人判断，喜欢在众人面前制造误会。`;
  document.querySelector("#plotInput").value = `围绕“${genre}”展开，要求首场戏就发生公开冲突，并在本集结尾留下身份反转。`;

  renderAllChips();
}

function optimizeCustomInput() {
  const custom = document.querySelector("#customTagInput").value.trim();
  if (!custom) {
    promptPreview.textContent = "请输入一个新的题材或角色关键词后再优化。";
    return;
  }

  promptPreview.textContent = `输入优化 Agent：已将“${custom}”扩写为角色卡。身份层：边缘求生者；外显特征：沉默观察、说话带留白；隐藏驱动：渴望翻盘；冲突触发器：被羞辱后绝不退让。`;
}

async function fakeStreamScene() {
  if (state.isStreaming) {
    return;
  }

  state.isStreaming = true;
  streamStatus.textContent = "推演中";
  chatFeed.innerHTML = "";

  for (const message of state.messages) {
    appendMessage({ ...message, text: "" });
    const body = chatFeed.lastElementChild.querySelector(".message-body");
    for (const char of message.text) {
      body.textContent += char;
      await new Promise((resolve) => setTimeout(resolve, 18));
    }
  }

  streamStatus.textContent = "已完成";
  state.isStreaming = false;
}

function cutScene() {
  streamStatus.textContent = "已暂停，等待导演指令";
  monitorFeed.prepend(createMonitorItem("Cut：导演已中断当前场景，可回档并改写角色动机。"));
}

function continueScene() {
  streamStatus.textContent = "继续推演";
  monitorFeed.prepend(createMonitorItem("Continue：维持当前张力，下一句必须升级冲突。"));
}

function createMonitorItem(text) {
  const li = document.createElement("li");
  li.textContent = text;
  return li;
}

function sendDirective() {
  const command = document.querySelector("#directorCommand").value.trim();
  if (!command) {
    return;
  }

  const directive = {
    type: "action",
    role: "Director",
    text: `导演指令已写入本场 Prompt：${command}`
  };

  state.messages.push(directive);
  appendMessage(directive);
  monitorFeed.prepend(createMonitorItem(`Suggestion：已根据导演指令重写角色行为约束。`));
}

function createFormattedScript() {
  const plot = document.querySelector("#plotInput").value.trim() || "女主重生回离婚前夜，决定反杀所有布局者。";
  const hero = document.querySelector("#heroInput").value.trim() || "顾沉舟：强控制欲的禁欲霸总";
  const villain = document.querySelector("#villainInput").value.trim() || "白薇：表面无害的操盘者";

  scriptOutput.textContent = [
    "[第 1 集]",
    "场景：总裁办公室 / 夜 / 内",
    "",
    `人物设定：${hero}`,
    `对抗人物：${villain}`,
    `剧情主线：${plot}`,
    "",
    "动作：暴雨砸在落地窗上，林晚将离婚协议推到桌面中央。",
    "顾沉舟：协议我不签。",
    "林晚：这次，不由你。",
    "内心独白：她盯着顾沉舟指节发白的手，知道前世的裂缝就在这一秒重新张开。",
    "动作：白薇推门而入，视线落在录音笔上，笑意僵住。",
    "白薇：你想把谁拖下水？",
    "林晚：谁心虚，谁就先下去。"
  ].join("\n");
}

async function mockAgentRequest(payload) {
  return {
    endpoint: "/api/agent/run-scene",
    method: "POST",
    body: payload,
    stream: "SSE"
  };
}

async function previewRequest() {
  const payload = {
    genre: state.selectedGenre,
    mode: state.selectedMode,
    hero: document.querySelector("#heroInput").value.trim(),
    villain: document.querySelector("#villainInput").value.trim(),
    plot: document.querySelector("#plotInput").value.trim(),
    roundLimit: Number(roundLimit.value),
    directorCommand: document.querySelector("#directorCommand").value.trim()
  };

  const request = await mockAgentRequest(payload);
  document.querySelector("#apiSnippet").textContent = JSON.stringify(request, null, 2);
}

document.querySelector("#spinIdeas").addEventListener("click", randomizeIdeas);
document.querySelector("#randomizeAll").addEventListener("click", randomizeIdeas);
document.querySelector("#optimizeInput").addEventListener("click", optimizeCustomInput);
document.querySelector("#startDemo").addEventListener("click", fakeStreamScene);
document.querySelector("#continueScene").addEventListener("click", continueScene);
document.querySelector("#cutScene").addEventListener("click", cutScene);
document.querySelector("#sendDirective").addEventListener("click", sendDirective);
document.querySelector("#producerSuggest").addEventListener("click", () => {
  monitorFeed.prepend(createMonitorItem("Suggestion：进入拖沓区间，下一轮必须出现身份差或实锤证据。"));
});
document.querySelector("#formatScript").addEventListener("click", createFormattedScript);
document.querySelector("#mockRequest").addEventListener("click", previewRequest);
document.querySelector("#clearStage").addEventListener("click", () => {
  chatFeed.innerHTML = "";
  streamStatus.textContent = "舞台已清空";
});

roundLimit.addEventListener("input", updateRoundDisplay);
timelineSlider.addEventListener("input", updateTimelineDisplay);

renderAllChips();
renderOutline();
renderMonitorFeed();
renderMessages();
initializeDefaults();
updateRoundDisplay();
updateTimelineDisplay();