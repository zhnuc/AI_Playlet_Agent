(function attachWorkflowMode(global) {
  function initWorkflowMode(deps) {
    const {
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
    } = deps;

    const config = global.PLAYLET_CONFIG || {};
    const genreOptions = Array.isArray(config.options?.genre) ? config.options.genre : [];

    const modeSelectPanel = document.querySelector("#modeSelectPanel");
    const stageToolbar = document.querySelector(".stage-toolbar");
    const workspaceGrid = document.querySelector(".workspace-grid");
    const stageFooter = document.querySelector(".stage-footer-nav");

    const freeCard = document.querySelector("#modeFreeCard");
    const plannedCard = document.querySelector("#modePlannedCard");
    const bgCard = document.querySelector("#backgroundSetupCard");
    const roleCard = document.querySelector("#roleSetupCard");
    const confirmBgBtn = document.querySelector("#confirmBackgroundBtn");
    const confirmRoleBtn = document.querySelector("#confirmRoleSetupBtn");
    const oneLineBgBtn = document.querySelector("#oneLineBackgroundBtn");
    const oneLineRoleBtn = document.querySelector("#oneLineRoleBtn");

    const oneLineModal = document.querySelector("#oneLineModal");
    const oneLineModalBackdrop = document.querySelector("#oneLineModalBackdrop");
    const closeOneLineModalBtn = document.querySelector("#closeOneLineModalBtn");
    const confirmOneLineBtn = document.querySelector("#confirmOneLineBtn");
    const oneLineInput = document.querySelector("#oneLineInput");
    const oneLineTitle = document.querySelector("#oneLineTitle");

    const downloadScriptBtn = document.querySelector("#downloadScriptBtn");

    let oneLineTarget = "background";

    function genRoleId() {
      return `role-${Date.now()}-${Math.floor(Math.random() * 100000)}`;
    }

    function normalizeTagList(value, fallback) {
      if (Array.isArray(value)) {
        const cleaned = value.map((item) => String(item || "").trim()).filter(Boolean);
        return cleaned.length ? cleaned : fallback;
      }
      return fallback;
    }

    function appendGeneratedRoles(roleItems) {
      if (!Array.isArray(roleItems) || !roleItems.length) return 0;
      const next = roleItems.slice(0, 5).map((item) => ({
        id: genRoleId(),
        isStarter: false,
        templateGroup: "support",
        templateId: null,
        name: String(item.name || "新角色").trim() || "新角色",
        role_type: "配角",
        role_position: String(item.role_position || "supporting").trim() || "supporting",
        gender: String(item.gender || "未设定").trim() || "未设定",
        age: Number(item.age || 20),
        identity: String(item.identity || "待设定身份").trim() || "待设定身份",
        appearance_tags: normalizeTagList(item.appearance_tags, ["待补充"]),
        personality_tags: normalizeTagList(item.personality_tags, ["待补充"])
      }));
      state.roleDrafts = [...next, ...state.roleDrafts];
      refreshRoleUI();
      return next.length;
    }

    function setWorkbenchVisible(visible) {
      const method = visible ? "remove" : "add";
      if (stageToolbar) stageToolbar.classList[method]("hidden");
      if (workspaceGrid) workspaceGrid.classList[method]("hidden");
      if (stageFooter) stageFooter.classList[method]("hidden");
    }

    function getStepButton(target) {
      return document.querySelector(`.stage-step[data-stage-target="${target}"]`);
    }

    function applyModeStageView() {
      const step2 = getStepButton(2);
      const step3 = getStepButton(3);
      const step4 = getStepButton(4);
      if (!step2 || !step3 || !step4) return;

      if (state.runMode === "free") {
        step2.classList.add("hidden");
        step3.querySelector(".stage-step-index").textContent = "2";
        step3.querySelector(".stage-step-label").textContent = "阶段 2";
        step4.querySelector(".stage-step-index").textContent = "3";
        step4.querySelector(".stage-step-label").textContent = "阶段 3";
      } else {
        step2.classList.remove("hidden");
        step3.querySelector(".stage-step-index").textContent = "3";
        step3.querySelector(".stage-step-label").textContent = "阶段 3";
        step4.querySelector(".stage-step-index").textContent = "4";
        step4.querySelector(".stage-step-label").textContent = "阶段 4";
      }
    }

    function chooseMode(mode) {
      state.runMode = mode;
      if (dom.modeBadge) dom.modeBadge.textContent = mode === "free" ? "自由开场" : "大纲驱动";
      if (dom.runModeResult) dom.runModeResult.textContent = mode === "free" ? "自由开场" : "大纲驱动";
      if (modeSelectPanel) modeSelectPanel.classList.add("hidden");
      setWorkbenchVisible(true);
      applyModeStageView();
      renderAllChips();
      setStage(1, { force: true });
      setStatus(mode === "free" ? "自由开场模式已选择" : "大纲驱动模式已选择");
    }

    function openOneLineModal(target) {
      oneLineTarget = target;
      if (oneLineTitle) {
        oneLineTitle.textContent = target === "background" ? "一句话背景" : "一句话角色";
      }
      if (oneLineInput) oneLineInput.value = "";
      if (oneLineModal) oneLineModal.classList.remove("hidden");
    }

    function closeOneLineModal() {
      if (oneLineModal) oneLineModal.classList.add("hidden");
    }

    async function request(path, body) {
      const response = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body || {})
      });
      const text = await response.text();
      const payload = text ? JSON.parse(text) : {};
      if (!response.ok) {
        throw new Error(payload?.detail || "request failed");
      }
      return payload;
    }

    function localFallbackBackground(text) {
      const value = String(text || "").trim();
      if (!value) return;
      if (dom.plotInput) dom.plotInput.value = value;
      if (dom.sceneInput && !dom.sceneInput.value.trim()) dom.sceneInput.value = "会议室";
      if (dom.sceneResult) dom.sceneResult.textContent = dom.sceneInput?.value || "会议室";
      if (genreOptions.length > 0) {
        state.selectedGenre = genreOptions[0];
        if (dom.genreResult) dom.genreResult.textContent = genreOptions[0];
      }
      updateEpisodeCountDisplay();
      renderAllChips();
    }

    function localFallbackRole(text) {
      const value = String(text || "").trim();
      if (!value) return;
      appendGeneratedRoles([
        {
          name: "新角色",
          role_position: "supporting",
          gender: "未设定",
          age: 20,
          identity: value.slice(0, 80),
          appearance_tags: ["待补充"],
          personality_tags: ["待补充"]
        }
      ]);
    }

    async function handleConfirmOneLine() {
      const value = oneLineInput?.value || "";
      const targetLabel = oneLineTarget === "background" ? "背景卡片" : "角色卡片";
      if (typeof showLoading === "function") {
        showLoading({
          title: `正在生成${targetLabel}，请稍等`,
          hint: "模型正在根据你的一句话组织可直接填充的结构化内容。"
        });
      }
      try {
        if (oneLineTarget === "background") {
          const payload = await request("/assist/one-line/background", { text: value });
          const result = payload?.result || {};

          if (typeof result.genre === "string" && result.genre.trim()) {
            state.selectedGenre = result.genre.trim();
            if (dom.genreResult) dom.genreResult.textContent = state.selectedGenre;
          }
          if (typeof result.scene === "string" && result.scene.trim()) {
            if (dom.sceneInput) dom.sceneInput.value = result.scene.trim();
            if (dom.sceneResult) dom.sceneResult.textContent = result.scene.trim();
          }
          if (typeof result.logline === "string" && result.logline.trim() && dom.plotInput) {
            dom.plotInput.value = result.logline.trim();
          }
          const episodes = Number(result.expected_episodes);
          if (Number.isFinite(episodes) && dom.episodeCount) {
            dom.episodeCount.value = String(Math.max(1, Math.min(20, episodes)));
          }
          updateEpisodeCountDisplay();
          renderAllChips();
          setStatus("背景卡片已由模型生成");
        } else {
          const payload = await request("/assist/one-line/role", { text: value });
          const result = payload?.result || {};
          const roles = Array.isArray(result.roles) ? result.roles : [];
          const count = appendGeneratedRoles(roles);
          if (count > 0) {
            setStatus(`已新增 ${count} 个角色`);
          }
        }
      } catch (error) {
        if (oneLineTarget === "background") {
          localFallbackBackground(value);
        } else {
          localFallbackRole(value);
        }
        setApiPreview("一句话生成回退为本地规则", { error: error.message });
      } finally {
        if (typeof hideLoading === "function") hideLoading();
        closeOneLineModal();
      }
    }

    function setupDownload() {
      if (!downloadScriptBtn) return;
      downloadScriptBtn.addEventListener("click", () => {
        const content = dom.scriptOutput?.textContent || "";
        const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `playlet_script_${new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-")}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      });
    }

    if (freeCard) freeCard.addEventListener("click", () => chooseMode("free"));
    if (plannedCard) plannedCard.addEventListener("click", () => chooseMode("planned"));
    if (confirmBgBtn) {
      confirmBgBtn.addEventListener("click", () => {
        if (bgCard) bgCard.classList.add("hidden");
        if (roleCard) roleCard.classList.remove("hidden");
      });
    }
    if (confirmRoleBtn) {
      confirmRoleBtn.addEventListener("click", () => {
        if (state.runMode === "free") {
          setStage(3, { force: true });
        } else {
          setStage(2, { force: true });
        }
      });
    }
    if (oneLineBgBtn) oneLineBgBtn.addEventListener("click", () => openOneLineModal("background"));
    if (oneLineRoleBtn) oneLineRoleBtn.addEventListener("click", () => openOneLineModal("role"));
    if (closeOneLineModalBtn) closeOneLineModalBtn.addEventListener("click", closeOneLineModal);
    if (oneLineModalBackdrop) oneLineModalBackdrop.addEventListener("click", closeOneLineModal);
    if (confirmOneLineBtn) confirmOneLineBtn.addEventListener("click", handleConfirmOneLine);

    setupDownload();

    setWorkbenchVisible(false);

    global.__onStageChanged = async (stage) => {
      if (stage === 4 && !state.hasExportedArtifacts) {
        try {
          await raExportArtifacts();
        } catch (error) {
          setApiPreview("自动导出失败", { error: error.message });
        }
      }
    };
  }

  global.initWorkflowMode = initWorkflowMode;
})(window);
