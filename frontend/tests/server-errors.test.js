import assert from 'node:assert/strict';
import { after, afterEach, before, beforeEach, test } from 'node:test';
import { build } from 'esbuild';
import { JSDOM } from 'jsdom';

let dom;
let act;
let mount;
let root;
let transport;
let axios;
const response = (config, data = []) => ({ config, data, status: 200, statusText: 'OK', headers: {} });

before(async () => {
  dom = new JSDOM('<div id="root"></div>', { url: 'https://library.example/' });
  for (const key of ['window', 'document', 'localStorage', 'sessionStorage', 'Event', 'FormData', 'HTMLElement', 'HTMLInputElement', 'Node']) {
    globalThis[key] = dom.window[key];
  }
  Object.defineProperty(globalThis, 'navigator', { value: dom.window.navigator, configurable: true });
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  globalThis.alert = () => {};
  ({ act } = await import('react'));
  ({ default: axios } = await import('axios'));
  axios.defaults.adapter = (config) => transport(config);
  const { outputFiles } = await build({
    stdin: {
      contents: `
        import React from 'react';
        import { createRoot } from 'react-dom/client';
        import { BrowserRouter } from 'react-router-dom';
        import App from './src/App.jsx';
        import { AuthProvider } from './src/AuthContext.jsx';
        export function mount(node) {
          const root = createRoot(node);
          root.render(<BrowserRouter><AuthProvider><App /></AuthProvider></BrowserRouter>);
          return root;
        }
      `,
      loader: 'jsx', resolveDir: process.cwd(),
    },
    bundle: true, write: false, format: 'esm', packages: 'external',
    loader: { '.css': 'empty', '.png': 'empty', '.jpg': 'empty', '.gif': 'empty' },
    define: { 'import.meta.env': JSON.stringify({ VITE_API_URL: 'https://api.example' }) },
  });
  const code = outputFiles[0].text.replace(/from "([^".][^"]*)"/g,
    (_, name) => `from ${JSON.stringify(import.meta.resolve(name))}`);
  ({ mount } = await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`));
});

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
  transport = () => Promise.reject(new Error('Offline'));
});
afterEach(async () => {
  await act(async () => root?.unmount());
  root = null;
});
after(() => dom.window.close());

async function open(path) {
  window.history.replaceState(null, '', path);
  await act(async () => { root = mount(document.querySelector('#root')); });
}

async function enter(selector, value) {
  await act(async () => {
    const input = document.querySelector(selector);
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, value);
    input.dispatchEvent(new Event('input', { bubbles: true }));
  });
}

async function submit() {
  await act(async () => document.querySelector('main form')
    .dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })));
}

function assertRefreshGuidance() {
  const error = document.querySelector('main [role="alert"], #notice-list [role="alert"]');
  assert.ok(error, 'API failures must show an error rather than an empty result');
  const korean = [...error.querySelectorAll('[lang="ko"]')].map((node) => node.textContent).join(' ');
  const german = [...error.querySelectorAll('[lang="de"]')].map((node) => node.textContent).join(' ');
  assert.match(korean, /ctrl\+shift\+R/);
  assert.match(korean, /command\+shift\+R/);
  assert.match(german, /Strg\+Umschalt\+R/);
  assert.match(german, /Command\+Umschalt\+R/);
}

for (const path of ['/', '/board', '/notice/7', '/search?search=Kafka', '/search?search=Kafka&ai=1', '/mypage']) {
  for (const status of [null, 503]) {
    test(`${path} shows bilingual refresh guidance when the API is ${status ?? 'offline'}`, async () => {
      if (path === '/mypage') {
        sessionStorage.setItem('accessToken', 'test-access');
        sessionStorage.setItem('userName', 'Reader');
        sessionStorage.setItem('userSid', '123');
      }
      if (status) transport = (config) => Promise.reject(new axios.AxiosError(
        'Service unavailable', 'ERR_BAD_RESPONSE', config, null, { ...response(config), status }));
      await open(path);
      assertRefreshGuidance();
      assert.doesNotMatch(document.querySelector('main').textContent, /검색 결과가 없습니다|대출 기록이 없습니다/);
    });
  }
}

test('a successful search retry clears the error and renders the new results', async () => {
  await open('/search?search=Kafka');
  assertRefreshGuidance();
  transport = (config) => Promise.resolve(response(config, [
    { book_id: 1, call_number: 'K-1', title: 'Die Verwandlung', author: 'Franz Kafka', status: 'AVAILABLE' },
  ]));
  await submit();
  assert.equal(document.querySelector('main [role="alert"]'), null);
  assert.match(document.querySelector('main').textContent, /Die Verwandlung/);
});

for (const path of ['/login', '/register']) {
  test(`${path} shows refresh guidance for a server failure and clears it on validation errors`, async () => {
    await open(path);
    await enter('#sid-input', '123');
    await enter('#password-input', 'test-password');
    if (path === '/register') {
      await enter('#name-input', 'Reader');
      await enter('#email-input', 'reader@example.com');
      await enter('#password-confirm-input', 'test-password');
    }
    await submit();
    assertRefreshGuidance();
    transport = (config) => Promise.reject(new axios.AxiosError(
      'Invalid input', 'ERR_BAD_REQUEST', config, null, { ...response(config, { sid: ['Already registered'] }), status: 400 }));
    await enter('#password-input', 'test-password');
    await submit();
    assert.equal(document.querySelector('main [role="alert"]'), null);
  });
}
