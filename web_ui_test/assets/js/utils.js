(function(global) {
  'use strict';

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
    if (apiBase.includes("ai-gateway-show")) return "预演环境";
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

  function scrollToBottom(chatScroll) {
    if (chatScroll) {
      requestAnimationFrame(() => {
        chatScroll.scrollTop = chatScroll.scrollHeight;
      });
    }
  }

  // 导出到全局
  global.App = global.App || {};
  global.App.Utils = {
    formatTime,
    formatApiLabel,
    escapeHtml,
    scrollToBottom
  };

})(window);
