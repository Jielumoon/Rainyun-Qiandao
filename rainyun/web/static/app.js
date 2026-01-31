const tokenKey = "rainyun_token";
const loginPanel = document.getElementById("login-panel");
const dashboard = document.getElementById("dashboard");
const loginBtn = document.getElementById("login-btn");
const loginPassword = document.getElementById("login-password");
const logoutBtn = document.getElementById("logout-btn");
const toast = document.getElementById("toast");

const accountsBody = document.getElementById("accounts-body");
const refreshAccountsBtn = document.getElementById("refresh-accounts");
const checkinBtn = document.getElementById("checkin-btn");
const renewBtn = document.getElementById("renew-btn");
const resetFormBtn = document.getElementById("reset-form");
const saveAccountBtn = document.getElementById("save-account");
const accountFormTitle = document.getElementById("account-form-title");
const toggleAccountFormBtn = document.getElementById("toggle-account-form");
const accountFormBody = document.getElementById("account-form-body");

const tabButtons = document.querySelectorAll(".tab-btn");
const tabMain = document.getElementById("tab-main");
const tabLogs = document.getElementById("tab-logs");
const logOutput = document.getElementById("log-output");
const logAutoRefresh = document.getElementById("log-auto-refresh");
const refreshLogsBtn = document.getElementById("refresh-logs");

const accountName = document.getElementById("account-name");
const accountUsername = document.getElementById("account-username");
const accountPassword = document.getElementById("account-password");
const accountApiKey = document.getElementById("account-api-key");
const accountRenew = document.getElementById("account-renew");
const accountEnabled = document.getElementById("account-enabled");

const settingAutoRenew = document.getElementById("setting-auto-renew");
const settingRenewDays = document.getElementById("setting-renew-days");
const settingCron = document.getElementById("setting-cron");
const cronMode = document.getElementById("cron-mode");
const cronHour = document.getElementById("cron-hour");
const cronMinute = document.getElementById("cron-minute");
const cronWeekday = document.getElementById("cron-weekday");
const cronMonthday = document.getElementById("cron-monthday");
const cronPreview = document.getElementById("cron-preview");
const cronNext = document.getElementById("cron-next");
const settingTimeout = document.getElementById("setting-timeout");
const settingMaxDelay = document.getElementById("setting-max-delay");
const settingDebug = document.getElementById("setting-debug");
const settingRequestTimeout = document.getElementById("setting-request-timeout");
const settingMaxRetries = document.getElementById("setting-max-retries");
const settingRetryDelay = document.getElementById("setting-retry-delay");
const settingDownloadTimeout = document.getElementById("setting-download-timeout");
const settingDownloadMaxRetries = document.getElementById("setting-download-max-retries");
const settingDownloadRetryDelay = document.getElementById("setting-download-retry-delay");
const settingCaptchaRetryLimit = document.getElementById("setting-captcha-retry-limit");
const settingCaptchaRetryUnlimited = document.getElementById("setting-captcha-retry-unlimited");
const settingCaptchaSaveSamples = document.getElementById("setting-captcha-save-samples");
const settingSkipPushTitle = document.getElementById("setting-skip-push-title");
const saveSettingsBtn = document.getElementById("save-settings");

const notifyBody = document.getElementById("notify-body");
const addNotifyBtn = document.getElementById("add-notify");
const notifyForm = document.getElementById("notify-form");
const notifyName = document.getElementById("notify-name");
const notifyType = document.getElementById("notify-type");
const notifyEnabled = document.getElementById("notify-enabled");
const notifyPushKey = document.getElementById("notify-push-key");
const notifyTgToken = document.getElementById("notify-tg-token");
const notifyTgUser = document.getElementById("notify-tg-user");
const notifyTgHost = document.getElementById("notify-tg-host");
const notifyPushPlusToken = document.getElementById("notify-pushplus-token");
const notifyPushPlusUser = document.getElementById("notify-pushplus-user");
const notifyBarkPush = document.getElementById("notify-bark-push");
const notifyCustomConfig = document.getElementById("notify-custom-config");
const saveNotifyBtn = document.getElementById("save-notify");
const cancelNotifyBtn = document.getElementById("cancel-notify");

let editingId = null;
let editingNotifyId = null;
let notifyChannels = [];
let savingSettings = false;
let logTimer = null;

function getToken() {
  return localStorage.getItem(tokenKey);
}

function setToken(token) {
  if (token) {
    localStorage.setItem(tokenKey, token);
  } else {
    localStorage.removeItem(tokenKey);
  }
}

function showToast(message, type = "success") {
  toast.textContent = message;
  toast.className = `toast ${type}`;
  toast.classList.remove("hidden");
  setTimeout(() => toast.classList.add("hidden"), 2800);
}

function maskValue(raw) {
  if (!raw) return "";
  if (raw.length <= 6) return raw;
  return `${raw.slice(0, 3)}***${raw.slice(-3)}`;
}

function normalizeNotifyChannels(settings) {
  const raw = settings.notify_channels;
  if (Array.isArray(raw) && raw.length) {
    return raw.map((item) => ({
      id: item.id || `notify_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`,
      name: item.name || "",
      type: item.type || "custom",
      enabled: item.enabled !== false,
      config: typeof item.config === "object" && item.config ? item.config : {},
    }));
  }
  return buildChannelsFromLegacy(settings.notify_config || {});
}

function buildChannelsFromLegacy(config) {
  const channels = [];
  if (!config || typeof config !== "object") {
    return channels;
  }
  const legacy = { ...config };
  if (legacy.CONSOLE && ["true", true, 1, "1"].includes(legacy.CONSOLE)) {
    channels.push({
      id: `notify_${Date.now()}_console`,
      name: "控制台",
      type: "console",
      enabled: true,
      config: { CONSOLE: "true" },
    });
    delete legacy.CONSOLE;
  }
  if (legacy.PUSH_KEY) {
    channels.push({
      id: `notify_${Date.now()}_serverj`,
      name: "Server酱",
      type: "serverj",
      enabled: true,
      config: { PUSH_KEY: String(legacy.PUSH_KEY) },
    });
    delete legacy.PUSH_KEY;
  }
  if (legacy.TG_BOT_TOKEN && legacy.TG_USER_ID) {
    const tgConfig = {
      TG_BOT_TOKEN: String(legacy.TG_BOT_TOKEN),
      TG_USER_ID: String(legacy.TG_USER_ID),
    };
    if (legacy.TG_API_HOST) {
      tgConfig.TG_API_HOST = String(legacy.TG_API_HOST);
    }
    channels.push({
      id: `notify_${Date.now()}_telegram`,
      name: "Telegram",
      type: "telegram",
      enabled: true,
      config: tgConfig,
    });
    delete legacy.TG_BOT_TOKEN;
    delete legacy.TG_USER_ID;
    delete legacy.TG_API_HOST;
  }
  if (legacy.PUSH_PLUS_TOKEN) {
    const pushPlusConfig = {
      PUSH_PLUS_TOKEN: String(legacy.PUSH_PLUS_TOKEN),
    };
    if (legacy.PUSH_PLUS_USER) {
      pushPlusConfig.PUSH_PLUS_USER = String(legacy.PUSH_PLUS_USER);
    }
    channels.push({
      id: `notify_${Date.now()}_pushplus`,
      name: "PushPlus",
      type: "pushplus",
      enabled: true,
      config: pushPlusConfig,
    });
    delete legacy.PUSH_PLUS_TOKEN;
    delete legacy.PUSH_PLUS_USER;
  }
  if (legacy.BARK_PUSH) {
    channels.push({
      id: `notify_${Date.now()}_bark`,
      name: "Bark",
      type: "bark",
      enabled: true,
      config: { BARK_PUSH: String(legacy.BARK_PUSH) },
    });
    delete legacy.BARK_PUSH;
  }
  const leftoverKeys = Object.keys(legacy);
  if (leftoverKeys.length) {
    channels.push({
      id: `notify_${Date.now()}_custom`,
      name: "高级 JSON",
      type: "custom",
      enabled: true,
      config: legacy,
    });
  }
  return channels;
}

function buildNotifyTypeOptions() {
  if (!notifyType) return;
  const options = [
    { value: "serverj", label: "Server酱" },
    { value: "telegram", label: "Telegram" },
    { value: "pushplus", label: "PushPlus" },
    { value: "bark", label: "Bark" },
    { value: "console", label: "控制台" },
    { value: "custom", label: "自定义 JSON" },
  ];
  notifyType.innerHTML = "";
  options.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.value;
    option.textContent = item.label;
    notifyType.appendChild(option);
  });
}

const notifyTypeLabels = {
  serverj: "Server酱",
  telegram: "Telegram",
  pushplus: "PushPlus",
  bark: "Bark",
  console: "控制台",
  custom: "自定义 JSON",
};

function setNotifyFormVisible(visible) {
  if (!notifyForm) return;
  notifyForm.classList.toggle("hidden", !visible);
}

function resetNotifyForm() {
  editingNotifyId = null;
  if (notifyName) notifyName.value = "";
  if (notifyType) notifyType.value = "serverj";
  if (notifyEnabled) notifyEnabled.checked = true;
  if (notifyPushKey) notifyPushKey.value = "";
  if (notifyTgToken) notifyTgToken.value = "";
  if (notifyTgUser) notifyTgUser.value = "";
  if (notifyTgHost) notifyTgHost.value = "";
  if (notifyPushPlusToken) notifyPushPlusToken.value = "";
  if (notifyPushPlusUser) notifyPushPlusUser.value = "";
  if (notifyBarkPush) notifyBarkPush.value = "";
  if (notifyCustomConfig) notifyCustomConfig.value = "";
  toggleNotifyFields("serverj");
}

function toggleNotifyFields(type) {
  const fieldIds = [
    "notify-fields-console",
    "notify-fields-serverj",
    "notify-fields-telegram",
    "notify-fields-pushplus",
    "notify-fields-bark",
    "notify-fields-custom",
  ];
  fieldIds.forEach((id) => {
    const block = document.getElementById(id);
    if (!block) return;
    block.classList.toggle("hidden", !id.includes(type));
  });
}

function summarizeNotifyChannel(channel) {
  const type = channel.type;
  const cfg = channel.config || {};
  if (type === "serverj") return maskValue(cfg.PUSH_KEY || "");
  if (type === "telegram") return `用户 ${cfg.TG_USER_ID || "-"}`;
  if (type === "pushplus")
    return `Token ${maskValue(cfg.PUSH_PLUS_TOKEN || "")}`;
  if (type === "bark") return (cfg.BARK_PUSH || "").replace(/https?:\/\//, "");
  if (type === "console") return "控制台输出";
  if (type === "custom") return "自定义 JSON";
  return "-";
}

function renderNotifyList() {
  if (!notifyBody) return;
  notifyBody.innerHTML = "";
  notifyChannels.forEach((channel) => {
    const typeLabel = notifyTypeLabels[channel.type] || channel.type || "-";
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${channel.name || "-"}</td>
      <td>${typeLabel}</td>
      <td>${channel.enabled ? "是" : "否"}</td>
      <td>${summarizeNotifyChannel(channel)}</td>
      <td>
        <button class="ghost-btn" data-action="edit" data-id="${channel.id}">编辑</button>
        <button class="ghost-btn" data-action="test" data-id="${channel.id}">测试</button>
        <button class="ghost-btn" data-action="delete" data-id="${channel.id}">删除</button>
      </td>
    `;
    notifyBody.appendChild(row);
  });
}

function buildNotifyConfigFromForm(type) {
  if (type === "console") {
    return { CONSOLE: "true" };
  }
  if (type === "serverj") {
    const key = notifyPushKey.value.trim();
    if (!key) {
      throw new Error("请填写 Server酱 PUSH_KEY");
    }
    return { PUSH_KEY: key };
  }
  if (type === "telegram") {
    const token = notifyTgToken.value.trim();
    const user = notifyTgUser.value.trim();
    if (!token || !user) {
      throw new Error("Telegram 需要同时填写 Bot Token 与用户ID");
    }
    const config = { TG_BOT_TOKEN: token, TG_USER_ID: user };
    const host = notifyTgHost.value.trim();
    if (host) {
      config.TG_API_HOST = host;
    }
    return config;
  }
  if (type === "pushplus") {
    const token = notifyPushPlusToken.value.trim();
    if (!token) {
      throw new Error("PushPlus 需要填写 Token");
    }
    const config = { PUSH_PLUS_TOKEN: token };
    const user = notifyPushPlusUser.value.trim();
    if (user) {
      config.PUSH_PLUS_USER = user;
    }
    return config;
  }
  if (type === "bark") {
    const push = notifyBarkPush.value.trim();
    if (!push) {
      throw new Error("请填写 Bark 推送地址");
    }
    return { BARK_PUSH: push };
  }
  if (type === "custom") {
    const raw = notifyCustomConfig.value.trim();
    if (!raw) {
      throw new Error("请填写自定义 JSON");
    }
    const parsed = JSON.parse(raw);
    if (typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error("自定义 JSON 需为对象");
    }
    return parsed;
  }
  return {};
}

function saveNotifyChannel() {
  const type = notifyType.value;
  const name = notifyName.value.trim();
  const enabled = notifyEnabled.checked;
  const config = buildNotifyConfigFromForm(type);
  const payload = {
    id:
      editingNotifyId ||
      `notify_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`,
    name: name || type,
    type,
    enabled,
    config,
  };
  if (editingNotifyId) {
    notifyChannels = notifyChannels.map((item) =>
      item.id === editingNotifyId ? payload : item
    );
  } else {
    notifyChannels.push(payload);
  }
  renderNotifyList();
  resetNotifyForm();
  setNotifyFormVisible(false);
}

function fillNotifyForm(channel) {
  editingNotifyId = channel.id;
  notifyName.value = channel.name || "";
  notifyType.value = channel.type || "serverj";
  notifyEnabled.checked = channel.enabled !== false;
  const cfg = channel.config || {};
  notifyPushKey.value = cfg.PUSH_KEY || "";
  notifyTgToken.value = cfg.TG_BOT_TOKEN || "";
  notifyTgUser.value = cfg.TG_USER_ID || "";
  notifyTgHost.value = cfg.TG_API_HOST || "";
  notifyPushPlusToken.value = cfg.PUSH_PLUS_TOKEN || "";
  notifyPushPlusUser.value = cfg.PUSH_PLUS_USER || "";
  notifyBarkPush.value = cfg.BARK_PUSH || "";
  notifyCustomConfig.value = JSON.stringify(cfg, null, 2);
  toggleNotifyFields(notifyType.value);
  setNotifyFormVisible(true);
}

function setCellLines(cell, lines, muted = false) {
  if (!cell) return;
  cell.innerHTML = "";
  const wrap = document.createElement("div");
  wrap.className = "cell-lines";
  lines.forEach((text) => {
    const line = document.createElement("span");
    line.textContent = text;
    if (muted) {
      line.classList.add("cell-muted");
    }
    wrap.appendChild(line);
  });
  cell.appendChild(wrap);
}

function formatServerLine(server) {
  const name = server.name || `服务器${server.id || ""}`.trim();
  const days =
    typeof server.days_remaining === "number"
      ? `${server.days_remaining} 天`
      : "未知";
  const expired = server.expired || "未知";
  return `${name} (${server.id}) ${days} (${expired})`;
}

function readNumberValue(input, fallback) {
  const raw = input.value.trim();
  if (!raw) {
    return fallback;
  }
  const value = Number(raw);
  return Number.isFinite(value) ? value : fallback;
}

function fillSelect(select, start, end, labelFn) {
  select.innerHTML = "";
  for (let i = start; i <= end; i += 1) {
    const option = document.createElement("option");
    option.value = String(i);
    option.textContent = labelFn ? labelFn(i) : String(i);
    select.appendChild(option);
  }
}

function initCronOptions() {
  if (!cronMode) return;
  const modes = [
    { value: "daily", label: "每天" },
    { value: "weekly", label: "每周" },
    { value: "monthly", label: "每月" },
    { value: "custom", label: "自定义" },
  ];
  cronMode.innerHTML = "";
  modes.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.value;
    option.textContent = item.label;
    cronMode.appendChild(option);
  });
  fillSelect(cronHour, 0, 23, (v) => `${v}点`);
  fillSelect(cronMinute, 0, 59, (v) => `${v}分`);
  cronWeekday.innerHTML = "";
  const weekdays = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];
  weekdays.forEach((label, index) => {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = label;
    cronWeekday.appendChild(option);
  });
  fillSelect(cronMonthday, 1, 31, (v) => `${v}号`);
}

function updateCronModeUI() {
  if (!cronMode) return;
  const mode = cronMode.value;
  const isCustom = mode === "custom";
  cronHour.classList.toggle("hidden", isCustom);
  cronMinute.classList.toggle("hidden", isCustom);
  cronWeekday.classList.toggle("hidden", mode !== "weekly");
  cronMonthday.classList.toggle("hidden", mode !== "monthly");
  settingCron.classList.toggle("hidden", !isCustom);
}

function buildCronFromUI() {
  if (!cronMode) return settingCron.value.trim() || "0 8 * * *";
  const mode = cronMode.value;
  if (mode === "custom") {
    return settingCron.value.trim() || "0 8 * * *";
  }
  const minute = cronMinute.value || "0";
  const hour = cronHour.value || "8";
  if (mode === "weekly") {
    const weekday = cronWeekday.value || "0";
    return `${minute} ${hour} * * ${weekday}`;
  }
  if (mode === "monthly") {
    const monthday = cronMonthday.value || "1";
    return `${minute} ${hour} ${monthday} * *`;
  }
  return `${minute} ${hour} * * *`;
}

function parseCronToUI(cronText) {
  if (!cronMode) return;
  const raw = (cronText || "").trim();
  const parts = raw.split(/\s+/);
  if (parts.length < 5) {
    cronMode.value = "custom";
    settingCron.value = raw || "0 8 * * *";
    updateCronModeUI();
    return;
  }
  const [minute, hour, monthday, month, weekday] = parts;
  if (monthday !== "*" && month === "*" && (weekday === "*" || weekday === "?")) {
    cronMode.value = "monthly";
    cronMinute.value = minute;
    cronHour.value = hour;
    cronMonthday.value = monthday;
  } else if (weekday !== "*" && (monthday === "*" || monthday === "?")) {
    cronMode.value = "weekly";
    cronMinute.value = minute;
    cronHour.value = hour;
    cronWeekday.value = weekday === "7" ? "0" : weekday;
  } else if (monthday === "*" && weekday === "*") {
    cronMode.value = "daily";
    cronMinute.value = minute;
    cronHour.value = hour;
  } else {
    cronMode.value = "custom";
    settingCron.value = raw;
  }
  updateCronModeUI();
}

function formatDate(date) {
  return date.toLocaleString("zh-CN", {
    hour12: false,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getNextDaily(hour, minute) {
  const now = new Date();
  const next = new Date(now);
  next.setHours(hour, minute, 0, 0);
  if (next <= now) {
    next.setDate(next.getDate() + 1);
  }
  return next;
}

function getNextWeekly(hour, minute, weekday) {
  const now = new Date();
  const next = new Date(now);
  next.setHours(hour, minute, 0, 0);
  const target = Number(weekday);
  let diff = (target - next.getDay() + 7) % 7;
  if (diff === 0 && next <= now) {
    diff = 7;
  }
  next.setDate(next.getDate() + diff);
  return next;
}

function getNextMonthly(base, hour, minute, day) {
  let year = base.getFullYear();
  let month = base.getMonth();
  for (let i = 0; i < 24; i += 1) {
    const candidate = new Date(year, month, day, hour, minute, 0, 0);
    if (candidate.getMonth() !== month) {
      month += 1;
      if (month > 11) {
        month = 0;
        year += 1;
      }
      continue;
    }
    if (candidate > base) {
      return candidate;
    }
    month += 1;
    if (month > 11) {
      month = 0;
      year += 1;
    }
  }
  return null;
}

function updateCronPreview() {
  if (!cronMode) return;
  const cron = buildCronFromUI();
  cronPreview.textContent = cron;
  if (cronMode.value === "custom") {
    cronNext.textContent = "自定义模式不计算执行时间";
    return;
  }
  const hour = Number(cronHour.value || 0);
  const minute = Number(cronMinute.value || 0);
  let first = null;
  let second = null;
  if (cronMode.value === "daily") {
    first = getNextDaily(hour, minute);
    second = new Date(first);
    second.setDate(first.getDate() + 1);
  } else if (cronMode.value === "weekly") {
    first = getNextWeekly(hour, minute, cronWeekday.value || "0");
    second = new Date(first);
    second.setDate(first.getDate() + 7);
  } else if (cronMode.value === "monthly") {
    const day = Number(cronMonthday.value || 1);
    first = getNextMonthly(new Date(), hour, minute, day);
    if (first) {
      second = getNextMonthly(first, hour, minute, day);
    }
  }
  if (first && second) {
    cronNext.textContent = `下一次: ${formatDate(first)} | 下下次: ${formatDate(second)}`;
  } else if (first) {
    cronNext.textContent = `下一次: ${formatDate(first)}`;
  } else {
    cronNext.textContent = "未能计算执行时间";
  }
}

async function apiFetch(path, options = {}) {
  const headers = options.headers || {};
  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  headers["Content-Type"] = "application/json";
  const response = await fetch(path, { ...options, headers });
  const payload = await response.json().catch(() => ({}));
  if (response.status === 401) {
    setToken(null);
    showLogin();
    throw new Error(payload.message || "未授权");
  }
  if (!response.ok || payload.code !== 0) {
    throw new Error(payload.message || "请求失败");
  }
  return payload.data;
}

function showLogin() {
  loginPanel.classList.remove("hidden");
  dashboard.classList.add("hidden");
  logoutBtn.classList.add("hidden");
}

function showDashboard() {
  loginPanel.classList.add("hidden");
  dashboard.classList.remove("hidden");
  logoutBtn.classList.remove("hidden");
}

async function handleLogin() {
  const password = loginPassword.value.trim();
  if (!password) {
    showToast("请输入密码", "error");
    return;
  }
  try {
    const data = await apiFetch("/api/login", {
      method: "POST",
      body: JSON.stringify({ password }),
    });
    setToken(data.token);
    showToast("登录成功");
    loginPassword.value = "";
    await loadAll();
    showDashboard();
  } catch (err) {
    showToast(err.message || "登录失败", "error");
  }
}

async function loadAccounts() {
  const accounts = await apiFetch("/api/accounts");
  accountsBody.innerHTML = "";
  const rowMap = new Map();
  accounts.forEach((account) => {
    const row = document.createElement("tr");
    const canRenew = !!account.api_key;
    row.innerHTML = `
      <td>${account.name || account.id}</td>
      <td>${account.enabled ? "是" : "否"}</td>
      <td>${account.last_status || "-"}</td>
      <td>${account.last_checkin || "-"}</td>
      <td data-field="points">-</td>
      <td data-field="whitelist">-</td>
      <td data-field="expiry">-</td>
      <td>
        <button class="ghost-btn" data-action="checkin" data-id="${account.id}">签到</button>
        <button class="ghost-btn" data-action="renew" data-id="${account.id}" ${canRenew ? "" : "disabled"}>续费</button>
        <button class="ghost-btn" data-action="edit" data-id="${account.id}">编辑</button>
        <button class="ghost-btn" data-action="delete" data-id="${account.id}">删除</button>
      </td>
    `;
    accountsBody.appendChild(row);
    rowMap.set(account.id, row);
  });
  await Promise.all(
    accounts.map(async (account) => {
      const row = rowMap.get(account.id);
      if (!row) return;
      const pointsCell = row.querySelector("[data-field='points']");
      const whitelistCell = row.querySelector("[data-field='whitelist']");
      const expiryCell = row.querySelector("[data-field='expiry']");
      const whitelistIds = Array.isArray(account.renew_products)
        ? account.renew_products
        : [];
      if (whitelistCell) {
        whitelistCell.textContent = whitelistIds.length
          ? whitelistIds.join(", ")
          : "全部";
      }
      if (!account.api_key) {
        if (pointsCell) {
          pointsCell.textContent = "无 API Key";
        }
        setCellLines(expiryCell, ["无 API Key"], true);
        return;
      }
      if (pointsCell) {
        pointsCell.textContent = "加载中";
      }
      setCellLines(expiryCell, ["加载中"]);
      try {
        const result = await apiFetch(`/api/servers/summary/${account.id}`);
        if (pointsCell) {
          pointsCell.textContent =
            typeof result.points === "number" ? result.points : "未知";
        }
        const servers = Array.isArray(result.servers) ? result.servers : [];
        const filtered =
          whitelistIds.length > 0
            ? servers.filter((item) => whitelistIds.includes(Number(item.id)))
            : servers;
        if (filtered.length === 0) {
          setCellLines(
            expiryCell,
            [whitelistIds.length ? "白名单无匹配服务器" : "无服务器"],
            true
          );
        } else {
          setCellLines(expiryCell, filtered.map(formatServerLine));
        }
      } catch (err) {
        if (pointsCell) {
          pointsCell.textContent = "获取失败";
        }
        setCellLines(expiryCell, ["获取失败"], true);
      }
    })
  );
}

async function loadSettings() {
  const settings = await apiFetch("/api/system/settings");
  settingAutoRenew.checked = !!settings.auto_renew;
  settingRenewDays.value = settings.renew_threshold_days || 7;
  const cronValue = settings.cron_schedule || "0 8 * * *";
  settingCron.value = cronValue;
  parseCronToUI(cronValue);
  updateCronPreview();
  settingTimeout.value = settings.timeout ?? 15;
  settingMaxDelay.value = settings.max_delay ?? 90;
  settingDebug.checked = !!settings.debug;
  settingRequestTimeout.value = settings.request_timeout ?? 15;
  settingMaxRetries.value = settings.max_retries ?? 3;
  settingRetryDelay.value = settings.retry_delay ?? 2;
  settingDownloadTimeout.value = settings.download_timeout ?? 10;
  settingDownloadMaxRetries.value = settings.download_max_retries ?? 3;
  settingDownloadRetryDelay.value = settings.download_retry_delay ?? 2;
  settingCaptchaRetryLimit.value = settings.captcha_retry_limit ?? 5;
  settingCaptchaRetryUnlimited.checked = !!settings.captcha_retry_unlimited;
  settingCaptchaSaveSamples.checked = !!settings.captcha_save_samples;
  settingSkipPushTitle.value = settings.skip_push_title || "";
  notifyChannels = normalizeNotifyChannels(settings);
  renderNotifyList();
}

async function loadAll() {
  await Promise.all([loadAccounts(), loadSettings()]);
}

function setAccountFormVisible(visible) {
  if (!accountFormBody) return;
  accountFormBody.classList.toggle("hidden", !visible);
  resetFormBtn.classList.toggle("hidden", !visible);
  toggleAccountFormBtn.textContent = visible ? "收起" : "添加新账户";
}

function resetForm() {
  editingId = null;
  accountFormTitle.textContent = "新增账户";
  accountName.value = "";
  accountUsername.value = "";
  accountPassword.value = "";
  accountApiKey.value = "";
  accountRenew.value = "";
  accountEnabled.checked = true;
}

function fillForm(account) {
  editingId = account.id;
  accountFormTitle.textContent = `编辑账户 ${account.name || account.id}`;
  accountName.value = account.name || "";
  accountUsername.value = account.username || "";
  accountPassword.value = account.password || "";
  accountApiKey.value = account.api_key || "";
  accountRenew.value = (account.renew_products || []).join(",");
  accountEnabled.checked = !!account.enabled;
  setAccountFormVisible(true);
}

async function saveAccount() {
  const payload = {
    name: accountName.value.trim(),
    username: accountUsername.value.trim(),
    password: accountPassword.value.trim(),
    api_key: accountApiKey.value.trim(),
    renew_products: accountRenew.value
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean)
      .map((item) => Number(item)),
    enabled: accountEnabled.checked,
  };
  try {
    if (editingId) {
      await apiFetch(`/api/accounts/${editingId}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      showToast("账户已更新");
    } else {
      await apiFetch("/api/accounts", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      showToast("账户已新增");
    }
    resetForm();
    setAccountFormVisible(false);
    await loadAccounts();
  } catch (err) {
    showToast(err.message || "保存失败", "error");
  }
}

async function deleteAccount(id) {
  if (!confirm("确认删除该账户吗？")) {
    return;
  }
  try {
    await apiFetch(`/api/accounts/${id}`, { method: "DELETE" });
    showToast("账户已删除");
    await loadAccounts();
  } catch (err) {
    showToast(err.message || "删除失败", "error");
  }
}

async function runCheckin() {
  try {
    const results = await apiFetch("/api/actions/checkin", { method: "POST" });
    showToast(`执行完成，共${results.length}个账户`);
    await loadAccounts();
  } catch (err) {
    showToast(err.message || "签到失败", "error");
  }
}

async function testNotifyChannel(id) {
  try {
    await apiFetch("/api/system/notify/test", {
      method: "POST",
      body: JSON.stringify({ channel_id: id }),
    });
    showToast("测试通知已发送");
  } catch (err) {
    showToast(err.message || "测试发送失败", "error");
  }
}

async function runCheckinForAccount(id) {
  try {
    await apiFetch(`/api/actions/checkin/${id}`, { method: "POST" });
    showToast("签到已触发");
    await loadAccounts();
  } catch (err) {
    showToast(err.message || "签到失败", "error");
  }
}

async function runRenewAll() {
  if (!confirm("确认对所有有 API Key 的账号执行续费吗？")) {
    return;
  }
  try {
    const results = await apiFetch("/api/actions/renew", { method: "POST" });
    showToast(`续费已触发，共${results.length}个账号`);
  } catch (err) {
    showToast(err.message || "续费失败", "error");
  }
}

async function runRenewForAccount(id) {
  if (!confirm("确认对该账号执行续费吗？")) {
    return;
  }
  try {
    await apiFetch(`/api/actions/renew/${id}`, { method: "POST" });
    showToast("续费已触发");
  } catch (err) {
    showToast(err.message || "续费失败", "error");
  }
}

async function loadLogs() {
  if (!logOutput) return;
  try {
    const lines = await apiFetch("/api/logs?limit=200");
    logOutput.textContent = lines.join("\n");
    logOutput.scrollTop = logOutput.scrollHeight;
  } catch (err) {
    showToast(err.message || "日志获取失败", "error");
  }
}

function startLogPolling() {
  if (logTimer) return;
  logTimer = setInterval(loadLogs, 2000);
}

function stopLogPolling() {
  if (!logTimer) return;
  clearInterval(logTimer);
  logTimer = null;
}

function switchTab(tabName) {
  if (!tabMain || !tabLogs) return;
  tabButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === tabName);
  });
  tabMain.classList.toggle("hidden", tabName !== "main");
  tabLogs.classList.toggle("hidden", tabName !== "logs");
  if (tabName === "logs") {
    loadLogs();
    if (logAutoRefresh && logAutoRefresh.checked) {
      startLogPolling();
    }
  } else {
    stopLogPolling();
  }
}

async function saveSettings() {
  if (savingSettings) return;
  savingSettings = true;
  if (saveSettingsBtn) {
    saveSettingsBtn.disabled = true;
  }
  const notifyChannelsPayload = notifyChannels.map((item) => ({
    id: item.id,
    name: item.name,
    type: item.type,
    enabled: item.enabled !== false,
    config: typeof item.config === "object" && item.config ? item.config : {},
  }));
  const cronSchedule = buildCronFromUI();
  settingCron.value = cronSchedule;
  updateCronPreview();
  const payload = {
    auto_renew: settingAutoRenew.checked,
    renew_threshold_days: readNumberValue(settingRenewDays, 7),
    cron_schedule: cronSchedule || "0 8 * * *",
    timeout: readNumberValue(settingTimeout, 15),
    max_delay: readNumberValue(settingMaxDelay, 90),
    debug: settingDebug.checked,
    request_timeout: readNumberValue(settingRequestTimeout, 15),
    max_retries: readNumberValue(settingMaxRetries, 3),
    retry_delay: readNumberValue(settingRetryDelay, 2),
    download_timeout: readNumberValue(settingDownloadTimeout, 10),
    download_max_retries: readNumberValue(settingDownloadMaxRetries, 3),
    download_retry_delay: readNumberValue(settingDownloadRetryDelay, 2),
    captcha_retry_limit: readNumberValue(settingCaptchaRetryLimit, 5),
    captcha_retry_unlimited: settingCaptchaRetryUnlimited.checked,
    captcha_save_samples: settingCaptchaSaveSamples.checked,
    skip_push_title: settingSkipPushTitle.value.trim(),
    notify_config: {},
    notify_channels: notifyChannelsPayload,
  };
  try {
    await apiFetch("/api/system/settings", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    showToast("设置已保存");
  } catch (err) {
    showToast(err.message || "保存失败", "error");
  } finally {
    savingSettings = false;
    if (saveSettingsBtn) {
      saveSettingsBtn.disabled = false;
    }
  }
}

accountsBody.addEventListener("click", async (event) => {
  const action = event.target.getAttribute("data-action");
  const id = event.target.getAttribute("data-id");
  if (!action || !id) return;
  if (event.target.disabled) return;
  if (action === "edit") {
    const accounts = await apiFetch("/api/accounts");
    const account = accounts.find((item) => item.id === id);
    if (account) {
      fillForm(account);
    }
  }
  if (action === "delete") {
    await deleteAccount(id);
  }
  if (action === "checkin") {
    await runCheckinForAccount(id);
  }
  if (action === "renew") {
    await runRenewForAccount(id);
  }
});

if (notifyBody) {
  notifyBody.addEventListener("click", (event) => {
    const action = event.target.getAttribute("data-action");
    const id = event.target.getAttribute("data-id");
    if (!action || !id) return;
    if (action === "edit") {
      const channel = notifyChannels.find((item) => item.id === id);
      if (channel) {
        fillNotifyForm(channel);
      }
    }
    if (action === "delete") {
      notifyChannels = notifyChannels.filter((item) => item.id !== id);
      renderNotifyList();
    }
    if (action === "test") {
      testNotifyChannel(id);
    }
  });
}

loginBtn.addEventListener("click", handleLogin);
logoutBtn.addEventListener("click", () => {
  setToken(null);
  showLogin();
});
refreshAccountsBtn.addEventListener("click", loadAccounts);
checkinBtn.addEventListener("click", runCheckin);
renewBtn.addEventListener("click", runRenewAll);
resetFormBtn.addEventListener("click", resetForm);
saveAccountBtn.addEventListener("click", saveAccount);
saveSettingsBtn.addEventListener("click", saveSettings);

if (addNotifyBtn) {
  addNotifyBtn.addEventListener("click", () => {
    resetNotifyForm();
    setNotifyFormVisible(true);
  });
}
if (saveNotifyBtn) {
  saveNotifyBtn.addEventListener("click", () => {
    try {
      saveNotifyChannel();
    } catch (err) {
      showToast(err.message || "保存渠道失败", "error");
    }
  });
}
if (cancelNotifyBtn) {
  cancelNotifyBtn.addEventListener("click", () => {
    resetNotifyForm();
    setNotifyFormVisible(false);
  });
}
if (notifyType) {
  notifyType.addEventListener("change", () => {
    toggleNotifyFields(notifyType.value);
  });
}

toggleAccountFormBtn.addEventListener("click", () => {
  const isHidden = accountFormBody.classList.contains("hidden");
  if (isHidden) {
    resetForm();
    setAccountFormVisible(true);
  } else {
    setAccountFormVisible(false);
  }
});

tabButtons.forEach((button) => {
  button.addEventListener("click", () => {
    switchTab(button.dataset.tab);
  });
});

if (refreshLogsBtn) {
  refreshLogsBtn.addEventListener("click", loadLogs);
}
if (logAutoRefresh) {
  logAutoRefresh.addEventListener("change", () => {
    if (logAutoRefresh.checked && !tabLogs.classList.contains("hidden")) {
      startLogPolling();
    } else {
      stopLogPolling();
    }
  });
}

if (cronMode) {
  cronMode.addEventListener("change", () => {
    updateCronModeUI();
    updateCronPreview();
  });
  [cronHour, cronMinute, cronWeekday, cronMonthday].forEach((item) => {
    item.addEventListener("change", updateCronPreview);
  });
  settingCron.addEventListener("input", updateCronPreview);
}

initCronOptions();
updateCronModeUI();
setAccountFormVisible(false);
buildNotifyTypeOptions();
resetNotifyForm();
switchTab("main");

if (getToken()) {
  loadAll()
    .then(showDashboard)
    .catch(() => showLogin());
} else {
  showLogin();
}
