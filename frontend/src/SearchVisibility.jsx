import React from 'react';
import { matchPath, useLocation } from 'react-router-dom';

const PUBLIC_PAGES = ['/', '/info', '/about', '/board', '/notice/:noticeId'];

export default function SearchVisibility() {
  const { pathname } = useLocation();
  const isPublic = PUBLIC_PAGES.some((path) => matchPath({ path, end: true }, pathname));
  // React 19 places this in <head> and removes it when navigating to a public page.
  // Keep public pages free of an explicit "index" so error views can use noindex.
  return isPublic ? null : <meta name="robots" content="noindex, follow" />;
}
