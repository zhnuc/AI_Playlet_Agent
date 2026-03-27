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
      buildConfigOverride,
      showLoading,
      hideLoading
    } = deps;
    let loopRunId = 0;

    async function withLoading(options, runner) {
      if (typeof showLoading === "function") showLoading(options);
      try {
        return await runner();
      } finally {
        if (typeof hideLoading === "function") hideLoading();
      }
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
        setStatus("自由模式会话已创建");
        renderOutline();
        setApiPreview("自由模式会话创建成功", payload);
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
      setStatus("大纲模式会话已创建");
      setApiPreview("大纲模式会话创建成功", payload);
      return payload.session_id;
    }

    async function generateOutline() {
      return withLoading(
        {
          title: "正在生成大纲，请稍等几分钟",
          hint: "模型会先规划分集冲突，再写角色 directive。"
        },
        async () => {
          if (state.runMode === "free") {
            await createSession(true);
            renderOutline();
            setStage(2, { force: true });
            setStatus("自由模式规划已就绪");
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
            setApiPreview("大纲生成失败", payload);
            return;
          }
          state.plannerOutput = payload.planner_output;
          state.outlineApproved = false;
          renderOutline();
          setStage(2, { force: true });
          setStatus("大纲已生成");
          setApiPreview("大纲生成完成", payload);
        }
      );
    }

    async function reviewOutline() {
      if (state.runMode === "free") {
        setStatus("自由模式无需审稿");
        return;
      }
      if (!state.sessionId) {
        await generateOutline();
      }
      const feedback = dom.outlineFeedback.value.trim();
      if (!feedback) {
        setStatus("请先填写审稿意见");
        return;
      }
      const payload = await request(`/sessions/${state.sessionId}/outline/review`, {
        method: "POST",
        body: { feedback }
      });
      state.plannerOutput = payload.planner_output;
      state.outlineApproved = false;
      renderOutline();
      setStatus("审稿意见已提交");
      setApiPreview("大纲审稿完成", payload);
    }

    async function approveOutline() {
      if (state.runMode === "free") {
        state.outlineApproved = true;
        setStatus("自由模式默认已通过");
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
      setStage(3, { force: true });
      setStatus("大纲审核通过");
      setApiPreview("大纲审核通过", payload);
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
      setStatus("第一集推演已启动");
      setApiPreview("推演运行时已创建", payload);
    }

    async function stepEpisode(runId) {
      const payload = await request(`/sessions/${state.sessionId}/episode/step`, {
        method: "POST"
      });
      if (runId !== loopRunId) return;
      applySnapshot(payload.snapshot);
      setApiPreview("推演前进一步", payload);

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
        setStatus(`本集结束：${resolved}`);
        state.shouldContinue = false;
      } else if (stepStatus === "paused") {
        setStatus("当前已暂停");
        state.shouldContinue = false;
      } else {
        setStatus(`推演进行中：第 ${state.snapshot?.current_turn ?? 0} 轮`);
      }
    }

    async function driveEpisodeLoop(runId) {
      if (state.isLooping || !state.sessionId) {
        return;
      }

      state.isLooping = true;
      try {
        while (state.shouldContinue && runId === loopRunId) {
          await stepEpisode(runId);
          if (
            runId !== loopRunId
            || !state.shouldContinue
            || state.snapshot?.result
            || state.snapshot?.episode_status === "paused"
          ) {
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
        loopRunId += 1;
        await driveEpisodeLoop(loopRunId);
      } catch (error) {
        state.shouldContinue = false;
        setStatus("快速启动失败");
        setApiPreview("快速启动失败", { error: error.message });
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
          setApiPreview("推演已恢复", payload);
        }

        state.shouldContinue = true;
        loopRunId += 1;
        await driveEpisodeLoop(loopRunId);
      } catch (error) {
        setStatus("继续推演失败");
        setApiPreview("继续推演失败", { error: error.message });
      }
    }

    async function startNextEpisode() {
      try {
        if (!state.sessionId || !state.snapshot || !state.plannerOutput?.episodes?.length) {
          setStatus("请先启动当前集");
          return;
        }
        const currentEpisode = getCurrentEpisodeNumber(state.snapshot);
        const nextEpisode = currentEpisode + 1;
        if (nextEpisode > state.plannerOutput.episodes.length) {
          setStatus("已经是最后一集");
          return;
        }

        const payload = await request(`/sessions/${state.sessionId}/episode/start`, {
          method: "POST",
          body: { episode: nextEpisode }
        });
        applySnapshot(payload);
        setStatus(`已切换到第 ${nextEpisode} 集`);
        setApiPreview("已切换到下一集", payload);
        state.shouldContinue = true;
        loopRunId += 1;
        await driveEpisodeLoop(loopRunId);
      } catch (error) {
        setApiPreview("启动下一集失败", { error: error.message });
      }
    }

    async function cutScene() {
      if (!state.sessionId || !state.snapshot) {
        setStatus("当前没有可暂停的推演");
        return;
      }
      state.shouldContinue = false;
      loopRunId += 1;
      setStatus("暂停中，正在等待当前步骤收束");
      try {
        await withLoading(
          {
            title: "正在暂停推演",
            hint: "马上暂停，不再继续自动输出。"
          },
          async () => {
            const payload = await request(`/sessions/${state.sessionId}/director`, {
              method: "POST",
              body: { command: "pause" }
            });
            applySnapshot(payload.snapshot);
            setStatus("已暂停");
            setApiPreview("暂停指令执行完成", payload);
          }
        );
      } catch (error) {
        setApiPreview("暂停失败", { error: error.message });
      }
    }

    async function sendDirective() {
      if (!state.sessionId || !state.snapshot) {
        setStatus("请先启动推演");
        return;
      }
      const instruction = dom.directorCommand.value.trim();
      if (!instruction) {
        setStatus("请输入导演指令");
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
        setStatus("导演指令已注入");
        setApiPreview("导演指令注入完成", payload);
      } catch (error) {
        setApiPreview("导演指令注入失败", { error: error.message });
      }
    }

    async function rollbackScene() {
      if (!state.sessionId || !state.snapshot) {
        setStatus("当前没有可回档的推演");
        return;
      }
      try {
        state.shouldContinue = false;
        loopRunId += 1;
        const currentTurn = Number(state.snapshot?.current_turn || 0);
        let targetStep = Number(dom.timelineSlider.value);
        if (state.snapshot?.result && targetStep >= currentTurn && currentTurn > 0) {
          targetStep = currentTurn - 1;
          dom.timelineSlider.value = String(targetStep);
        }
        await withLoading(
          {
            title: "正在执行回档",
            hint: "请稍等，系统正在恢复到你选择的历史步。"
          },
          async () => {
            const payload = await request(`/sessions/${state.sessionId}/director`, {
              method: "POST",
              body: {
                command: "rollback",
                step: targetStep
              }
            });
            applySnapshot(payload.snapshot);
            setStatus(`已回档到第 ${targetStep} 步，可继续推演`);
            setApiPreview("回档执行完成", payload);
          }
        );
      } catch (error) {
        setApiPreview("回档失败", { error: error.message });
      }
    }

    async function exportArtifacts() {
      if (!state.sessionId) {
        setStatus("当前没有会话");
        return;
      }
      try {
        const payload = await request(`/sessions/${state.sessionId}/export`, {
          method: "POST"
        });
        state.hasExportedArtifacts = true;
        setStage(4, { force: true });
        dom.scriptOutput.textContent = payload.script || "No script output.";
        setApiPreview("导出完成", payload.shotlist || payload);
        setStatus("导出已完成");
      } catch (error) {
        setApiPreview("导出失败", { error: error.message });
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
