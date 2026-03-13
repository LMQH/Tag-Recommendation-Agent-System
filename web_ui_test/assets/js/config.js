(function(global) {
  'use strict';

  const STORAGE_KEY = "test-api-chat-demo-config";
  const SIDEBAR_KEY = "test-api-chat-demo-sidebar";
  const MOBILE_BREAKPOINT = 960;

  const DEFAULT_CONFIG = {
    apiBase: "https://ai-gateway-show.yunzhonghe.com/ecom_reco_agent",
    agentId: "ecom-reco-agent",
    userId: "test-001",
    pageLimit: 30
  };

  // 状态对象
  const state = {
    config: null,
    sessions: [],
    filteredSessions: [],
    activeSessionId: "",
    messages: [],
    isSending: false,
    isSidebarCollapsed: false,
    isMobileSidebarOpen: false
  };

  // DOM 元素引用
  let els = {};

  // 配置管理函数
  function loadConfig() {
    const defaults = { ...DEFAULT_CONFIG };
    try {
      return { ...defaults, ...JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}") };
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

  function persistConfig() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state.config));
  }

  function persistSidebarPreference() {
    localStorage.setItem(SIDEBAR_KEY, JSON.stringify(state.isSidebarCollapsed));
  }

  function syncConfigInputs() {
    if (els.apiBaseInput) els.apiBaseInput.value = state.config.apiBase;
    if (els.agentIdInput) els.agentIdInput.value = state.config.agentId;
    if (els.userIdInput) els.userIdInput.value = state.config.userId;
    if (els.pageLimitInput) els.pageLimitInput.value = state.config.pageLimit;
  }

  function initConfig() {
    state.config = loadConfig();
    state.isSidebarCollapsed = loadSidebarPreference();
  }

  // 导出到全局
  global.App = global.App || {};
  global.App.Config = {
    state,
    els,
    STORAGE_KEY,
    SIDEBAR_KEY,
    MOBILE_BREAKPOINT,
    DEFAULT_CONFIG,
    initConfig,
    loadConfig,
    persistConfig,
    persistSidebarPreference,
    syncConfigInputs,
    setEls: function(elements) { els = elements; },
    getEls: function() { return els; }
  };

})(window);
