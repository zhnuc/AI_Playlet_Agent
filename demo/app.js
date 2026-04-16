const roles = {
  lin: {
    id: "lin",
    name: "林若雪",
    initials: "林",
    tone: "linear-gradient(135deg, #c4522d, #8e3417)",
    identity: "林家真千金，重生归来",
    summary: "擅长用冷静和证据反制对手，发言克制，但每一句都带着布局。",
    staticTags: ["冷艳", "利落", "黑长发", "真千金"],
    dynamicTags: ["压制", "掌控全局", "冲突对象：顾寒庭"]
  },
  gu: {
    id: "gu",
    name: "顾寒庭",
    initials: "顾",
    tone: "linear-gradient(135deg, #1f5f84, #113f5d)",
    identity: "顾氏集团掌权人",
    summary: "习惯用沉默观察全场，在关键时刻切断对方节奏。",
    staticTags: ["克制", "西装", "高压", "总裁"],
    dynamicTags: ["试探", "暂不站队", "冲突对象：董事会"]
  },
  qin: {
    id: "qin",
    name: "秦曼",
    initials: "秦",
    tone: "linear-gradient(135deg, #7d4b9a, #56316b)",
    identity: "林家养女，直播间话题中心",
    summary: "擅长情绪操控和舆论引导，语言表演欲强，节奏快。",
    staticTags: ["直播感", "甜美", "锋利", "养女"],
    dynamicTags: ["委屈包装", "舆论先手", "冲突对象：林若雪"]
  }
};

const roleProfiles = Object.fromEntries(
  Object.values(roles).map((role) => [
    role.id,
    {
      character_id: role.id,
      static_profile: {
        name: role.name,
        identity: role.identity,
        appearance_tags: [...role.staticTags],
        personality_tags: [],
      },
      dynamic_profile: {
        current_goal: role.summary,
        beliefs_about_others: {},
        unresolved_hook: "",
        episode_digest_public: role.dynamicTags.join("；"),
        episode_digest_private: "",
      },
    },
  ])
);

const episodes = {
  1: {
    title: "董事会会议室",
    stream: [
      {
        type: "role",
        roleId: "lin",
        turn: 11,
        scene: "董事会会议室",
        segments: [
          { kind: "thought", content: "现在不是争辩的时候，先让他们把注意力移到录音上。" },
          { kind: "action", content: "她把录音笔推向桌面中央，指尖停在播放键上。" },
          { kind: "dialogue", content: "今天这份协议，我不签。" }
        ]
      },
      {
        type: "role",
        roleId: "qin",
        turn: 12,
        scene: "董事会会议室",
        segments: [
          { kind: "thought", content: "如果现在不先抢到情绪点，舆论会彻底站到她那边。" },
          { kind: "action", content: "她先一步抬眼看向董事席，声音刻意放轻。" },
          { kind: "dialogue", content: "姐姐是不是对我有什么误会？我可以解释。" }
        ]
      },
      {
        type: "system",
        label: "DIRECTOR",
        turn: 13,
        scene: "董事会会议室",
        content: "导演指令：让林若雪下一句先抛证据，不做解释。"
      },
      {
        type: "role",
        roleId: "lin",
        turn: 14,
        scene: "董事会会议室",
        segments: [
          { kind: "thought", content: "既然导演要求提速，那就直接把证据摊出来。" },
          { kind: "action", content: "她点开录音，把关键信息停在每个人都听得见的位置。" },
          { kind: "dialogue", content: "这段录音，从昨晚十点二十七分开始，谁先解释？" }
        ]
      },
      {
        type: "system",
        label: "MONITOR",
        turn: 14,
        scene: "董事会会议室",
        content: "监制提示：情绪张力明显提升，冲突焦点已锁定“证据公开”。"
      },
      {
        type: "role",
        roleId: "gu",
        turn: 15,
        scene: "董事会会议室",
        segments: [
          { kind: "thought", content: "现在必须压住现场节奏，不能让会议失控成互相甩锅。" },
          { kind: "action", content: "他合上资料夹，抬手示意所有人停下。" },
          { kind: "dialogue", content: "继续开会，谁都别离席。" }
        ]
      },
      {
        type: "role",
        roleId: "qin",
        turn: 16,
        scene: "董事会会议室",
        segments: [
          { kind: "thought", content: "不能让顾寒庭把节奏锁死，只要观众还在看我，我就还有机会。" },
          { kind: "action", content: "她把肩膀微微缩住，像是被突然压住了呼吸。" },
          { kind: "dialogue", content: "如果姐姐手里的录音是真的，那我也想知道是谁故意让我背这个锅。" }
        ]
      },
      {
        type: "role",
        roleId: "lin",
        turn: 17,
        scene: "董事会会议室",
        segments: [
          { kind: "thought", content: "她现在开始往“被利用”这个方向退，我得把人名钉死。" },
          { kind: "action", content: "她翻开第二页材料，把时间线投到了会议室主屏上。" },
          { kind: "dialogue", content: "十点二十七分给你打电话的人，不是我，也不是顾总，是林家的财务总监。" }
        ]
      },
      {
        type: "system",
        label: "MONITOR",
        turn: 17,
        scene: "董事会会议室",
        content: "监制提示：主冲突正在从情绪对撞转向责任归属，信息密度提升。"
      },
      {
        type: "role",
        roleId: "gu",
        turn: 18,
        scene: "董事会会议室",
        segments: [
          { kind: "thought", content: "财务总监这个名字一出来，董事会的人就不可能继续装作只是家事。" },
          { kind: "action", content: "他朝法务点了点头，让人立刻去调昨晚的门禁记录。" },
          { kind: "dialogue", content: "把财务总监请进来，在他到之前，这个会议一秒都不停。" }
        ]
      },
      {
        type: "role",
        roleId: "qin",
        turn: 19,
        scene: "董事会会议室",
        segments: [
          { kind: "thought", content: "不行，不能让所有人的视线都顺着那条时间线走下去。" },
          { kind: "action", content: "她抬手按住桌边，先一步把话题拉回自己身上。" },
          { kind: "dialogue", content: "可昨晚最后见到那份协议的人是我，如果真有人动过手脚，我也是受害者。" }
        ]
      },
      {
        type: "role",
        roleId: "lin",
        turn: 20,
        scene: "董事会会议室",
        segments: [
          { kind: "thought", content: "她开始争受害者位置了，那就把她的主动行为一并摆出来。" },
          { kind: "action", content: "她把一段监控截图推到秦曼面前，指尖停在暂停画面上。" },
          { kind: "dialogue", content: "受害者不会在凌晨一点独自去协议室，也不会删掉门口那段监控。" }
        ]
      },
      {
        type: "system",
        label: "DIRECTOR",
        turn: 20,
        scene: "董事会会议室",
        content: "导演指令：让顾寒庭暂时不表态，把舞台继续留给两位女主角。"
      },
      {
        type: "role",
        roleId: "gu",
        turn: 21,
        scene: "董事会会议室",
        segments: [
          { kind: "thought", content: "现在不是我接管的时候，再沉半拍，她们自己会把底牌翻出来。" },
          { kind: "action", content: "他收回原本要开口的动作，只把椅背往后靠了一寸。" },
          { kind: "dialogue", content: "你们继续。今天谁先失言，谁就先出局。" }
        ]
      },
      {
        type: "role",
        roleId: "qin",
        turn: 22,
        scene: "董事会会议室",
        segments: [
          { kind: "thought", content: "顾寒庭不救场，那我只能赌最后一次情绪反扑。" },
          { kind: "action", content: "她忽然笑了一下，眼里却已经有了明显的红意。" },
          { kind: "dialogue", content: "姐姐，你今天到底是回来认家，还是回来把所有人都拖进泥里？" }
        ]
      },
      {
        type: "role",
        roleId: "lin",
        turn: 23,
        scene: "董事会会议室",
        segments: [
          { kind: "thought", content: "终于，她把问题说成“我和这个家”的对立了。" },
          { kind: "action", content: "她合上文件夹，视线越过秦曼，直接看向董事席最中间的位置。" },
          { kind: "dialogue", content: "我回来不是认家，我回来是告诉你们，这个家从来没把我当过家人。" }
        ]
      },
      {
        type: "system",
        label: "MONITOR",
        turn: 23,
        scene: "董事会会议室",
        content: "监制提示：人物关系强度上升，亲缘、利益与舆论三条冲突线已并行展开。"
      },
      {
        type: "role",
        roleId: "gu",
        turn: 24,
        scene: "董事会会议室",
        segments: [
          { kind: "thought", content: "情绪已经到顶点，现在该把这场家事彻底转成公司决策。" },
          { kind: "action", content: "他把最终议程推到桌前，示意秘书重新记录会议纪要。" },
          { kind: "dialogue", content: "会议继续，第二项议程，追责昨夜协议篡改人与相关受益方。" }
        ]
      }
    ]
  },
  2: {
    title: "直播后台",
    stream: [
      {
        type: "system",
        label: "SYSTEM",
        turn: 1,
        scene: "直播后台",
        content: "第 2 集开始，场景切换到直播后台。"
      },
      {
        type: "role",
        roleId: "qin",
        turn: 5,
        scene: "直播后台",
        segments: [
          { kind: "thought", content: "先把自己的受害者感做出来，才有机会抢回镜头。" },
          { kind: "action", content: "她摘下耳返，眼眶瞬间红了，话却说得更慢。" },
          { kind: "dialogue", content: "大家都看到了，她从一开始就在给我设局。" }
        ]
      },
      {
        type: "role",
        roleId: "lin",
        turn: 8,
        scene: "直播后台",
        segments: [
          { kind: "thought", content: "不用解释动机，只要让观众先看见电话和时间点。" },
          { kind: "action", content: "她把后台录音递给顾寒庭，让返送屏停在拨号记录页。" },
          { kind: "dialogue", content: "你要直播，那就别删掉开场前那通电话。" }
        ]
      },
      {
        type: "system",
        label: "MONITOR",
        turn: 8,
        scene: "直播后台",
        content: "监制提示：场景张力已从董事会压迫转为舆论争夺。"
      },
      {
        type: "role",
        roleId: "gu",
        turn: 10,
        scene: "直播后台",
        segments: [
          { kind: "thought", content: "现在该做的是压住现场节奏，让证据先于情绪扩散。" },
          { kind: "action", content: "他抬手让法务后撤，把直播切到延时模式。" },
          { kind: "dialogue", content: "直播可以继续，但任何剪辑都不能离开我这边。" }
        ]
      }
    ]
  }
};

const dom = {
  statusMode: document.querySelector("#statusMode"),
  statusSession: document.querySelector("#statusSession"),
  statusState: document.querySelector("#statusState"),
  sceneTitle: document.querySelector("#sceneTitle"),
  sceneDescription: document.querySelector("#sceneDescription"),
  episodeChip: document.querySelector("#episodeChip"),
  turnChip: document.querySelector("#turnChip"),
  progressChip: document.querySelector("#progressChip"),
  chatFeed: document.querySelector("#chatFeed"),
  continueBtn: document.querySelector("#continueBtn"),
  rollbackStepBtn: document.querySelector("#rollbackStepBtn"),
  nextEpisodeActionBtn: document.querySelector("#nextEpisodeActionBtn"),
  controlStateTitle: document.querySelector("#controlStateTitle"),
  controlStateDescription: document.querySelector("#controlStateDescription"),
  controlActions: document.querySelector("#controlActions"),
  monitorList: document.querySelector("#monitorList"),
  roleCardShell: document.querySelector("#roleCardShell"),
  roleCardTitle: document.querySelector("#roleCardTitle"),
  roleCardAvatar: document.querySelector("#roleCardAvatar"),
  roleCardName: document.querySelector("#roleCardName"),
  roleCardIdentity: document.querySelector("#roleCardIdentity"),
  roleCardSummary: document.querySelector("#roleCardSummary"),
  staticTagList: document.querySelector("#staticTagList"),
  dynamicTagList: document.querySelector("#dynamicTagList"),
  recentRecordList: document.querySelector("#recentRecordList"),
  recentRecordsHint: document.querySelector("#recentRecordsHint"),
  expandRecentBtn: document.querySelector("#expandRecentBtn"),
  openHistoryBtn: document.querySelector("#openHistoryBtn"),
  closeRoleCardBtn: document.querySelector("#closeRoleCardBtn"),
  historyShell: document.querySelector("#historyShell"),
  historySubtitle: document.querySelector("#historySubtitle"),
  historySearchInput: document.querySelector("#historySearchInput"),
  kindFilter: document.querySelector("#kindFilter"),
  historyGroups: document.querySelector("#historyGroups"),
  backToRoleCardBtn: document.querySelector("#backToRoleCardBtn"),
  closeHistoryBtn: document.querySelector("#closeHistoryBtn"),
  backdrops: Array.from(document.querySelectorAll(".modal-backdrop"))
};

const state = {
  runtimeMode: "大纲驱动",
  session: "sess_demo_001",
  currentEpisode: 1,
  visibleCounts: { 1: episodes[1].stream.length, 2: 0 },
  roleCardOpen: false,
  historyOpen: false,
  currentRoleId: null,
  recentExpanded: false,
  historyKeyword: "",
  historyKind: "all",
  expandedEpisodes: new Set([1])
};

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function getEpisodeData(episode = state.currentEpisode) {
  return episodes[episode];
}

function getVisibleMessages(episode = state.currentEpisode) {
  const episodeData = getEpisodeData(episode);
  return episodeData.stream.slice(0, state.visibleCounts[episode]);
}

function getLastVisibleTurn(episode = state.currentEpisode) {
  const visible = getVisibleMessages(episode);
  if (!visible.length) {
    return 0;
  }
  return visible[visible.length - 1].turn;
}

function getStatusText() {
  const episodeData = getEpisodeData();
  const visibleCount = state.visibleCounts[state.currentEpisode];
  if (!visibleCount) {
    return "等待推演";
  }
  if (visibleCount >= episodeData.stream.length) {
    return "当前集已完成";
  }
  return "推演进行中";
}

function getSceneText() {
  const episodeData = getEpisodeData();
  const visibleCount = state.visibleCounts[state.currentEpisode];
  if (!visibleCount) {
    return {
      title: `第 ${state.currentEpisode} 集尚未开始生成`,
      description: `${episodeData.title} · 准备开始`
    };
  }
  if (visibleCount >= episodeData.stream.length) {
    return {
      title: `第 ${state.currentEpisode} 集已生成完成`,
      description: `${episodeData.title} · 可回滚或进入下一集`
    };
  }
  return {
    title: `第 ${state.currentEpisode} 集生成中`,
    description: `${episodeData.title} · 聊天流持续追加中`
  };
}

function getControlState() {
  const visible = getVisibleMessages();
  const latestDirector = [...visible].reverse().find((item) => item.type === "system" && item.label === "DIRECTOR");
  const visibleCount = state.visibleCounts[state.currentEpisode];
  const totalCount = getEpisodeData().stream.length;

  let title = "当前集尚未开始推进";
  let description = "等待推演";

  if (visibleCount && !latestDirector) {
    title = "继续推演中";
    description = "正在追加当前集输出";
  }
  if (latestDirector) {
    title = "导演指令已介入";
    description = "已将导演指令注入当前集";
  }
  if (visibleCount >= totalCount) {
    title = "当前集推进完成";
    description = "当前集输出已结束";
  }

  return {
    title,
    description,
    actions: [
      { title: "继续推演", detail: "追加下一组输出" },
      { title: "回滚一步", detail: "删除最新一组消息" },
      { title: "开始下一集", detail: "切换到下一集" }
    ]
  };
}

function getMonitorNotes() {
  const notes = getVisibleMessages()
    .filter((item) => item.type === "system" && item.label === "MONITOR")
    .map((item) => item.content);

  if (!notes.length) {
    return ["当前还没有新的监制观察。"];
  }
  return notes;
}

function renderStatusBar() {
  const scene = getSceneText();
  const episodeData = getEpisodeData();
  const visibleCount = state.visibleCounts[state.currentEpisode];

  dom.statusMode.textContent = state.runtimeMode;
  dom.statusSession.textContent = state.session;
  dom.statusState.textContent = getStatusText();
  dom.sceneTitle.textContent = scene.title;
  dom.sceneDescription.textContent = scene.description;
  dom.episodeChip.textContent = `第 ${state.currentEpisode} 集`;
  dom.turnChip.textContent = `最新 Turn ${getLastVisibleTurn()}`;
  dom.progressChip.textContent = `${visibleCount} / ${episodeData.stream.length} 组输出`;

  dom.continueBtn.disabled = visibleCount >= episodeData.stream.length;
  dom.rollbackStepBtn.disabled = visibleCount === 0;
  dom.nextEpisodeActionBtn.disabled = state.currentEpisode >= Object.keys(episodes).length;
}

function renderSideRail() {
  const controlState = getControlState();
  dom.controlStateTitle.textContent = controlState.title;
  dom.controlStateDescription.textContent = controlState.description;
  dom.controlActions.innerHTML = controlState.actions
    .map((action) => `
      <div class="action-chip">
        <strong>${escapeHtml(action.title)}</strong>
        <span>${escapeHtml(action.detail)}</span>
      </div>
    `)
    .join("");

  dom.monitorList.innerHTML = getMonitorNotes()
    .map((note) => `<li>${escapeHtml(note)}</li>`)
    .join("");
}

function renderChatFeed() {
  const visible = getVisibleMessages();

  if (!visible.length) {
    dom.chatFeed.innerHTML = `
      <article class="system-card">
        <div class="system-topline">
          <strong>SYSTEM</strong>
          <span>E${state.currentEpisode} · Turn 0</span>
        </div>
        <div class="system-body">点击“继续推演”开始当前集聊天流。</div>
      </article>
    `;
    return;
  }

  dom.chatFeed.innerHTML = visible
    .map((message) => {
      if (message.type === "system") {
        return `
          <article class="system-card">
            <div class="system-topline">
              <strong>${escapeHtml(message.label)}</strong>
              <span>E${state.currentEpisode} · Turn ${message.turn}</span>
            </div>
            <div class="system-body">${escapeHtml(message.content)}</div>
          </article>
        `;
      }

      const role = roles[message.roleId];
      const segments = message.segments
        .map((segment) => `
          <div class="segment segment-${escapeHtml(segment.kind)}">
            <span class="segment-label">${escapeHtml(segment.kind)}</span>
            <span class="segment-text">${escapeHtml(segment.content)}</span>
          </div>
        `)
        .join("");

      return `
        <article class="chat-role">
          <button class="avatar-btn" type="button" data-role-id="${escapeHtml(role.id)}" style="background:${escapeHtml(role.tone)}" aria-label="查看 ${escapeHtml(role.name)} 的角色卡">
            <span>${escapeHtml(role.initials)}</span>
          </button>
          <div class="message-stack">
            <div class="message-topline">
              <span class="message-name">${escapeHtml(role.name)}</span>
              <span class="message-meta">E${state.currentEpisode} · Turn ${message.turn}</span>
            </div>
            <div class="message-bubble">${segments}</div>
          </div>
        </article>
      `;
    })
    .join("");

  dom.chatFeed.scrollTop = dom.chatFeed.scrollHeight;
}

function buildHistoryRecords() {
  return Object.entries(episodes).flatMap(([episodeKey, episodeData]) =>
    episodeData.stream.flatMap((item) => {
      if (item.type === "role") {
        return item.segments.map((segment) => ({
          episode: Number(episodeKey),
          scene: item.scene,
          turn: item.turn,
          kind: segment.kind,
          roleId: item.roleId,
          content: segment.content
        }));
      }

      return [];
    })
  );
}

const historyRecords = buildHistoryRecords();

function buildCurrentEpisodeRecordsByRole(episode = state.currentEpisode) {
  const recordsByRole = {};
  getVisibleMessages(episode).forEach((item) => {
    if (item.type !== "role") return;
    if (!recordsByRole[item.roleId]) recordsByRole[item.roleId] = [];
    item.segments.forEach((segment, index) => {
      recordsByRole[item.roleId].push({
        event_id: `e${episode}_${item.turn}_${index}`,
        episode,
        scene: item.scene,
        turn: item.turn,
        kind: segment.kind,
        content: segment.content,
      });
    });
  });
  Object.keys(recordsByRole).forEach((roleId) => {
    recordsByRole[roleId].sort((left, right) => right.turn - left.turn);
  });
  return recordsByRole;
}

function getCurrentRole() {
  return roles[state.currentRoleId] || null;
}

function getVisibleRoleRecords(roleId, episode) {
  return getVisibleMessages(episode)
    .filter((item) => item.type === "role" && item.roleId === roleId)
    .flatMap((item) =>
      item.segments.map((segment, index) => ({
        episode,
        scene: item.scene,
        turn: item.turn,
        kind: segment.kind,
        sortKey: item.turn * 10 + index,
        content: segment.content
      }))
    )
    .sort((a, b) => b.sortKey - a.sortKey);
}

function renderRoleCard() {
  const role = getCurrentRole();
  const roleProfile = roleProfiles[state.currentRoleId];
  const isOpen = state.roleCardOpen && !!role;
  dom.roleCardShell.classList.toggle("hidden", !isOpen);
  dom.roleCardShell.setAttribute("aria-hidden", String(!isOpen));

  if (!isOpen) {
    return;
  }

  const recordsByRole = buildCurrentEpisodeRecordsByRole(state.currentEpisode);
  const records = recordsByRole[role.id] || getVisibleRoleRecords(role.id, state.currentEpisode);
  const visibleRecords = state.recentExpanded ? records : records.slice(0, 5);

  dom.roleCardTitle.textContent = `${roleProfile?.static_profile?.name || role.name} · 角色卡`;
  dom.roleCardAvatar.style.background = role.tone;
  dom.roleCardAvatar.textContent = role.initials;
  dom.roleCardName.textContent = roleProfile?.static_profile?.name || role.name;
  dom.roleCardIdentity.textContent = roleProfile?.static_profile?.identity || role.identity;
  dom.roleCardSummary.textContent = roleProfile?.dynamic_profile?.current_goal || role.summary;
  dom.recentRecordsHint.textContent = `第 ${state.currentEpisode} 集 · 最新在上`;
  dom.expandRecentBtn.classList.toggle("hidden", records.length <= 5 || state.recentExpanded);
  dom.staticTagList.innerHTML = (roleProfile?.static_profile?.appearance_tags || role.staticTags)
    .map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`)
    .join("");
  dom.dynamicTagList.innerHTML = role.dynamicTags.map((tag) => `<span class="tag dynamic">${escapeHtml(tag)}</span>`).join("");

  if (!visibleRecords.length) {
    dom.recentRecordList.innerHTML = `<div class="empty-state">当前集还没有 ${escapeHtml(role.name)} 的输出。</div>`;
    return;
  }

  dom.recentRecordList.innerHTML = visibleRecords
    .map((record) => `
      <article class="record-item">
        <div class="record-meta">
          <span>E${record.episode}</span>
          <span>${escapeHtml(record.scene)}</span>
          <span>Turn ${record.turn}</span>
          <span class="record-kind">${escapeHtml(record.kind)}</span>
        </div>
        <div class="record-content">${escapeHtml(record.content)}</div>
      </article>
    `)
    .join("");
}

function getFilteredHistory(roleId) {
  const keyword = state.historyKeyword.trim().toLowerCase();
  const records = historyRecords.filter((record) => {
    const roleMatches = record.roleId === roleId;
    const kindMatches = state.historyKind === "all" || record.kind === state.historyKind;
    const keywordMatches = !keyword || record.content.toLowerCase().includes(keyword);
    return roleMatches && kindMatches && keywordMatches;
  });

  const grouped = new Map();
  records.forEach((record) => {
    if (!grouped.has(record.episode)) {
      grouped.set(record.episode, []);
    }
    grouped.get(record.episode).push(record);
  });

  return [...grouped.entries()]
    .sort((a, b) => b[0] - a[0])
    .map(([episode, groupRecords]) => ({
      episode,
      records: groupRecords.sort((a, b) => b.turn - a.turn)
    }));
}

function renderKindFilter() {
  const options = [
    { key: "all", label: "全部" },
    { key: "thought", label: "thought" },
    { key: "action", label: "action" },
    { key: "dialogue", label: "dialogue" }
  ];

  dom.kindFilter.innerHTML = options
    .map((option) => `
      <button class="kind-btn ${option.key === state.historyKind ? "active" : ""}" data-kind="${escapeHtml(option.key)}" type="button">
        ${escapeHtml(option.label)}
      </button>
    `)
    .join("");
}

function renderHistory() {
  const role = getCurrentRole();
  const isOpen = state.historyOpen && !!role;
  dom.historyShell.classList.toggle("hidden", !isOpen);
  dom.historyShell.setAttribute("aria-hidden", String(!isOpen));

  if (!isOpen) {
    return;
  }

  dom.historySubtitle.textContent = `${role.name} · 按集查看完整聊天记录`;
  dom.historySearchInput.value = state.historyKeyword;
  renderKindFilter();

  const groups = getFilteredHistory(role.id);
  if (!groups.length) {
    dom.historyGroups.innerHTML = `<div class="empty-state">没有符合条件的聊天记录。</div>`;
    return;
  }

  dom.historyGroups.innerHTML = groups
    .map((group) => {
      const isExpanded = state.expandedEpisodes.has(group.episode);
      return `
        <section class="episode-group">
          <div class="episode-head">
            <div class="episode-summary">
              <h3>第 ${group.episode} 集</h3>
              <p>${group.records.length} 条记录</p>
            </div>
            <button class="episode-toggle ${isExpanded ? "active" : ""}" data-episode="${group.episode}" type="button">
              ${isExpanded ? "收起" : "展开"}
            </button>
          </div>
          ${isExpanded
            ? group.records
                .map((record) => `
                  <article class="history-item">
                    <div class="history-item-meta">
                      <span>E${record.episode}</span>
                      <span>${escapeHtml(record.scene)}</span>
                      <span>Turn ${record.turn}</span>
                      <span class="history-item-kind">${escapeHtml(record.kind)}</span>
                    </div>
                    <div class="history-item-content">${escapeHtml(record.content)}</div>
                  </article>
                `)
                .join("")
            : ""}
        </section>
      `;
    })
    .join("");
}

function render() {
  renderStatusBar();
  renderSideRail();
  renderChatFeed();
  renderRoleCard();
  renderHistory();
}

function continueEpisode() {
  const episodeData = getEpisodeData();
  if (state.visibleCounts[state.currentEpisode] >= episodeData.stream.length) {
    return;
  }
  state.visibleCounts[state.currentEpisode] += 1;
  render();
}

function rollbackEpisode() {
  if (state.visibleCounts[state.currentEpisode] === 0) {
    return;
  }
  state.visibleCounts[state.currentEpisode] -= 1;
  render();
}

function nextEpisode() {
  const nextEpisodeNumber = state.currentEpisode + 1;
  if (!episodes[nextEpisodeNumber]) {
    return;
  }
  state.currentEpisode = nextEpisodeNumber;
  state.expandedEpisodes = new Set([state.currentEpisode]);
  render();
}

function openRoleCard(roleId) {
  state.currentRoleId = roleId;
  state.roleCardOpen = true;
  state.historyOpen = false;
  state.recentExpanded = false;
  state.expandedEpisodes = new Set([state.currentEpisode]);
  renderRoleCard();
  renderHistory();
}

function closeRoleCard() {
  state.roleCardOpen = false;
  renderRoleCard();
}

function openHistory() {
  state.historyOpen = true;
  renderHistory();
}

function closeHistory() {
  state.historyOpen = false;
  renderHistory();
}

dom.continueBtn.addEventListener("click", continueEpisode);
dom.rollbackStepBtn.addEventListener("click", rollbackEpisode);
dom.nextEpisodeActionBtn.addEventListener("click", nextEpisode);

dom.chatFeed.addEventListener("click", (event) => {
  const avatarButton = event.target.closest("[data-role-id]");
  if (!avatarButton) {
    return;
  }
  openRoleCard(avatarButton.dataset.roleId);
});

dom.closeRoleCardBtn.addEventListener("click", closeRoleCard);
dom.openHistoryBtn.addEventListener("click", openHistory);
dom.expandRecentBtn.addEventListener("click", () => {
  state.recentExpanded = true;
  renderRoleCard();
});
dom.closeHistoryBtn.addEventListener("click", closeHistory);
dom.backToRoleCardBtn.addEventListener("click", closeHistory);

dom.historySearchInput.addEventListener("input", (event) => {
  state.historyKeyword = event.target.value;
  renderHistory();
});

dom.kindFilter.addEventListener("click", (event) => {
  const button = event.target.closest("[data-kind]");
  if (!button) {
    return;
  }
  state.historyKind = button.dataset.kind;
  renderHistory();
});

dom.historyGroups.addEventListener("click", (event) => {
  const button = event.target.closest("[data-episode]");
  if (!button) {
    return;
  }
  const episode = Number(button.dataset.episode);
  if (state.expandedEpisodes.has(episode)) {
    state.expandedEpisodes.delete(episode);
  } else {
    state.expandedEpisodes.add(episode);
  }
  renderHistory();
});

dom.backdrops.forEach((backdrop) => {
  backdrop.addEventListener("click", () => {
    const target = backdrop.dataset.close;
    if (target === "role-card") {
      closeRoleCard();
    }
    if (target === "history") {
      closeHistory();
    }
  });
});

render();
