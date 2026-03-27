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

    const on = (selector, event, handler) => {
      const el = document.querySelector(selector);
      if (el) el.addEventListener(event, handler);
    };

    on("#randomizeAll", "click", randomizeAll);
    on("#optimizeInput", "click", optimizeInput);
    on("#episodeCount", "input", updateEpisodeCountDisplay);
    on("#roundLimit", "input", updateRoundDisplay);
    on("#timelineSlider", "input", updateTimelineDisplay);

    if (dom.openRoleDesignerBtn) dom.openRoleDesignerBtn.addEventListener("click", openRoleDesigner);
    if (dom.closeRoleDesignerBtn) dom.closeRoleDesignerBtn.addEventListener("click", closeRoleDesigner);
    if (dom.roleDesignerModal) {
      dom.roleDesignerModal.addEventListener("click", (event) => {
        if (event.target instanceof HTMLElement && event.target.dataset.closeRoleModal === "true") {
          closeRoleDesigner();
        }
      });
    }
    if (dom.addPresetRoleBtn) dom.addPresetRoleBtn.addEventListener("click", addPresetRole);
    if (dom.addCustomRoleBtn) dom.addCustomRoleBtn.addEventListener("click", addCustomRole);
    if (dom.roleDesignerList) {
      dom.roleDesignerList.addEventListener("input", handleRoleDesignerInput);
      dom.roleDesignerList.addEventListener("change", handleRoleDesignerChange);
      dom.roleDesignerList.addEventListener("click", handleRoleDesignerClick);
    }

    on("#generateOutlineBtn", "click", () => raGenerateOutline().catch((error) => setApiPreview("大纲生成失败", { error: error.message })));
    on("#reviewOutlineBtn", "click", () => raReviewOutline().catch((error) => setApiPreview("审稿失败", { error: error.message })));
    on("#approveOutlineBtn", "click", () => raApproveOutline().catch((error) => setApiPreview("审核通过失败", { error: error.message })));

    on("#startDemo", "click", async () => {
      if (state.hasTriggeredStartDemo) return;
      state.hasTriggeredStartDemo = true;
      if (dom.startDemoBtn) dom.startDemoBtn.disabled = true;
      try {
        await raQuickStart();
      } catch (error) {
        setApiPreview("推演启动失败", { error: error.message });
      }
    });

    on("#continueScene", "click", raContinueScene);
    on("#nextEpisodeBtn", "click", raStartNextEpisode);
    on("#cutScene", "click", raCutScene);
    on("#sendDirective", "click", raSendDirective);
    on("#rollbackBtn", "click", raRollbackScene);
    on("#formatScript", "click", raExportArtifacts);
    on("#previewStateBtn", "click", raPreviewCurrentState);
    on("#refreshStageBtn", "click", raRefreshStage);
    on("#resetSessionBtn", "click", resetSessionState);

    if (dom.stageSteps) {
      dom.stageSteps.forEach((button) => {
        button.addEventListener("click", () => {
          const targetStage = Number(button.dataset.stageTarget || "1");
          setStage(targetStage);
        });
      });
    }

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

