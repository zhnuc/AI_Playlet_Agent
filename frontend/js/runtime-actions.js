(function attachRuntimeActions(global) {
  function createRuntimeActions(deps) {
    const {
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
      buildConfigOverride
    } = deps;

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
        const detail = payload?.detail || response.statusText || "Request failed";
        throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
      }
      return payload;
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
        setStatus("Free session created");
        renderOutline();
        setApiPreview("Created free session", payload);
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
      setStatus("Planned session created");
      setApiPreview("Created planned session", payload);
      return payload.session_id;
    }

    async function generateOutline() {
      if (state.runMode === "free") {
        await createSession(true);
        renderOutline();
        setStage(2, { force: true });
        setStatus("Free mode plan is ready");
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
        setStatus("Outline generation failed");
        setApiPreview("Outline generation failed", payload);
        return;
      }
      state.plannerOutput = payload.planner_output;
      state.outlineApproved = false;
      renderOutline();
      setStage(2, { force: true });
      setStatus("Outline generated");
      setApiPreview("Planner output generated", payload);
    }

    async function reviewOutline() {
      if (state.runMode === "free") {
        setStatus("Free mode does not require review");
        return;
      }
      if (!state.sessionId) {
        await generateOutline();
      }
      const feedback = dom.outlineFeedback.value.trim();
      if (!feedback) {
        setStatus("Feedback is required");
        return;
      }
      const payload = await request(`/sessions/${state.sessionId}/outline/review`, {
        method: "POST",
        body: { feedback }
      });
      state.plannerOutput = payload.planner_output;
      state.outlineApproved = false;
      renderOutline();
      setStatus("Outline reviewed");
      setApiPreview("Outline review completed", payload);
    }

    async function approveOutline() {
      if (state.runMode === "free") {
        state.outlineApproved = true;
        setStatus("Free mode is auto-approved");
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
      setStage(2, { force: true });
      setStatus("Outline approved");
      setApiPreview("Outline approved", payload);
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
      setStatus("Episode runtime started");
      setApiPreview("Episode runtime created", payload);
    }

    async function stepEpisode() {
      const payload = await request(`/sessions/${state.sessionId}/episode/step`, {
        method: "POST"
      });
      applySnapshot(payload.snapshot);
      setApiPreview("Episode advanced one step", payload);

      const stepStatus = payload.step_result?.status;
      if (state.snapshot?.result) {
        const statusMap = {
          ended: "ended",
          director_cut: "director_cut",
          max_turns_reached: "max_turns_reached",
          handoff: "handoff",
          api_error: "api_error",
          format_error: "format_error",
          key_error: "key_error"
        };
        const resolved = statusMap[state.snapshot.result.status] || state.snapshot.result.status;
        setStatus(`Episode ended: ${resolved}`);
        state.shouldContinue = false;
      } else if (stepStatus === "paused") {
        setStatus("Episode paused");
        state.shouldContinue = false;
      } else {
        setStatus(`Running: turn ${state.snapshot?.current_turn ?? 0}`);
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
        setStage(3, { force: true });
        await startEpisode();
        state.shouldContinue = true;
        await driveEpisodeLoop();
      } catch (error) {
        state.shouldContinue = false;
        setStatus("Quick start failed");
        setApiPreview("Quick start failed", { error: error.message });
      }
    }

    async function continueScene() {
      try {
        setStage(3, { force: true });
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
          setApiPreview("Episode runtime resumed", payload);
        }

        state.shouldContinue = true;
        await driveEpisodeLoop();
      } catch (error) {
        setStatus("Continue failed");
        setApiPreview("Continue failed", { error: error.message });
      }
    }

    async function startNextEpisode() {
      try {
        if (!state.sessionId || !state.snapshot || !state.plannerOutput?.episodes?.length) {
          setStatus("Start current episode first");
          return;
        }
        const currentEpisode = getCurrentEpisodeNumber(state.snapshot);
        const nextEpisode = currentEpisode + 1;
        if (nextEpisode > state.plannerOutput.episodes.length) {
          setStatus("Already at final episode");
          return;
        }

        const payload = await request(`/sessions/${state.sessionId}/episode/start`, {
          method: "POST",
          body: { episode: nextEpisode }
        });
        applySnapshot(payload);
        setStatus(`Started episode ${nextEpisode}`);
        setApiPreview("Switched to next episode", payload);
        state.shouldContinue = true;
        await driveEpisodeLoop();
      } catch (error) {
        setApiPreview("Start next episode failed", { error: error.message });
      }
    }

    async function cutScene() {
      if (!state.sessionId || !state.snapshot) {
        setStatus("No active runtime");
        return;
      }
      try {
        state.shouldContinue = false;
        const payload = await request(`/sessions/${state.sessionId}/director`, {
          method: "POST",
          body: { command: "pause" }
        });
        applySnapshot(payload.snapshot);
        setStatus("Episode paused");
        setApiPreview("Pause command completed", payload);
      } catch (error) {
        setApiPreview("Pause command failed", { error: error.message });
      }
    }

    async function sendDirective() {
      if (!state.sessionId || !state.snapshot) {
        setStatus("Start runtime first");
        return;
      }
      const instruction = dom.directorCommand.value.trim();
      if (!instruction) {
        setStatus("Directive is required");
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
        setStatus("Directive injected");
        setApiPreview("Directive injected", payload);
      } catch (error) {
        setApiPreview("Directive injection failed", { error: error.message });
      }
    }

    async function rollbackScene() {
      if (!state.sessionId || !state.snapshot) {
        setStatus("No runtime to rollback");
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
        setStatus(`Rolled back to step ${dom.timelineSlider.value}`);
        setApiPreview("Rollback completed", payload);
      } catch (error) {
        setApiPreview("Rollback failed", { error: error.message });
      }
    }

    async function exportArtifacts() {
      if (!state.sessionId) {
        setStatus("No session");
        return;
      }
      try {
        const payload = await request(`/sessions/${state.sessionId}/export`, {
          method: "POST"
        });
        state.hasExportedArtifacts = true;
        setStage(4, { force: true });
        dom.scriptOutput.textContent = payload.script || "No script output.";
        setApiPreview("Artifacts exported", payload.shotlist || payload);
        setStatus("Export completed");
      } catch (error) {
        setApiPreview("Export failed", { error: error.message });
      }
    }

    function previewCurrentState() {
      setApiPreview("Current frontend snapshot", {
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
      syncRuntimeStatus();
    }

    return {
      createSession,
      generateOutline,
      reviewOutline,
      approveOutline,
      startEpisode,
      stepEpisode,
      driveEpisodeLoop,
      quickStart,
      continueScene,
      startNextEpisode,
      cutScene,
      sendDirective,
      rollbackScene,
      exportArtifacts,
      previewCurrentState,
      refreshStage
    };
  }

  global.createRuntimeActions = createRuntimeActions;
})(window);
