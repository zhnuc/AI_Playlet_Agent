(function attachBindEvents(global) {
  function bindFrontendEvents(deps) {
    const {
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
      raStartNextEpisode,
      raCutScene,
      raSendDirective,
      raRollbackScene,
      raExportArtifacts,
      raPreviewCurrentState,
      raRefreshStage
    } = deps;

    dom.randomizeAll = document.querySelector("#randomizeAll");
    document.querySelector("#randomizeAll").addEventListener("click", randomizeAll);
    document.querySelector("#optimizeInput").addEventListener("click", optimizeInput);
    document.querySelector("#episodeCount").addEventListener("input", updateEpisodeCountDisplay);
    document.querySelector("#roundLimit").addEventListener("input", updateRoundDisplay);
    document.querySelector("#timelineSlider").addEventListener("input", updateTimelineDisplay);
    dom.openRoleDesignerBtn.addEventListener("click", openRoleDesigner);
    document.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      const trigger = target.closest("#openRoleDesignerBtn");
      if (!trigger) return;
      event.preventDefault();
      openRoleDesigner();
    });
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
    document.querySelector("#generateOutlineBtn").addEventListener("click", () => raGenerateOutline().catch((error) => setApiPreview("生成大纲失败。", { error: error.message })));
    document.querySelector("#reviewOutlineBtn").addEventListener("click", () => raReviewOutline().catch((error) => setApiPreview("审稿失败。", { error: error.message })));
    document.querySelector("#approveOutlineBtn").addEventListener("click", () => raApproveOutline().catch((error) => setApiPreview("审核通过失败。", { error: error.message })));
    document.querySelector("#buildFreePlanBtn").addEventListener("click", () => {
      state.runMode = "free";
      syncStageNav();
      dom.runModeResult.textContent = "自由开场";
      dom.modeBadge.textContent = "自由开场";
      renderAllChips();
      raGenerateOutline().catch((error) => setApiPreview("生成最小 episode plan 失败。", { error: error.message }));
    });
    document.querySelector("#startDemo").addEventListener("click", async () => {
      if (state.hasTriggeredStartDemo) return;
      state.hasTriggeredStartDemo = true;
      if (dom.startDemoBtn) dom.startDemoBtn.disabled = true;
      try {
        await raQuickStart();
      } catch (error) {
        setApiPreview("推演启动失败", { error: error.message });
      }
    });
    document.querySelector("#continueScene").addEventListener("click", raContinueScene);
    document.querySelector("#nextEpisodeBtn").addEventListener("click", raStartNextEpisode);
    document.querySelector("#cutScene").addEventListener("click", raCutScene);
    document.querySelector("#sendDirective").addEventListener("click", raSendDirective);
    document.querySelector("#rollbackBtn").addEventListener("click", raRollbackScene);
    document.querySelector("#formatScript").addEventListener("click", raExportArtifacts);
    document.querySelector("#previewStateBtn").addEventListener("click", raPreviewCurrentState);
    document.querySelector("#refreshStageBtn").addEventListener("click", raRefreshStage);
    document.querySelector("#resetSessionBtn").addEventListener("click", resetSessionState);
    dom.stageSteps.forEach((button) => {
      button.addEventListener("click", () => {
        const targetStage = Number(button.dataset.stageTarget || "1");
        setStage(targetStage);
      });
    });
    if (dom.stagePrevBtn) {
      dom.stagePrevBtn.addEventListener("click", () => setStage(state.currentStage - 1));
    }
    if (dom.stageNextBtn) {
      dom.stageNextBtn.addEventListener("click", () => setStage(state.currentStage + 1));
    }
    window.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && state.roleDesignerOpen) {
        closeRoleDesigner();
      }
    });
  }

  global.bindFrontendEvents = bindFrontendEvents;
})(window);
