import assert from 'node:assert/strict';
import { after, afterEach, before, beforeEach, test } from 'node:test';
import { build } from 'esbuild';
import { JSDOM } from 'jsdom';

let dom;
let act;
let axios;
let root;
let alerts;
let calls;
let transport;
const tokens = { access: 'test-access', refresh: 'test-refresh', name: 'Reader', sid: '123' };
const response = (config, data = tokens, status = 200) => ({ config, data, status, statusText: '', headers: {} });

before(async () => {
  dom = new JSDOM('<div id="root"></div>', { url: 'https://library.example/#/login' });
  for (const key of ['window', 'document', 'localStorage', 'sessionStorage', 'Event', 'HTMLElement', 'HTMLInputElement', 'Node']) {
    globalThis[key] = dom.window[key];
  }
  Object.defineProperty(globalThis, 'navigator', { value: dom.window.navigator, configurable: true });
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  ({ act } = await import('react'));
  ({ default: axios } = await import('axios'));
});

beforeEach(async () => {
  localStorage.clear();
  sessionStorage.clear();
  window.history.replaceState(null, '', '/#/login');
  alerts = [];
  calls = [];
  globalThis.alert = (message) => alerts.push(message);
  transport = (config) => Promise.resolve(response(config));
  axios.defaults.adapter = (config) => {
    calls.push(config);
    return transport(config);
  };
  // Run the real Login component, router, AuthProvider and API interceptors.
  // Only the network transport is replaced; no production account is used.
  const { outputFiles } = await build({
    stdin: {
      contents: `
        import React from 'react';
        import { createRoot } from 'react-dom/client';
        import { HashRouter, Routes, Route } from 'react-router-dom';
        import Login from './src/Login.jsx';
        import { AuthProvider, useAuth } from './src/AuthContext.jsx';
        function Home() {
          const { user } = useAuth();
          return <p data-testid="home">{user?.name}</p>;
        }
        export function mount(node) {
          const root = createRoot(node);
          root.render(<React.StrictMode><HashRouter><AuthProvider><Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/" element={<Home />} />
          </Routes></AuthProvider></HashRouter></React.StrictMode>);
          return root;
        }
      `,
      loader: 'jsx', resolveDir: process.cwd(),
    },
    bundle: true, write: false, format: 'esm', packages: 'external',
    loader: { '.css': 'empty' },
    define: { 'import.meta.env': JSON.stringify({ VITE_API_URL: 'https://api.example' }) },
  });
  const code = outputFiles[0].text.replace(/from "([^".][^"]*)"/g, (_, name) => `from ${JSON.stringify(import.meta.resolve(name))}`);
  const { mount } = await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}#${Math.random()}`);
  await act(async () => { root = mount(document.querySelector('#root')); });
  await enter('#sid-input', '123');
  await enter('#password-input', 'test-password');
});

afterEach(async () => {
  await act(async () => root?.unmount());
});
after(() => dom.window.close());

async function enter(selector, value) {
  await act(async () => {
    const input = document.querySelector(selector);
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, value);
    input.dispatchEvent(new Event('input', { bubbles: true }));
  });
}

function submit(form = document.querySelector('form')) {
  form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
}

test('one successful submission displays only success and opens the signed-in home page', async () => {
  await act(async () => submit());
  assert.deepEqual(alerts, ['로그인에 성공했습니다!']);
  assert.equal(calls.length, 1);
  assert.equal(window.location.hash, '#/');
  assert.equal(document.querySelector('[data-testid="home"]').textContent, 'Reader');
});

test('rapid repeated submissions send one request and never show an error after success', async () => {
  const pending = [];
  transport = (config) => new Promise((resolve) => pending.push(() => resolve(response(config))));
  await act(async () => {
    const form = document.querySelector('form');
    submit(form);
    submit(form); // Same event turn: catches guards that rely only on React state.
  });
  const buttonWasDisabled = document.querySelector('button[type="submit"]').disabled;
  const passwordWasDisabled = document.querySelector('#password-input').disabled;
  await act(async () => submit()); // Repeated Enter while the request is pending.
  await act(async () => pending.forEach((finish) => finish()));
  assert.deepEqual(alerts, ['로그인에 성공했습니다!']);
  assert.equal(calls.length, 1);
  assert.equal(buttonWasDisabled, true);
  assert.equal(passwordWasDisabled, true);
  assert.equal(sessionStorage.getItem('accessToken'), 'test-access');
  assert.equal(window.location.hash, '#/');
});

for (const [status, message] of [
  [401, '학번 또는 비밀번호가 일치하지 않습니다.'],
  [429, '로그인 시도가 너무 잦습니다. 잠시 후 다시 시도해주세요.'],
  [null, '로그인 중 오류가 발생했습니다.'],
]) {
  test(`a failed login (${status ?? 'offline'}) shows one error and allows retry`, async () => {
    transport = (config) => Promise.reject(status
      ? new axios.AxiosError('Request failed', 'ERR_BAD_REQUEST', config, null, response(config, {}, status))
      : new Error('Offline'));
    await act(async () => submit());
    assert.deepEqual(alerts, [message]);
    assert.equal(window.location.hash, '#/login');
    assert.equal(sessionStorage.getItem('accessToken'), null);
    assert.equal(document.querySelector('#password-input').value, '');
    assert.equal(document.querySelector('button[type="submit"]').disabled, false);
    transport = (config) => Promise.resolve(response(config));
    await enter('#password-input', 'correct-password');
    await act(async () => submit());
    assert.deepEqual(alerts, [message, '로그인에 성공했습니다!']);
    assert.equal(calls.length, 2);
    assert.equal(window.location.hash, '#/');
  });
}
