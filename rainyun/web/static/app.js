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
const resetFormBtn = document.getElementById("reset-form");
const saveAccountBtn = document.getElementById("save-account");
const accountFormTitle = document.getElementById("account-form-title");

const accountName = document.getElementById("account-name");
const accountUsername = document.getElementById("account-username");
const accountPassword = document.getElementById("account-password");
const accountApiKey = document.getElementById("account-api-key");
const accountRenew = document.getElementById("account-renew");
const accountEnabled = document.getElementById("account-enabled");

const settingAutoRenew = document.getElementById("setting-auto-renew");
const settingRenewDays = document.getElementById("setting-renew-days");
const settingCron = document.getElementById("setting-cron");
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
const settingNotifyConfig = document.getElementById("setting-notify-config");
const saveSettingsBtn = document.getElementById("save-settings");

let editingId = null;

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

function readNumberValue(input, fallback) {
  const raw = input.value.trim();
  if (!raw) {
    return fallback;
  }
  const value = Number(raw);
  return Number.isFinite(value) ? value : fallback;
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
  accounts.forEach((account) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${account.name || account.id}</td>
      <td>${account.enabled ? "是" : "否"}</td>
      <td>${account.last_status || "-"}</td>
      <td>${account.last_checkin || "-"}</td>
      <td>
        <button class="ghost-btn" data-action="edit" data-id="${account.id}">编辑</button>
        <button class="ghost-btn" data-action="delete" data-id="${account.id}">删除</button>
      </td>
    `;
    accountsBody.appendChild(row);
  });
}

async function loadSettings() {
  const settings = await apiFetch("/api/system/settings");
  settingAutoRenew.checked = !!settings.auto_renew;
  settingRenewDays.value = settings.renew_threshold_days || 7;
  settingCron.value = settings.cron_schedule || "0 8 * * *";
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
  const notifyConfig = settings.notify_config || {};
  settingNotifyConfig.value = JSON.stringify(notifyConfig, null, 2);
}

async function loadAll() {
  await Promise.all([loadAccounts(), loadSettings()]);
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

async function saveSettings() {
  let notifyConfig = {};
  const notifyRaw = settingNotifyConfig.value.trim();
  if (notifyRaw) {
    try {
      notifyConfig = JSON.parse(notifyRaw);
    } catch (err) {
      showToast("通知配置 JSON 无效", "error");
      return;
    }
    if (typeof notifyConfig !== "object" || Array.isArray(notifyConfig)) {
      showToast("通知配置需为对象", "error");
      return;
    }
  }
  const payload = {
    auto_renew: settingAutoRenew.checked,
    renew_threshold_days: readNumberValue(settingRenewDays, 7),
    cron_schedule: settingCron.value.trim() || "0 8 * * *",
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
    notify_config: notifyConfig,
  };
  try {
    await apiFetch("/api/system/settings", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    showToast("设置已保存");
  } catch (err) {
    showToast(err.message || "保存失败", "error");
  }
}

accountsBody.addEventListener("click", async (event) => {
  const action = event.target.getAttribute("data-action");
  const id = event.target.getAttribute("data-id");
  if (!action || !id) return;
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
});

loginBtn.addEventListener("click", handleLogin);
logoutBtn.addEventListener("click", () => {
  setToken(null);
  showLogin();
});
refreshAccountsBtn.addEventListener("click", loadAccounts);
checkinBtn.addEventListener("click", runCheckin);
resetFormBtn.addEventListener("click", resetForm);
saveAccountBtn.addEventListener("click", saveAccount);
saveSettingsBtn.addEventListener("click", saveSettings);

if (getToken()) {
  loadAll()
    .then(showDashboard)
    .catch(() => showLogin());
} else {
  showLogin();
}
