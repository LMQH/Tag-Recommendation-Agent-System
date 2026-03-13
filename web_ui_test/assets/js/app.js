// ============================================================================
// AI 自动装修助手 - 主应用文件
// ============================================================================
// 本文件包含所有前端逻辑，按功能模块进行了清晰分隔
// ============================================================================

(function() {
  'use strict';

  // ==========================================================================
  // 模块 1: 配置与状态管理
  // ==========================================================================

  const STORAGE_KEY = "test-api-chat-demo-config";
  const SIDEBAR_KEY = "test-api-chat-demo-sidebar";
  const DISPLAY_PANEL_KEY = "test-api-chat-demo-display-panel";
  const CONFIG_VERSION = "1.0";  // 配置版本号，修改后自动清除旧缓存
  const MOBILE_BREAKPOINT = 960;

  const state = {
    config: loadConfig(),
    sessions: [],
    filteredSessions: [],
    activeSessionId: "",
    messages: [],
    isSending: false,
    isSidebarCollapsed: loadSidebarPreference(),
    isMobileSidebarOpen: false,
    isDisplayPanelOpen: loadDisplayPanelPreference(),
    currentRecommendationData: null,  // 当前获取的推荐数据（统一为 { festival_recommendations }）
    recommendationCache: {},  // 会话推荐数据缓存：sessionId -> recommendationData
    selectedFestivalIndex: 0,  // 当前选中的节日下标
    reasoningSteps: [],  // 当前轮的思考推理步骤（会挂到当条 assistant 消息上）
    reasoningExpandedByMsgId: {}  // 某条消息的推理块是否展开 { [message._id]: true/false }
  };

  const els = {
    app: document.getElementById("app"),
    sessionList: document.getElementById("sessionList"),
    messages: document.getElementById("messages"),
    chatScroll: document.getElementById("chatScroll"),
    messageInput: document.getElementById("messageInput"),
    sendBtn: document.getElementById("sendBtn"),
    statusText: document.getElementById("statusText"),
    countText: document.getElementById("countText"),
    searchInput: document.getElementById("searchInput"),
    conversationTitle: document.getElementById("conversationTitle"),
    conversationMeta: document.getElementById("conversationMeta"),
    userChip: document.getElementById("userChip"),
    apiChip: document.getElementById("apiChip"),
    toggleSidebarBtn: document.getElementById("toggleSidebarBtn"),
    refreshBtn: document.getElementById("refreshBtn"),
    configBtn: document.getElementById("configBtn"),
    newSessionBtn: document.getElementById("newSessionBtn"),
    drawer: document.getElementById("drawer"),
    drawerBg: document.getElementById("drawerBg"),
    closeConfigBtn: document.getElementById("closeConfigBtn"),
    saveConfigBtn: document.getElementById("saveConfigBtn"),
    apiBaseInput: document.getElementById("apiBaseInput"),
    agentIdInput: document.getElementById("agentIdInput"),
    userIdInput: document.getElementById("userIdInput"),
    pageLimitInput: document.getElementById("pageLimitInput"),
    configError: document.getElementById("configError"),
    configSuccess: document.getElementById("configSuccess"),
    // 右侧展示面板相关元素
    toggleDisplayPanelBtn: document.getElementById("toggleDisplayPanelBtn"),
    displayPanel: document.getElementById("displayPanel"),
    closeDisplayPanelBtn: document.getElementById("closeDisplayPanelBtn"),
    festivalTabBar: document.getElementById("festivalTabBar"),
    categoryTagsForFestival: document.getElementById("categoryTagsForFestival"),
    brandTagsForFestival: document.getElementById("brandTagsForFestival"),
    confirmRecommendationBtn: document.getElementById("confirmRecommendationBtn"),
  };

  function loadConfig() {
    const defaults = {
      apiBase: "https://ai-gateway-show.yunzhonghe.com/ecom_reco_agent",
      agentId: "ecom-reco-agent",
      userId: "test-001",
      pageLimit: 30,
      _version: CONFIG_VERSION  // 添加版本号
    };

    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");

      // 检查版本，如果不匹配则清除旧缓存
      if (saved._version && saved._version !== CONFIG_VERSION) {
        console.log(`配置版本已更新 (${saved._version} → ${CONFIG_VERSION})，清除旧缓存`);
        localStorage.removeItem(STORAGE_KEY);
        return defaults;
      }

      // 如果保存的配置中没有版本号，也清除（旧版本数据）
      if (!saved._version && Object.keys(saved).length > 0) {
        console.log(`检测到旧版本配置，清除缓存以使用新版本`);
        localStorage.removeItem(STORAGE_KEY);
        return defaults;
      }

      return { ...defaults, ...saved };
    } catch (error) {
      return defaults;
    }
  }

  function loadSidebarPreference() {
    try {
      return JSON.parse(localStorage.getItem(SIDEBAR_KEY) || "false");
    } catch (error) {
      return false;
    }
  }

  function loadDisplayPanelPreference() {
    try {
      return JSON.parse(localStorage.getItem(DISPLAY_PANEL_KEY) || "false");
    } catch (error) {
      return false;
    }
  }

  function persistConfig() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state.config));
  }

  function persistSidebarPreference() {
    localStorage.setItem(SIDEBAR_KEY, JSON.stringify(state.isSidebarCollapsed));
  }

  function persistDisplayPanelPreference() {
    localStorage.setItem(DISPLAY_PANEL_KEY, JSON.stringify(state.isDisplayPanelOpen));
  }

  function syncConfigInputs() {
    els.apiBaseInput.value = state.config.apiBase;
    els.agentIdInput.value = state.config.agentId;
    els.userIdInput.value = state.config.userId;
    els.pageLimitInput.value = state.config.pageLimit;
  }

  // ==========================================================================
  // 模块 2: 工具函数
  // ==========================================================================

  function formatTime(value) {
    if (!value) return "刚刚";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "刚刚";
    return date.toLocaleString("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false
    });
  }

  function formatApiLabel(apiBase) {
    if (!apiBase) return "未设置";
    if (apiBase.includes("localhost") || apiBase.includes("127.0.0.1")) return "本地开发";
    if (apiBase.includes("ai-gateway-show")) return "show";
    return apiBase.replace(/^https?:\/\//, "");
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  /**
   * 将推荐数据归一化为 { festival_recommendations: [...] } 格式。
   * 若已是新格式直接返回；若是旧格式（recommendations + festival_scenes）则转换为虚拟单节日结构。
   */
  function normalizeRecommendationData(data) {
    if (!data) return null;
    if (data.festival_recommendations && Array.isArray(data.festival_recommendations) && data.festival_recommendations.length > 0) {
      return { festival_recommendations: data.festival_recommendations };
    }
    const scenes = data.festival_scenes && Array.isArray(data.festival_scenes) ? data.festival_scenes : [];
    const recs = data.recommendations && Array.isArray(data.recommendations) ? data.recommendations : [];
    if (recs.length === 0 && scenes.length === 0) return null;
    const categorySet = new Set();
    const brandList = [];
    recs.forEach(function(rec) {
      if (rec.categoryName) {
        categorySet.add(JSON.stringify({ name: rec.categoryName, code: rec.categoryCode || "" }));
      }
      if (rec.brandName) {
        brandList.push({ brandName: rec.brandName, brandCode: rec.brandCode || "" });
      }
    });
    const categories = Array.from(categorySet).map(function(s) {
      const c = JSON.parse(s);
      return { categoryName: c.name, categoryCode: c.code };
    });
    const festivalRec = {
      festival_id: 0,
      festival_name: "未指定节日",
      scene_type: "推荐",
      brands: brandList.length ? brandList : recs.map(function(r) { return { brandName: r.brandName, brandCode: r.brandCode || "" }; }).filter(function(b) { return b.brandName; }),
      categories: categories.length ? categories : recs.map(function(r) { return { categoryName: r.categoryName, categoryCode: r.categoryCode || "" }; }).filter(function(c) { return c.categoryName; })
    };
    if (scenes.length > 0) {
      return {
        festival_recommendations: scenes.map(function(s) {
          return {
            festival_id: s.id != null ? s.id : 0,
            festival_name: s.festival_name || "未指定",
            scene_type: s.scene_type || "节日营销",
            brands: festivalRec.brands,
            categories: festivalRec.categories
          };
        })
      };
    }
    return { festival_recommendations: [festivalRec] };
  }

  // 修复可能的编码问题（UTF-8 被 Latin-1 错误解析）
  function fixEncoding(text) {
    if (!text || typeof text !== 'string') return text;

    // 检测是否包含典型的乱码模式
    // UTF-8 中文字符被当作 Latin-1 解码后，会产生多个 128-255 范围的字符
    let needsFix = false;
    let latin1CharCount = 0;

    for (let i = 0; i < text.length; i++) {
      const code = text.charCodeAt(i);
      if (code > 127 && code <= 255) {
        latin1CharCount++;
        // 如果连续有3个以上的 Latin-1 字符，很可能是乱码
        if (latin1CharCount >= 3) {
          needsFix = true;
          break;
        }
      } else {
        latin1CharCount = 0;
      }
    }

    if (!needsFix) {
      return text;
    }

    console.log('[Encoding Debug] 检测到乱码，尝试修复:', text.slice(0, 30));

    try {
      // 修复方案：将字符串按 Latin-1 编码转为字节，然后用 UTF-8 解码
      const bytes = new Uint8Array([...text].map(char => char.charCodeAt(0) & 0xFF));
      const decoder = new TextDecoder('utf-8');
      const decoded = decoder.decode(bytes);

      // 验证修复结果：检查是否包含有效的中文字符
      const hasChinese = /[\u4e00-\u9fa5]/.test(decoded);
      if (hasChinese) {
        console.log('[Encoding Debug] 修复成功:', decoded.slice(0, 30));
        return decoded;
      } else {
        console.log('[Encoding Debug] 修复结果无效，保持原样');
        return text;
      }
    } catch (error) {
      console.warn('[Encoding Debug] 修复失败:', error);
      return text;
    }
  }

  function scrollToBottom() {
    requestAnimationFrame(() => {
      els.chatScroll.scrollTop = els.chatScroll.scrollHeight;
    });
  }

  function clearDisplayPanel() {
    state.selectedFestivalIndex = 0;
    if (els.festivalTabBar) els.festivalTabBar.innerHTML = '<div class="empty-tags">暂无节日数据</div>';
    if (els.categoryTagsForFestival) els.categoryTagsForFestival.innerHTML = '<div class="empty-tags">请先选择节日</div>';
    if (els.brandTagsForFestival) els.brandTagsForFestival.innerHTML = '<div class="empty-tags">请先选择节日</div>';
    if (els.confirmRecommendationBtn) els.confirmRecommendationBtn.disabled = true;
  }

  // ==========================================================================
  // 模块 3: UI 渲染
  // ==========================================================================

  function renderLayout() {
    const isMobile = window.innerWidth <= MOBILE_BREAKPOINT;
    els.app.classList.toggle("collapsed", !isMobile && state.isSidebarCollapsed);
    els.app.classList.toggle("mobile-open", isMobile && state.isMobileSidebarOpen);
    els.app.classList.toggle("display-open", state.isDisplayPanelOpen);
    els.toggleDisplayPanelBtn.classList.toggle("rotate", state.isDisplayPanelOpen);
  }

  function renderHeader() {
    const active = state.sessions.find((item) => item.session_id === state.activeSessionId);
    els.userChip.textContent = `user_id: ${state.config.userId || "未设置"}`;
    els.apiChip.textContent = `API: ${formatApiLabel(state.config.apiBase)}`;
    // 修复可能的编码问题
    const sessionName = active?.session_name ? fixEncoding(active.session_name) : "新对话";
    els.conversationTitle.textContent = sessionName;
    els.conversationMeta.textContent = active
      ? `session_id: ${active.session_id}`
      : "使用 runs 接口进行流式对话，左侧管理会话历史";
    els.countText.textContent = `${state.sessions.length} 个会话`;
  }

  function renderSessionList() {
    if (!state.filteredSessions.length) {
      els.sessionList.innerHTML = '<div class="empty-side">暂无会话，可点击"新建会话"开始。</div>';
      return;
    }
    els.sessionList.innerHTML = state.filteredSessions.map((item) => {
      // 修复可能的编码问题
      const sessionName = fixEncoding(item.session_name || "未命名会话");
      const preview = fixEncoding(item.preview || "点击查看历史消息");
      return `
      <div class="session-item ${item.session_id === state.activeSessionId ? "active" : ""}" data-session-id="${item.session_id}">
        <div class="session-head">
          <div class="session-name" title="${escapeHtml(sessionName)}">${escapeHtml(sessionName)}</div>
          <div class="session-time">${formatTime(item.updated_at || item.created_at)}</div>
        </div>
        <div class="session-preview" title="${escapeHtml(preview)}">${escapeHtml(preview)}</div>
        <div class="session-actions">
          <button class="session-btn" data-action="open" data-session-id="${item.session_id}">打开</button>
          <button class="session-btn" data-action="rename" data-session-id="${item.session_id}">重命名</button>
          <button class="session-btn" data-action="delete" data-session-id="${item.session_id}">删除</button>
        </div>
      </div>
    `;
    }).join("");

    els.sessionList.querySelectorAll(".session-item").forEach((node) => {
      node.addEventListener("click", (event) => {
        if (event.target.closest(".session-btn")) return;
        openSession(node.dataset.sessionId);
      });
    });

    els.sessionList.querySelectorAll(".session-btn").forEach((button) => {
      button.addEventListener("click", (event) => {
        event.stopPropagation();
        const sessionId = button.dataset.sessionId;
        const action = button.dataset.action;
        if (action === "open") return openSession(sessionId);
        if (action === "rename") return renameSession(sessionId);
        if (action === "delete") return deleteSession(sessionId);
      });
    });
  }

  /** 构建单条 assistant 消息的气泡内容（推理块 + 正文），用于渲染和流式更新 */
  function buildAssistantBubbleInner(item) {
    const msgId = item._id;
    const hasReasoning = item.reasoningSteps && item.reasoningSteps.length > 0;
    let bubbleInner = "";
    if (hasReasoning) {
      const durationSec = item.reasoningDurationSec != null ? item.reasoningDurationSec : 0;
      const durationText = durationSec > 0 ? "用时" + durationSec + "秒" : (item.streaming ? "进行中" : "已深度思考");
      const expanded = state.reasoningExpandedByMsgId[msgId] === true;
      const caret = expanded ? "▼" : "▲";
      const stepsHtml = item.reasoningSteps.map(function(step) {
        const title = escapeHtml(step.title || "步骤");
        const summary = step.reasoning ? escapeHtml(step.reasoning.slice(0, 300)) + (step.reasoning.length > 300 ? "…" : "") : "";
        const rc = step.reasoningContent || "";
        const firstLine = rc.split(/\n/)[0] || "";
        const detail = summary || (firstLine ? escapeHtml(firstLine.slice(0, 280)) + (firstLine.length > 280 ? "…" : "") : "");
        return "<div class=\"reasoning-step-item\"><div class=\"reasoning-step-title\">" + title + "</div>" + (detail ? "<div class=\"reasoning-step-detail\">" + detail + "</div>" : "") + "</div>";
      }).join("");
      bubbleInner += "<div class=\"message-reasoning-block" + (expanded ? " expanded" : "") + "\" data-msg-id=\"" + msgId + "\">";
      bubbleInner += "<button type=\"button\" class=\"message-reasoning-header\">已深度思考(" + durationText + ") " + caret + "</button>";
      bubbleInner += "<div class=\"message-reasoning-content\">" + stepsHtml + "</div></div>";
    }
    if (!item.content || item.content.trim() === "") {
      if (item.streaming) {
        bubbleInner += "<span class=\"streaming-placeholder\">正在思考...</span>";
      } else {
        bubbleInner += "<em class=\"empty-message\">（无内容）</em>";
      }
    } else {
      const fixedContent = fixEncoding(item.content);
      bubbleInner += typeof marked !== "undefined" ? marked.parse(fixedContent) : escapeHtml(fixedContent);
    }
    return bubbleInner;
  }

  /** 更新当前 assistant 消息气泡（推理块 + 正文），用于流式：每收到 ReasoningStep 或 RunContent 时调用 */
  function updateAssistantBubble(assistantMessage) {
    const msgId = assistantMessage._id;
    if (!msgId) return;
    const msgElement = els.messages.querySelector("[data-msg-id=\"" + msgId + "\"]");
    if (!msgElement) return;
    const bubbleElement = msgElement.querySelector(".bubble");
    if (!bubbleElement) return;
    bubbleElement.innerHTML = buildAssistantBubbleInner(assistantMessage);
    bubbleElement.classList.toggle("streaming", !!assistantMessage.streaming);
    scrollToBottom();
  }

  function renderMessages() {
    if (!state.messages.length) {
      els.messages.innerHTML = `
        <div class="empty">
          <div class="empty-card">
            <h3>今天想聊什么？</h3>
            <p>这里对接主接口 <code>runs</code> 的流式输出，同时支持会话历史查看、新建、删除和重命名。</p>
          </div>
        </div>
      `;
      return;
    }

    // 过滤掉空内容的历史消息（但保留正在流式输出的消息和用户消息）
    const visibleMessages = state.messages.filter((item) => {
      // 保留用户消息
      if (item.role === "user") return true;
      // 保留正在流式输出的消息
      if (item.streaming) return true;
      // 保留有内容的 AI 消息
      return item.content && item.content.trim() !== "";
    });

    els.messages.innerHTML = visibleMessages.map((item, index) => {
      let bubbleInner;
      if (item.role === "assistant") {
        bubbleInner = buildAssistantBubbleInner(item);
      } else {
        const fixedContent = fixEncoding(item.content || "");
        bubbleInner = escapeHtml(fixedContent);
      }
      const msgId = item._id || index;
      return `
        <div class="msg ${item.role === "user" ? "user" : ""}" data-msg-id="${msgId}">
          <div class="avatar">${item.role === "user" ? "你" : "AI"}</div>
          <div class="bubble-wrap">
            <div class="meta">
              <span>${item.role === "user" ? "你" : "AI"}</span>
              <span>${formatTime(item.created_at)}</span>
            </div>
            <div class="bubble ${item.streaming ? "streaming" : ""}">${bubbleInner}</div>
          </div>
        </div>
      `;
    }).join("");

    scrollToBottom();
  }

  // 已由 updateAssistantBubble 统一处理流式更新（推理块 + 正文）
  function updateStreamingMessage(assistantMessage) {
    updateAssistantBubble(assistantMessage);
  }

  // ==========================================================================
  // 模块 4: 交互控制
  // ==========================================================================

  function setStatus(text, isError = false) {
    els.statusText.textContent = text;
    els.statusText.style.color = isError ? "#b42318" : "";
  }

  function autoResizeTextarea() {
    els.messageInput.style.height = "auto";
    els.messageInput.style.height = `${Math.min(els.messageInput.scrollHeight, 180)}px`;
  }

  function toggleSidebar() {
    if (window.innerWidth <= MOBILE_BREAKPOINT) {
      state.isMobileSidebarOpen = !state.isMobileSidebarOpen;
    } else {
      state.isSidebarCollapsed = !state.isSidebarCollapsed;
      persistSidebarPreference();
    }
    renderLayout();
  }

  function toggleDisplayPanel() {
    state.isDisplayPanelOpen = !state.isDisplayPanelOpen;
    persistDisplayPanelPreference();
    renderLayout();
  }

  function updateDisplayTags(data) {
    console.log('[updateDisplayTags Called]', data);
    const normalized = normalizeRecommendationData(data);
    if (!normalized || !normalized.festival_recommendations || normalized.festival_recommendations.length === 0) {
      els.festivalTabBar.innerHTML = '<div class="empty-tags">暂无节日数据</div>';
      els.categoryTagsForFestival.innerHTML = '<div class="empty-tags">暂无品类数据</div>';
      els.brandTagsForFestival.innerHTML = '<div class="empty-tags">暂无品牌数据</div>';
      els.confirmRecommendationBtn.disabled = true;
      return;
    }

    const list = normalized.festival_recommendations;
    state.selectedFestivalIndex = Math.min(state.selectedFestivalIndex, list.length - 1);

    // 节日标签栏：横向排布，当前选中项带 active 和下划线
    els.festivalTabBar.innerHTML = list.map(function(fest, idx) {
      const name = fixEncoding(fest.festival_name || "未指定");
      const active = idx === state.selectedFestivalIndex ? " festival-tab active" : " festival-tab";
      return '<button type="button" class="' + active + '" data-festival-index="' + idx + '">' + escapeHtml(name) + '</button>';
    }).join('');

    els.festivalTabBar.querySelectorAll(".festival-tab").forEach(function(btn) {
      btn.addEventListener("click", function() {
        const idx = parseInt(btn.getAttribute("data-festival-index"), 10);
        if (Number.isNaN(idx)) return;
        state.selectedFestivalIndex = idx;
        renderFestivalDetail();
        els.festivalTabBar.querySelectorAll(".festival-tab").forEach(function(b) { b.classList.remove("active"); });
        btn.classList.add("active");
      });
    });

    renderFestivalDetail();
    els.confirmRecommendationBtn.disabled = false;
    console.log('[Display Tags Updated Successfully]');
  }

  function renderFestivalDetail() {
    const data = state.currentRecommendationData;
    if (!data || !data.festival_recommendations || !data.festival_recommendations.length) {
      if (els.categoryTagsForFestival) els.categoryTagsForFestival.innerHTML = '<div class="empty-tags">请先选择节日</div>';
      if (els.brandTagsForFestival) els.brandTagsForFestival.innerHTML = '<div class="empty-tags">请先选择节日</div>';
      return;
    }
    const idx = state.selectedFestivalIndex;
    const fest = data.festival_recommendations[idx];
    if (!fest) return;

    const categories = fest.categories && Array.isArray(fest.categories) ? fest.categories : [];
    const brands = fest.brands && Array.isArray(fest.brands) ? fest.brands : [];

    if (categories.length > 0) {
      els.categoryTagsForFestival.innerHTML = categories.map(function(c) {
        const catName = fixEncoding(c.categoryName);
        const catCode = fixEncoding(c.categoryCode || "");
        return '<div class="tag category-tag" title="' + escapeHtml(catCode) + '"><span class="tag-name">' + escapeHtml(catName) + '</span>' + (catCode ? '<span class="tag-code">' + escapeHtml(catCode) + '</span>' : '') + '</div>';
      }).join('');
    } else {
      els.categoryTagsForFestival.innerHTML = '<div class="empty-tags">暂无品类数据</div>';
    }

    if (brands.length > 0) {
      els.brandTagsForFestival.innerHTML = brands.map(function(b) {
        const brandName = fixEncoding(b.brandName);
        const brandCode = fixEncoding(b.brandCode || "");
        return '<div class="tag brand-tag" title="' + escapeHtml(brandCode) + '"><span class="tag-name">' + escapeHtml(brandName) + '</span>' + (brandCode ? '<span class="tag-code">' + escapeHtml(brandCode) + '</span>' : '') + '</div>';
      }).join('');
    } else {
      els.brandTagsForFestival.innerHTML = '<div class="empty-tags">暂无品牌数据</div>';
    }
  }

  async function saveRecommendationData() {
    if (!state.currentRecommendationData) {
      setStatus('没有可保存的推荐数据', true);
      return;
    }

    const sessionId = state.activeSessionId || 'unknown';
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    const filename = `recommendation_${sessionId}_${timestamp}.json`;

    // 准备要保存的数据
    const dataToSave = {
      session_id: sessionId,
      timestamp: new Date().toISOString(),
      data: state.currentRecommendationData
    };

    const jsonContent = JSON.stringify(dataToSave, null, 2);

    try {
      // 尝试使用 File System Access API（Chrome/Edge 支持）
      if ('showDirectoryPicker' in window) {
        try {
          // 提示用户选择 web_ui_test 目录
          setStatus('请选择 web_ui_test 目录...');
          
          // 请求用户选择目录
          const directoryHandle = await window.showDirectoryPicker();
          
          // 在选择的目录下创建或获取 data 文件夹
          let dataHandle;
          try {
            dataHandle = await directoryHandle.getDirectoryHandle('data', { create: true });
          } catch (e) {
            // 如果无法创建 data 文件夹，直接在当前目录保存
            console.warn('无法创建 data 文件夹，保存到当前目录:', e);
            dataHandle = directoryHandle;
          }

          // 在 data 文件夹中创建文件
          const fileHandle = await dataHandle.getFileHandle(filename, { create: true });
          const writable = await fileHandle.createWritable();
          await writable.write(jsonContent);
          await writable.close();

          setStatus(`✅ 推荐数据已保存到 data 文件夹: ${filename}`);
          return;
        } catch (error) {
          // 用户取消了选择，或者发生错误
          if (error.name === 'AbortError' || error.name === 'NotAllowedError') {
            // 用户取消了操作，不显示错误
            setStatus('保存已取消');
            return;
          }
          console.log('File System Access API 出错，使用下载方式:', error);
        }
      }

      // 回退到下载方式（兼容所有浏览器）
      const blob = new Blob([jsonContent], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      setStatus(`📥 文件已下载，请将 ${filename} 移动到 web_ui_test/data/ 文件夹`);
    } catch (error) {
      console.error(error);
      setStatus('保存推荐数据失败：' + (error.message || '未知错误'), true);
    }
  }

  function openDrawer() {
    hideConfigTips();
    els.drawer.classList.add("open");
  }

  function closeDrawer() {
    els.drawer.classList.remove("open");
  }

  function hideConfigTips() {
    els.configError.classList.add("hidden");
    els.configSuccess.classList.add("hidden");
    els.configError.textContent = "";
    els.configSuccess.textContent = "";
  }

  function showConfigError(message) {
    els.configError.textContent = message;
    els.configError.classList.remove("hidden");
    els.configSuccess.classList.add("hidden");
  }

  function showConfigSuccess(message) {
    els.configSuccess.textContent = message;
    els.configSuccess.classList.remove("hidden");
    els.configError.classList.add("hidden");
  }

  // ==========================================================================
  // 模块 5: API 调用 - 配置管理
  // ==========================================================================

  async function saveConfig() {
    hideConfigTips();
    const apiBase = els.apiBaseInput.value.trim().replace(/\/+$/, "");
    const agentId = els.agentIdInput.value.trim();
    const userId = els.userIdInput.value.trim();
    const pageLimit = Number(els.pageLimitInput.value);
    if (!apiBase || !/^https?:\/\//i.test(apiBase)) return showConfigError("API Base URL 必须是完整的 http/https 地址。");
    if (!agentId) return showConfigError("Agent ID 不能为空。");
    if (!userId) return showConfigError("User ID 不能为空。");
    if (!Number.isFinite(pageLimit) || pageLimit < 1 || pageLimit > 100) return showConfigError("会话列表加载条数需在 1 到 100 之间。");

    state.config = { apiBase, agentId, userId, pageLimit };
    persistConfig();
    renderHeader();
    showConfigSuccess("配置已保存，正在刷新会话列表。");
    await refreshSessions();
  }

  // ==========================================================================
  // 模块 6: API 调用 - 会话管理
  // ==========================================================================

  async function refreshSessions() {
    setStatus("正在加载会话列表...");
    try {
      const params = new URLSearchParams({
        type: "agent",
        component_id: state.config.agentId,
        user_id: state.config.userId,
        limit: String(state.config.pageLimit),
        page: "1",
        sort_by: "updated_at",
        sort_order: "desc"
      });
      const response = await fetch(`${state.config.apiBase}/sessions?${params.toString()}`);
      if (!response.ok) throw new Error(`加载会话失败 (${response.status})`);

      // 检查响应头的字符编码
      const contentType = response.headers.get("content-type");
      console.log('[Response Content-Type]', contentType);

      const data = await response.json();
      console.log('[Sessions Data]', data);

      state.sessions = (Array.isArray(data?.data) ? data.data : []).map((item) => ({
        ...item,
        preview: item.preview || ""
      }));

      // 调试：检查第一个会话的名称
      if (state.sessions.length > 0) {
        console.log('[First Session Name]', state.sessions[0].session_name);
        console.log('[First Session Name Chars]', Array.from(state.sessions[0].session_name || ''));
      }

      applySessionFilter();
      renderSessionList();
      renderHeader();

      // 不自动打开第一个会话，避免 404 导致的 CORS 错误
      // 用户需要手动点击会话或创建新会话
      if (state.activeSessionId && !state.sessions.find((item) => item.session_id === state.activeSessionId)) {
        state.activeSessionId = "";
        state.messages = [];
        renderMessages();
        renderHeader();
      }

      if (state.sessions.length === 0) {
        setStatus("暂无会话，点击「新建会话」开始使用。");
      } else {
        setStatus(`会话列表已更新，共 ${state.sessions.length} 个会话。`);
      }
    } catch (error) {
      console.error(error);
      setStatus(error.message || "会话列表加载失败", true);
      renderSessionList();
    }
  }

  function applySessionFilter() {
    const keyword = els.searchInput.value.trim().toLowerCase();
    state.filteredSessions = state.sessions.filter((item) => {
      if (!keyword) return true;
      return [item.session_name, item.preview, item.session_id]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(keyword));
    });
  }

  async function createSession() {
    if (state.isSending) return;
    setStatus("正在创建新会话...");
    try {
      const response = await fetch(`${state.config.apiBase}/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_name: `新会话 ${new Date().toLocaleString("zh-CN", { hour12: false })}`,
          user_id: state.config.userId,
          agent_id: state.config.agentId
        })
      });
      if (!response.ok) throw new Error(`创建会话失败 (${response.status})`);

      const created = await response.json();
      state.sessions.unshift({ ...created, preview: "" });
      state.activeSessionId = created.session_id;
      state.messages = [];
      applySessionFilter();
      renderSessionList();
      renderMessages();
      renderHeader();
      setStatus("新会话已创建，可以开始对话。");
      if (window.innerWidth <= MOBILE_BREAKPOINT) {
        state.isMobileSidebarOpen = false;
        renderLayout();
      }
    } catch (error) {
      console.error(error);
      setStatus(error.message || "创建会话失败", true);
    }
  }

  async function openSession(sessionId, showLoading = true) {
    if (!sessionId || state.isSending) return;
    if (showLoading) setStatus("正在加载会话历史...");

    try {
      // 使用 /sessions/{id} 接口，从 chat_history 字段获取消息
      const response = await fetch(`${state.config.apiBase}/sessions/${sessionId}`);
      if (!response.ok) {
        throw new Error(`加载会话失败 (${response.status})`);
      }

      const sessionData = await response.json();
      const messages = Array.isArray(sessionData?.chat_history) ? sessionData.chat_history : [];

      // 过滤掉空内容的 AI 消息（保留用户消息和有内容的消息）
      const filteredMessages = messages.filter((item) => {
        if (item.role === "user") return true;  // 保留所有用户消息
        if (item.role === "assistant") {
          // 只保留有内容的 AI 消息
          return item.content && item.content.trim() !== "";
        }
        return false;
      });

      state.activeSessionId = sessionId;
      state.messages = filteredMessages.map((item, index) => {
        const content = typeof item.content === "string" ? item.content : JSON.stringify(item.content || "");
        // 修复可能的编码问题
        const fixedContent = fixEncoding(content);
        return {
          role: item.role === "assistant" ? "assistant" : "user",
          content: fixedContent,
          created_at: item.created_at || new Date().toISOString(),
          _id: Date.now() + index
        };
      });

      const session = state.sessions.find((item) => item.session_id === sessionId);
      if (session) {
        session.session_name = sessionData.session_name || session.session_name;
        session.preview = (state.messages[state.messages.length - 1]?.content || "").slice(0, 60);
      }
      applySessionFilter();
      renderSessionList();
      renderMessages();
      renderHeader();

      // 从缓存中加载该会话的推荐数据（归一化为 festival_recommendations 格式）
      const cachedData = state.recommendationCache[sessionId];
      if (cachedData) {
        state.currentRecommendationData = normalizeRecommendationData(cachedData) || cachedData;
        updateDisplayTags(state.currentRecommendationData);
        // 自动展开展示面板
        if (!state.isDisplayPanelOpen) {
          state.isDisplayPanelOpen = true;
          persistDisplayPanelPreference();
          renderLayout();
        }
      } else {
        // 清空展示面板并显示提示
        state.currentRecommendationData = null;
        clearDisplayPanel();
      }

      setStatus(messages.length > 0 ? "历史消息已加载。" : "会话已打开，可以开始对话。");
      if (window.innerWidth <= MOBILE_BREAKPOINT) {
        state.isMobileSidebarOpen = false;
        renderLayout();
      }
    } catch (error) {
      console.error(error);
      if (showLoading) setStatus(error.message || "会话加载失败", true);
    }
  }

  async function renameSession(sessionId) {
    const session = state.sessions.find((item) => item.session_id === sessionId);
    if (!session) return;
    const nextName = window.prompt("请输入新的会话名称", session.session_name || "");
    if (!nextName || nextName.trim() === session.session_name) return;

    try {
      const response = await fetch(`${state.config.apiBase}/sessions/${sessionId}/rename`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_name: nextName.trim() })
      });
      if (!response.ok) throw new Error(`重命名失败 (${response.status})`);

      session.session_name = nextName.trim();
      renderSessionList();
      renderHeader();
      setStatus("会话已重命名。");
    } catch (error) {
      console.error(error);
      setStatus(error.message || "重命名失败", true);
    }
  }

  async function deleteSession(sessionId) {
    if (!window.confirm("确认删除这个会话吗？删除后不可恢复。")) return;
    try {
      const response = await fetch(`${state.config.apiBase}/sessions/${sessionId}`, { method: "DELETE" });
      if (!response.ok && response.status !== 204) throw new Error(`删除失败 (${response.status})`);

      state.sessions = state.sessions.filter((item) => item.session_id !== sessionId);
      // 清理缓存
      delete state.recommendationCache[sessionId];

      if (state.activeSessionId === sessionId) {
        state.activeSessionId = "";
        state.messages = [];
        state.currentRecommendationData = null;
      }
      applySessionFilter();
      renderSessionList();
      renderMessages();
      renderHeader();
      setStatus("会话已删除。");

      if (!state.activeSessionId && state.sessions[0]?.session_id) {
        openSession(state.sessions[0].sessionId, false);
      }
    } catch (error) {
      console.error(error);
      setStatus(error.message || "删除失败", true);
    }
  }

  // ==========================================================================
  // 模块 7: API 调用 - 聊天功能
  // ==========================================================================

  async function handleSendMessage() {
    const content = els.messageInput.value.trim();
    if (!content || state.isSending) return;

    if (!state.activeSessionId) {
      await createSession();
      if (!state.activeSessionId) return;
    }

    state.reasoningSteps = [];

    const userMessage = { role: "user", content, created_at: new Date().toISOString(), _id: Date.now() };
    const assistantMessage = { role: "assistant", content: "", created_at: new Date().toISOString(), streaming: true, _id: Date.now() + 1 };
    state.messages.push(userMessage, assistantMessage);
    renderMessages();

    els.messageInput.value = "";
    autoResizeTextarea();
    state.isSending = true;
    els.sendBtn.disabled = true;
    setStatus("正在生成回复...");

    try {
      await streamRun(content, assistantMessage);
      assistantMessage.streaming = false;
      updateSessionPreview();
      await refreshSessions();
      renderMessages();
      setStatus("回复完成。");
    } catch (error) {
      console.error(error);
      assistantMessage.streaming = false;
      assistantMessage.content = assistantMessage.content || `请求失败：${error.message || "未知错误"}`;
      renderMessages();
      setStatus(error.message || "发送失败", true);
    } finally {
      state.isSending = false;
      els.sendBtn.disabled = false;
    }
  }

  // 生成会话标题摘要
  function generateSessionTitle() {
    // 获取第一条用户消息作为标题基础
    const firstUserMessage = state.messages.find((item) => item.role === "user")?.content;
    if (!firstUserMessage) return null;

    // 移除常见的问候语和语气词
    const greetings = ["你好", "您好", "嗨", "hi", "hello", "请", "麻烦", "帮我", "我想"];
    let title = firstUserMessage.trim();

    // 移除开头的问候语
    for (const greeting of greetings) {
      const regex = new RegExp(`^${greeting}[，,，。\\s]*`, "i");
      title = title.replace(regex, "");
    }

    // 去除结尾的标点符号
    title = title.replace(/[。，,.?!！?\s]+$/, "");

    // 限制长度，最多20个字符
    if (title.length > 20) {
      title = title.slice(0, 20) + "...";
    }

    // 如果处理后为空，使用原始消息的前15个字符
    if (!title) {
      title = firstUserMessage.slice(0, 15);
      if (firstUserMessage.length > 15) {
        title += "...";
      }
    }

    return title;
  }

  // 更新服务器上的会话标题
  async function updateSessionTitleOnServer(sessionId, newTitle) {
    if (!sessionId || !newTitle) return;

    try {
      const response = await fetch(`${state.config.apiBase}/sessions/${sessionId}/rename`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_name: newTitle })
      });

      if (!response.ok) {
        console.warn(`更新会话标题失败 (${response.status})`);
      } else {
        console.log(`[Session Title Updated] ${newTitle}`);
      }
    } catch (error) {
      console.warn(`更新会话标题时出错: ${error.message}`);
    }
  }

  function updateSessionPreview() {
    const session = state.sessions.find((item) => item.session_id === state.activeSessionId);
    if (!session) return;

    const lastMessage = [...state.messages].reverse().find((item) => item.content);
    session.preview = (lastMessage?.content || "").slice(0, 60);

    // 如果会话名称是默认的"新会话"，生成新标题
    if (!session.session_name || /^新会话/.test(session.session_name)) {
      const newTitle = generateSessionTitle();
      if (newTitle) {
        session.session_name = newTitle;
        // 异步更新到服务器
        updateSessionTitleOnServer(session.session_id, newTitle);
      }
    }

    renderSessionList();
    renderHeader();
  }

  // ==========================================================================
  // 模块 8: SSE 流式处理
  // ==========================================================================

  async function streamRun(message, assistantMessage) {
    const body = new URLSearchParams({
      message,
      session_id: state.activeSessionId,
      user_id: state.config.userId,
      stream: "true"
    });

    const response = await fetch(`${state.config.apiBase}/agents/${state.config.agentId}/runs`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: body.toString()
    });
    if (!response.ok || !response.body) throw new Error(`runs 请求失败 (${response.status})`);

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split(/\n\n/);
      buffer = blocks.pop() || "";
      for (const block of blocks) {
        const payload = parseSseEvent(block);
        if (payload) applySseEvent(payload, assistantMessage);
      }
    }

    if (buffer.trim()) {
      const payload = parseSseEvent(buffer);
      if (payload) applySseEvent(payload, assistantMessage);
    }
  }

  function parseSseEvent(block) {
    const lines = block.split(/\r?\n/);
    let eventName = "";
    const dataLines = [];
    for (const line of lines) {
      if (!line.trim()) continue;
      if (line.startsWith("event:")) eventName = line.slice(6).trim();
      if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
    }
    if (!eventName && !dataLines.length) return null;

    const rawData = dataLines.join("\n");
    let data = rawData;
    try {
      data = rawData ? JSON.parse(rawData) : {};
    } catch (error) {}
    const payload = { event: eventName, data };

    // 调试日志
    console.log('[SSE Event]', eventName, data);

    return payload;
  }

  function applySseEvent(payload, assistantMessage) {
    console.log('[Apply Event]', payload.event, payload.data);

    if (payload.event === "RunStarted" || payload.event === "run_started") {
      if (payload.data?.session_id && !state.activeSessionId) state.activeSessionId = payload.data.session_id;
      state.reasoningSteps = [];
      return;
    }
    // 服务端可能发 PascalCase(ReasoningStep) 或 snake_case(reasoning_step)，均识别
    const ev = payload.event || "";
    const isReasoningStep = ev === "ReasoningStep" || ev === "reasoning_step";
    if (isReasoningStep) {
      const content = payload.data?.content || payload.data;
      const title = content?.title || "推理步骤";
      const reasoning = content?.reasoning || "";
      const reasoningContent = payload.data?.reasoning_content || content?.reasoning_content || "";
      const createdAt = payload.data?.created_at;
      state.reasoningSteps.push({ title: title, reasoning: reasoning, reasoningContent: reasoningContent, createdAt: createdAt });
      assistantMessage.reasoningSteps = state.reasoningSteps.slice();
      updateAssistantBubble(assistantMessage);
      return;
    }
    if (payload.event === "RunContent") {
      const content = typeof payload.data?.content === "string" ? payload.data.content : "";
      console.log('[Content Chunk]', JSON.stringify(content));
      assistantMessage.content += content;
      // 只更新当前流式消息，避免整个页面重渲染
      updateStreamingMessage(assistantMessage);
      return;
    }
    if (payload.event === "RunError") {
      throw new Error(payload.data?.error || "服务端返回 RunError");
    }
    if (payload.event === "ToolCallCompleted") {
      // 输出完整的工具调用数据用于调试
      console.log('[ToolCallCompleted Raw Data]', JSON.stringify(payload.data, null, 2));

      // 获取工具对象（可能是嵌套在 tool 字段中）
      const toolData = payload.data?.tool || payload.data;
      const toolName = toolData?.tool_name || toolData?.name || toolData?.toolName || "";
      console.log('[Tool Name]', toolName);

      // 检查是否是 build_review_fields 工具（部分匹配也行）
      if (toolName && toolName.toLowerCase().includes("build_review_fields")) {
        console.log('[build_review_fields detected]');

        // 获取原始结果字符串
        let resultString = toolData?.result || toolData?.output ||
                           toolData?.response || toolData?.return_value ||
                           payload.data?.result || payload.data?.output || "";

        console.log('[Raw Result String]', resultString);

        let toolResult = null;

        // 尝试解析结果（可能是字符串格式的 JSON）
        if (typeof resultString === 'string') {
          try {
            // 尝试 JSON.parse（处理双引号）
            toolResult = JSON.parse(resultString);
          } catch (e1) {
            try {
              // 如果 JSON.parse 失败，可能是单引号的 JSON，尝试 eval
              toolResult = eval(`(${resultString})`);
            } catch (e2) {
              console.warn('[Failed to parse result string]', e1, e2);
            }
          }
        } else if (typeof resultString === 'object') {
          // 结果已经是对象
          toolResult = resultString;
        }

        console.log('[Parsed Tool Result]', toolResult);

        const normalized = normalizeRecommendationData(toolResult);
        const hasRecommendations = normalized && normalized.festival_recommendations && normalized.festival_recommendations.length > 0;

        if (hasRecommendations) {
          console.log('[Valid Recommendation Data Found]', { festival_recommendations: normalized.festival_recommendations.length });
          state.currentRecommendationData = normalized;
          if (state.activeSessionId) {
            state.recommendationCache[state.activeSessionId] = normalized;
          }
          updateDisplayTags(normalized);
          // 自动展开右侧展示面板
          if (!state.isDisplayPanelOpen) {
            state.isDisplayPanelOpen = true;
            persistDisplayPanelPreference();
            renderLayout();
          }
        } else {
          console.warn('[No valid recommendation data in tool result]', toolResult);
        }
      } else {
        console.log('[Skipping other tool]', toolName);
      }
      return;
    }
    if (payload.event === "RecommendationDataEvent" || payload.event === "CustomEvent") {
      console.log('[Custom Event Data]', payload.data);
      const eventData = payload.data?.data || payload.data;
      const normalized = normalizeRecommendationData(eventData);
      if (normalized && normalized.festival_recommendations && normalized.festival_recommendations.length > 0) {
        console.log('[Final Recommendation Data]', normalized);
        state.currentRecommendationData = normalized;
        if (state.activeSessionId) {
          state.recommendationCache[state.activeSessionId] = normalized;
        }
        updateDisplayTags(normalized);
        // 自动展开右侧展示面板
        if (!state.isDisplayPanelOpen) {
          state.isDisplayPanelOpen = true;
          persistDisplayPanelPreference();
          renderLayout();
        }
      }
      return;
    }
    if (payload.event === "RunCompleted" || payload.event === "RunContentCompleted") {
      assistantMessage.streaming = false;
      // 将本轮的推理步骤挂到当前 assistant 消息上，并计算用时
      if (state.reasoningSteps.length > 0) {
        assistantMessage.reasoningSteps = state.reasoningSteps.slice();
        const first = state.reasoningSteps[0].createdAt;
        const last = state.reasoningSteps[state.reasoningSteps.length - 1].createdAt;
        assistantMessage.reasoningDurationSec = (typeof first === "number" && typeof last === "number" && last >= first) ? Math.round(last - first) : 0;
      }
      renderMessages();

      // 对话完成后，尝试更新会话标题（使用更智能的方式）
      if (payload.event === "RunCompleted") {
        const session = state.sessions.find((item) => item.session_id === state.activeSessionId);
        // 只在标题仍然是默认名称时更新
        if (session && (!session.session_name || /^新会话/.test(session.session_name))) {
          const newTitle = generateSessionTitle();
          if (newTitle && newTitle !== session.session_name) {
            session.session_name = newTitle;
            updateSessionTitleOnServer(session.session_id, newTitle);
            renderSessionList();
            renderHeader();
          }
        }
      }
    }
  }

  // ==========================================================================
  // 模块 9: 事件绑定与初始化
  // ==========================================================================

  function bindEvents() {
    els.sendBtn.addEventListener("click", handleSendMessage);
    els.messageInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        handleSendMessage();
      }
    });
    els.messageInput.addEventListener("input", autoResizeTextarea);
    els.searchInput.addEventListener("input", () => {
      applySessionFilter();
      renderSessionList();
    });
    els.toggleSidebarBtn.addEventListener("click", toggleSidebar);
    els.refreshBtn.addEventListener("click", refreshSessions);
    els.configBtn.addEventListener("click", openDrawer);
    els.newSessionBtn.addEventListener("click", createSession);
    els.drawerBg.addEventListener("click", closeDrawer);
    els.closeConfigBtn.addEventListener("click", closeDrawer);
    els.saveConfigBtn.addEventListener("click", saveConfig);
    // 新增：右侧展示面板事件绑定
    els.toggleDisplayPanelBtn.addEventListener("click", toggleDisplayPanel);
    els.closeDisplayPanelBtn.addEventListener("click", toggleDisplayPanel);
    els.confirmRecommendationBtn.addEventListener("click", saveRecommendationData);
    els.messages.addEventListener("click", function(e) {
      const btn = e.target.closest(".message-reasoning-header");
      if (!btn) return;
      const block = btn.closest(".message-reasoning-block");
      if (!block) return;
      const msgId = block.getAttribute("data-msg-id");
      if (msgId == null) return;
      state.reasoningExpandedByMsgId[msgId] = !state.reasoningExpandedByMsgId[msgId];
      block.classList.toggle("expanded", state.reasoningExpandedByMsgId[msgId]);
      var caret = state.reasoningExpandedByMsgId[msgId] ? "▼" : "▲";
      btn.textContent = btn.textContent.replace(/[▲▼]$/, caret);
    });
    window.addEventListener("resize", renderLayout);
  }

  function init() {
    syncConfigInputs();
    bindEvents();
    renderLayout();
    renderHeader();
    renderMessages();
    refreshSessions();
  }

  // 启动应用
  init();

})();
