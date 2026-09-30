import assert from 'node:assert/strict';
import { after, afterEach, before, beforeEach, test } from 'node:test';
import { build } from 'esbuild';
import { JSDOM } from 'jsdom';

let dom;
let act;
let mount;
let migrateLegacyHashRoute;
let root;
let calls;
let noticeStatus;

before(async () => {
  dom = new JSDOM('<div id="root"></div>', { url: 'https://library.example/' });
  for (const key of ['window', 'document', 'localStorage', 'sessionStorage', 'Event', 'HTMLElement', 'Node']) {
    globalThis[key] = dom.window[key];
  }
  Object.defineProperty(globalThis, 'navigator', { value: dom.window.navigator, configurable: true });
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  globalThis.alert = () => {};
  ({ act } = await import('react'));
  const { default: axios } = await import('axios');
  axios.defaults.adapter = async (config) => {
    calls.push(config);
    let data = [];
    if (/\/api\/notices\/\d+\/$/.test(config.url)) {
      if (noticeStatus !== 200) {
        throw new axios.AxiosError('Not found', 'ERR_BAD_REQUEST', config, null, { status: noticeStatus });
      }
      data = { notice_id: 7, title: '도서관 운영 안내', content: '공개 공지 내용', post_date: '2026-09-30', view_count: 1 };
    }
    return { config, data, status: 200, statusText: 'OK', headers: {} };
  };
  const { outputFiles } = await build({
    stdin: {
      contents: `
        import React from 'react';
        import { createRoot } from 'react-dom/client';
        import { BrowserRouter } from 'react-router-dom';
        import App from './src/App.jsx';
        import { AuthProvider } from './src/AuthContext.jsx';
        export { migrateLegacyHashRoute } from './src/legacyRoutes.js';
        export function mount(node) {
          const root = createRoot(node);
          root.render(<React.StrictMode><BrowserRouter><AuthProvider><App /></AuthProvider></BrowserRouter></React.StrictMode>);
          return root;
        }
      `,
      loader: 'jsx', resolveDir: process.cwd(),
    },
    bundle: true, write: false, format: 'esm', packages: 'external',
    loader: { '.css': 'empty', '.png': 'empty', '.jpg': 'empty', '.gif': 'empty' },
    define: { 'import.meta.env': JSON.stringify({ VITE_API_URL: 'https://api.example' }) },
  });
  const code = outputFiles[0].text.replace(/from "([^".][^"]*)"/g, (_, name) => `from ${JSON.stringify(import.meta.resolve(name))}`);
  ({ mount, migrateLegacyHashRoute } = await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`));
});

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
  window.history.replaceState(null, '', '/');
  calls = [];
  noticeStatus = 200;
});
afterEach(async () => {
  await act(async () => root?.unmount());
  root = null;
});
after(() => dom.window.close());

async function open(path) {
  window.history.replaceState(null, '', path);
  migrateLegacyHashRoute();
  await act(async () => { root = mount(document.querySelector('#root')); });
}

function isNoindex() {
  const tags = [...document.head.querySelectorAll('meta[name="robots"]')];
  assert.ok(tags.length <= 1, 'navigation must not leave duplicate robots metadata');
  return tags.some((tag) => tag.content.includes('noindex'));
}

for (const path of ['/', '/info', '/about', '/board', '/notice/7']) {
  test(`public page ${path} remains indexable and uses ordinary links`, async () => {
    await open(path);
    assert.equal(isNoindex(), false);
    assert.equal(document.querySelector('nav.main-nav a').getAttribute('href'), '/search');
    if (path === '/notice/7') assert.match(document.body.textContent, /공개 공지 내용/);
  });
}

for (const path of ['/search?search=Kafka&ai=1', '/login', '/register']) {
  test(`${path} is excluded without leaving noindex on a public page after navigation`, async () => {
    await open(path);
    assert.equal(isNoindex(), true);
    await act(async () => document.querySelector('a[href="/info"]').click());
    assert.equal(window.location.pathname, '/info');
    assert.equal(isNoindex(), false);
    await act(async () => document.querySelector('a[href="/search"]').click());
    assert.equal(isNoindex(), true);
  });
}

test('anonymous readers cannot access loans through a direct mypage link', async () => {
  await open('/mypage');
  assert.equal(window.location.pathname, '/login');
  assert.equal(isNoindex(), true);
  assert.equal(calls.some((call) => call.url === '/api/loans/'), false);
});

test('signed-in readers can view their library with noindex', async () => {
  sessionStorage.setItem('accessToken', 'test-access');
  sessionStorage.setItem('userName', 'Reader');
  sessionStorage.setItem('userSid', '123');
  await open('/mypage');
  assert.equal(window.location.pathname, '/mypage');
  assert.equal(isNoindex(), true);
  assert.match(document.body.textContent, /대출 현황/);
});

test('old hash search links preserve their query and stay on this origin', async () => {
  await open('/#/search?search=Kafka%20Wien&ai=1');
  assert.equal(window.location.pathname, '/search');
  assert.equal(window.location.search, '?search=Kafka%20Wien&ai=1');
  assert.equal(window.location.hash, '');
  assert.equal(isNoindex(), true);
  assert.ok(calls.some((call) => call.url === '/api/books/smart_search/' && call.params.q === 'Kafka Wien'));
});

test('legacy conversion preserves normal anchors and rejects external destinations', () => {
  for (const path of ['/info#hours', '/#//attacker.example/login', '/#/\\attacker.example/login']) {
    window.history.replaceState(null, '', path);
    const before = window.location.href;
    migrateLegacyHashRoute();
    assert.equal(window.location.href, before);
  }
});

test('missing pages display a recovery link and are excluded from indexing', async () => {
  await open('/not-a-page');
  assert.equal(isNoindex(), true);
  assert.match(document.body.textContent, /페이지를 찾을 수 없습니다/);
  assert.ok(document.querySelector('main a[href="/"]'));
});

test('a missing notice is excluded even though valid notices are public', async () => {
  noticeStatus = 404;
  await open('/notice/999');
  assert.equal(isNoindex(), true);
});

test('normalized legacy paths cannot be reinterpreted as a different origin', () => {
  for (const path of ['/#/.//attacker.example/login', '/#/foo/..//attacker.example/login', '/#/%2e//attacker.example/login']) {
    window.history.replaceState(null, '', path);
    assert.doesNotThrow(() => migrateLegacyHashRoute());
    assert.equal(window.location.origin, 'https://library.example');
    assert.equal(window.location.pathname, '//attacker.example/login');
  }
});
