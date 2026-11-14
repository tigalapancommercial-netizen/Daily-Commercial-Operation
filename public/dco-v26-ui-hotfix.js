/**
 * Tigalapan Daily Commercial Operation - v26 UI-only hotfix
 *
 * Purpose:
 *   1. Hide the floating v25 Draft/Foto STATUS TOOLBAR without removing it.
 *   2. Correct cramped account/role card sizing inside the left sidebar.
 *
 * IMPORTANT: this does not replace or disable src/drafts.js, IndexedDB, service
 * worker, photo queue or server upload. The application itself must implement
 * automatic draft restoration before the manual recovery UI can be retired.
 *
 * Include using: <script src="./dco-v26-ui-hotfix.js" defer></script>
 */
(() => {
  'use strict';
  if (window.__DCO_V26_UI_HOTFIX_INSTALLED__) return;
  window.__DCO_V26_UI_HOTFIX_INSTALLED__ = true;

  const STYLE_ID = 'dco-v26-ui-hotfix-style';
  const PANEL_CLASS = 'dco-v26-draft-toolbar-hidden';
  const PROFILE_CLASS = 'dco-v26-profile-card';
  const RECOVERY_CLASS = 'dco-v26-recovery-visible';
  const NAME_CLASS = 'dco-v26-profile-name';
  const ROLE_CLASS = 'dco-v26-profile-role';

  const styles = `
    /* Toolbar remains mounted so existing draft handlers keep functioning. */
    .${PANEL_CLASS} {
      display: none !important;
      visibility: hidden !important;
      pointer-events: none !important;
    }
    /* Emergency-only recovery: Ctrl+Alt+D reveals the old toolbar. */
    .${PANEL_CLASS}.${RECOVERY_CLASS} {
      display: flex !important;
      visibility: visible !important;
      pointer-events: auto !important;
    }

    /* Scoped to the compact sidebar profile card; never changes global nav. */
    .${PROFILE_CLASS} {
      box-sizing: border-box !important;
      height: auto !important;
      min-height: 64px !important;
      max-height: none !important;
      min-width: 0 !important;
      max-width: 100% !important;
      padding: 11px 12px !important;
      display: flex !important;
      flex-direction: column !important;
      align-items: flex-start !important;
      justify-content: center !important;
      gap: 2px !important;
      overflow: hidden !important;
      border-radius: 13px !important;
      flex-shrink: 0 !important;
    }
    .${PROFILE_CLASS} .${NAME_CLASS} {
      display: block !important;
      max-width: 100% !important;
      overflow: hidden !important;
      white-space: nowrap !important;
      text-overflow: ellipsis !important;
      font-size: 14px !important;
      font-weight: 650 !important;
      line-height: 1.4 !important;
      min-width: 0 !important;
    }
    .${PROFILE_CLASS} .${ROLE_CLASS} {
      display: block !important;
      max-width: 100% !important;
      overflow: hidden !important;
      white-space: nowrap !important;
      text-overflow: ellipsis !important;
      font-size: 12px !important;
      line-height: 1.35 !important;
      min-width: 0 !important;
    }
    @media (max-width: 550px) {
      .${PROFILE_CLASS} { min-height: 60px !important; padding: 10px 11px !important; }
      .${PROFILE_CLASS} .${NAME_CLASS} { font-size: 13px !important; }
      .${PROFILE_CLASS} .${ROLE_CLASS} { font-size: 11px !important; }
    }
  `;

  const norm = (s) => String(s ?? '').replace(/\s+/g, ' ').trim();
  const lower = (s) => norm(s).toLocaleLowerCase('id-ID');
  const isDraftButton = (text) => /^(?:[^a-z\d]+\s*)?draft\s*$/i.test(norm(text));
  const isPhotoButton = (text) => /^(?:[^a-z\d]+\s*)?foto\s*$/i.test(norm(text));
  const isCounter = (text) => /\b\d+\s+draft\b/i.test(text) && /\b\d+\s+foto\b/i.test(text);
  const rolePattern = /^(master|administrator|admin|superadmin|spv|supervisor|viewer|store)\s*[·•|\-]\s*.+$/i;

  function injectStyle() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = styles;
    (document.head || document.documentElement).append(style);
  }

  function findDraftToolbarFromButton(button) {
    let node = button.parentElement;
    for (let level = 0; node && level < 5; level++, node = node.parentElement) {
      if (!node.querySelectorAll || node === document.body) break;
      const t = norm(node.textContent);
      if (t.length > 150 || !isCounter(t)) continue;
      const buttons = [...node.querySelectorAll('button, [role="button"]')];
      if (buttons.length > 8 || !buttons.some(el => isPhotoButton(el.textContent))) continue;
      if (!buttons.some(el => isDraftButton(el.textContent))) continue;
      return node;
    }
    return null;
  }

  function hideDraftToolbar() {
    const buttons = document.querySelectorAll('button, [role="button"]');
    for (const button of buttons) {
      if (!isDraftButton(button.textContent)) continue;
      const bar = findDraftToolbarFromButton(button);
      if (bar && !bar.classList.contains(PANEL_CLASS)) {
        bar.classList.add(PANEL_CLASS);
        bar.dataset.dcoV26UiHidden = '1';
      }
    }
  }

  function ownText(el) {
    return norm([...el.childNodes].filter(n => n.nodeType === 3).map(n => n.nodeValue).join(' '));
  }

  function findRoleLeaves() {
    return [...document.querySelectorAll('small, span, p, div, label')].filter(el => {
      if (el.childElementCount > 0 && !ownText(el)) return false;
      const text = ownText(el) || norm(el.textContent);
      return text.length < 85 && rolePattern.test(text);
    });
  }

  function findProfileCard(roleEl) {
    const roleText = lower(roleEl.textContent);
    let node = roleEl.parentElement;
    for (let level = 0; node && level < 4; level++, node = node.parentElement) {
      if (node.matches?.('aside, nav, body, main')) break;
      const text = norm(node.textContent);
      // Require a username AND role in this small local card: never style sidebar root.
      if (text.length <= roleText.length + 2 || text.length > 150) continue;
      if (!lower(text).includes(roleText)) continue;
      if (node.querySelectorAll('button, input').length > 0) continue;
      // Prefer the smallest parent that contains both username and role.
      return node;
    }
    return null;
  }

  function adjustProfileCard() {
    for (const roleEl of findRoleLeaves()) {
      const card = findProfileCard(roleEl);
      if (!card) continue;
      const rect = card.getBoundingClientRect();
      // Guard against accidentally changing full-width panels.
      if (rect.width > 380 && rect.width !== 0) continue;
      card.classList.add(PROFILE_CLASS);
      roleEl.classList.add(ROLE_CLASS);
      const nameEl = [...card.querySelectorAll('strong, b, span, p, div')].find(el => {
        if (el === roleEl || el.contains(roleEl)) return false;
        const s = norm(el.textContent);
        return s.length > 1 && s.length < 80 && !rolePattern.test(s);
      });
      if (nameEl) nameEl.classList.add(NAME_CLASS);
    }
  }

  let scheduled = false;
  function scanSoon() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      scheduled = false;
      hideDraftToolbar();
      adjustProfileCard();
    });
  }

  function start() {
    injectStyle();
    scanSoon();
    if (!document.body) return;
    const observer = new MutationObserver(records => {
      // Re-rendered menus may add the toolbar and user card later.
      if (records.some(record => record.addedNodes.length || record.removedNodes.length)) scanSoon();
    });
    observer.observe(document.body, { subtree: true, childList: true });
    window.addEventListener('pageshow', scanSoon, { passive: true });
    // Non-visible escape hatch until app-specific automatic recovery is verified.
    window.addEventListener('keydown', (event) => {
      if (!event.ctrlKey || !event.altKey || lower(event.key) !== 'd') return;
      event.preventDefault();
      for (const toolbar of document.querySelectorAll('.' + PANEL_CLASS)) {
        toolbar.classList.toggle(RECOVERY_CLASS);
      }
    });
    window.DCOv26UI = Object.freeze({ rescan: scanSoon, version: '26.1-ui' });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();
})();
