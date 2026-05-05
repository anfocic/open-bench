import { withViewTransition } from '../lib/view-transition';

export function initTabs(fallback?: string) {
  const tabList = document.querySelector('[role="tablist"]');
  const tabs = [...document.querySelectorAll<HTMLButtonElement>('.tab[role="tab"]')];
  const panels = [...document.querySelectorAll<HTMLElement>('.tab-panel[role="tabpanel"]')];
  const validNames = panels.map(p => p.dataset.panel!);
  const defaultName = fallback ?? validNames[0] ?? 'scoreboard';

  function activate(name: string) {
    tabs.forEach(t => {
      const on = t.dataset.tab === name;
      t.classList.toggle('active', on);
      t.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    panels.forEach(p => { p.hidden = p.dataset.panel !== name; });
    const activeTab = tabs.find(t => t.dataset.tab === name);
    if (activeTab) activeTab.focus();
  }

  function go(name: string, push: boolean) {
    const target = validNames.includes(name) ? name : defaultName;
    withViewTransition(() => activate(target));
    if (push) history.replaceState(null, '', '#' + target);
  }

  const initial = location.hash.slice(1);
  activate(validNames.includes(initial) ? initial : defaultName);

  tabs.forEach(t => t.addEventListener('click', () => go(t.dataset.tab!, true)));
  window.addEventListener('hashchange', () => go(location.hash.slice(1) || defaultName, false));

  if (tabList) {
    tabList.addEventListener('keydown', (e: KeyboardEvent) => {
      const idx = tabs.findIndex(t => t === document.activeElement);
      if (idx === -1) return;
      let next: number | undefined;
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        e.preventDefault();
        next = (idx + 1) % tabs.length;
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        e.preventDefault();
        next = (idx - 1 + tabs.length) % tabs.length;
      } else if (e.key === 'Home') {
        e.preventDefault();
        next = 0;
      } else if (e.key === 'End') {
        e.preventDefault();
        next = tabs.length - 1;
      }
      if (next !== undefined) {
        tabs[next].focus();
        go(tabs[next].dataset.tab!, true);
      }
    });
  }
}