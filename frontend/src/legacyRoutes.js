// Preserve bookmarks shared before the switch from HashRouter to BrowserRouter.
export function migrateLegacyHashRoute() {
  const { hash, origin } = window.location;
  if (!hash.startsWith('#/')) return;

  let target;
  try {
    target = new URL(hash.slice(1), origin);
  } catch {
    return;
  }
  // A fragment must never turn into a redirect to a different site.
  if (target.origin !== origin) return;
  // Keep the verified absolute URL: a normalized path may start with '//'.
  window.history.replaceState(window.history.state, '', target.href);
}
