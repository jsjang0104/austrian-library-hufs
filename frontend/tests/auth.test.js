import assert from 'node:assert/strict';
import { beforeEach, test } from 'node:test';
import { build } from 'esbuild';
import axios from 'axios';

// Only browser storage and the HTTP transport are replaced. The application
// interceptors, token updates, and logout logic execute unchanged.
function storage() {
  const items = new Map();
  return {
    getItem: (key) => items.get(key) ?? null,
    setItem: (key, value) => items.set(key, String(value)),
    removeItem: (key) => items.delete(key),
    clear: () => items.clear(),
  };
}
let api;
let calls;
let transport;
const tokens = { access: 'access-one', refresh: 'refresh-one', name: 'Reader', sid: '123', role: 'UNDERGRADUATE' };
const response = (config, data = {}, status = 200) => ({ config, data, status, statusText: '', headers: {} });
const unauthorized = (config) => Promise.reject(new axios.AxiosError('Unauthorized', 'ERR_BAD_REQUEST', config, null, response(config, {}, 401)));

beforeEach(async () => {
  globalThis.localStorage = storage();
  globalThis.sessionStorage = storage();
  globalThis.window = new EventTarget();
  window.location = { href: '/', origin: 'https://library.example' };
  calls = [];
  transport = (config) => Promise.resolve(response(config, tokens));
  axios.defaults.adapter = (config) => {
    calls.push(config);
    return transport(config);
  };
  const { outputFiles } = await build({
    entryPoints: ['src/api.jsx'], bundle: true, write: false,
    format: 'esm', packages: 'external',
    define: { 'import.meta.env': JSON.stringify({ VITE_API_URL: 'https://api.example' }) },
  });
  const code = outputFiles[0].text.replaceAll('from "axios"', `from ${JSON.stringify(import.meta.resolve('axios'))}`);
  api = await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}#${Math.random()}`);
});

test('login keeps credentials in this tab and removes only legacy auth data', async () => {
  localStorage.setItem('accessToken', 'legacy');
  localStorage.setItem('refreshToken', 'legacy-refresh');
  localStorage.setItem('theme', 'dark');
  await api.loginUser('123', 'password');
  assert.equal(sessionStorage.getItem('accessToken'), 'access-one');
  assert.equal(sessionStorage.getItem('refreshToken'), 'refresh-one');
  assert.equal(localStorage.getItem('accessToken'), null);
  assert.equal(localStorage.getItem('refreshToken'), null);
  assert.equal(localStorage.getItem('theme'), 'dark');
});

test('refresh rotation replaces both tokens and retries with the new access token', async () => {
  await api.loginUser('123', 'password');
  transport = (config) => {
    if (config.url.includes('/api/token/refresh/')) return Promise.resolve(response(config, { access: 'access-two', refresh: 'refresh-two' }));
    if (!config._retry) return unauthorized(config);
    return Promise.resolve(response(config, { authorizedAs: config.headers.Authorization }));
  };
  const result = await api.default.get('/api/loans/');
  assert.equal(result.data.authorizedAs, 'Bearer access-two');
  assert.equal(sessionStorage.getItem('refreshToken'), 'refresh-two');
});

test('logout revokes the refresh token and clears credentials even when the server fails', async () => {
  await api.loginUser('123', 'password');
  sessionStorage.setItem('theme', 'dark');
  transport = () => Promise.reject(new Error('Offline'));
  await api.logoutUser();
  const logout = calls.find((config) => config.url.includes('/api/token/logout/'));
  assert.ok(logout, 'logout must request server-side token revocation');
  assert.equal(JSON.parse(logout.data).refresh, 'refresh-one');
  assert.equal(sessionStorage.getItem('accessToken'), null);
  assert.equal(sessionStorage.getItem('refreshToken'), null);
  assert.equal(sessionStorage.getItem('theme'), 'dark');
  transport = (config) => Promise.resolve(response(config));
  await api.default.get('/api/notices/');
  assert.equal(calls.at(-1).headers.Authorization, undefined);
});

test('logging out while refresh is pending cannot restore credentials or retry protected requests', async () => {
  await api.loginUser('123', 'password');
  let finishRefresh;
  let startedRefresh;
  const started = new Promise((resolve) => { startedRefresh = resolve; });
  transport = (config) => {
    if (config.url.includes('/api/token/refresh/')) {
      startedRefresh();
      return new Promise((resolve) => { finishRefresh = () => resolve(response(config, { access: 'access-two', refresh: 'refresh-two' })); });
    }
    if (config.url.includes('/api/token/logout/')) return Promise.resolve(response(config, {}, 204));
    if (!config._retry) return unauthorized(config);
    return Promise.resolve(response(config));
  };
  const pending = api.default.get('/api/loans/');
  const rejected = assert.rejects(pending);
  await started;
  await api.logoutUser();
  finishRefresh();
  await rejected;
  assert.equal(sessionStorage.getItem('accessToken'), null);
  assert.equal(sessionStorage.getItem('refreshToken'), null);
  assert.equal(calls.filter((config) => config.url === '/api/loans/').length, 1);
});

test('concurrent unauthorized requests share one refresh and use the rotated credentials', async () => {
  await api.loginUser('123', 'password');
  let finishRefresh;
  let startedRefresh;
  const started = new Promise((resolve) => { startedRefresh = resolve; });
  transport = (config) => {
    if (config.url === '/api/token/refresh/') {
      startedRefresh();
      return new Promise((resolve) => { finishRefresh = () => resolve(response(config, { access: 'access-two', refresh: 'refresh-two' })); });
    }
    if (!config._retry) return unauthorized(config);
    return Promise.resolve(response(config, { authorizedAs: config.headers.Authorization }));
  };
  const first = api.default.get('/api/loans/');
  const second = api.default.get('/api/notices/');
  await started;
  finishRefresh();
  const responses = await Promise.all([first, second]);
  assert.deepEqual(responses.map((result) => result.data.authorizedAs), ['Bearer access-two', 'Bearer access-two']);
  assert.equal(calls.filter((config) => config.url === '/api/token/refresh/').length, 1);
});

test('failed refresh clears authentication without clearing unrelated browser data', async () => {
  await api.loginUser('123', 'password');
  sessionStorage.setItem('theme', 'dark');
  transport = unauthorized;
  await assert.rejects(api.default.get('/api/loans/'));
  assert.equal(sessionStorage.getItem('accessToken'), null);
  assert.equal(sessionStorage.getItem('refreshToken'), null);
  assert.equal(sessionStorage.getItem('theme'), 'dark');
  assert.equal(window.location.href, '/#/login');
  assert.equal(calls.filter((config) => config.url === '/api/token/refresh/').length, 1);
});
