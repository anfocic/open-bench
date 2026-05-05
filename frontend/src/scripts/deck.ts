/**
 * Single-section slide deck. Mounts on any page whose pathname matches the
 * supplied prefix and that contains the expected DOM:
 *
 *   <nav class="deck-toc"> <a data-toc="..."> ... </nav>
 *   <main class="deck"> <section data-section="..."> ... </section> ... </main>
 *
 * Wires:
 *   - wheel / arrow / page / space / home / end key navigation
 *   - touch swipe (vertical or horizontal)
 *   - TOC link clicks + hashchange
 *   - View Transition API for the push animation between sections
 *   - body scroll lock via .deck-on on <html>
 *   - cleanup on astro:before-preparation so the next route is unaffected
 */
let cleanup: (() => void) | null = null;

function withViewTransition(fn: () => void) {
  const doc = document as any;
  if (doc.startViewTransition) doc.startViewTransition(fn);
  else fn();
}

export function setupDeck() {
  cleanup?.();
  cleanup = null;

  const tocLinks = [...document.querySelectorAll<HTMLAnchorElement>('.deck-toc a[data-toc]')];
  const sections = [...document.querySelectorAll<HTMLElement>('.deck-section[data-section]')];
  const progress = document.querySelector<HTMLElement>('[data-progress-num]');
  if (!tocLinks.length || !sections.length) {
    document.documentElement.classList.remove('deck-on');
    return;
  }
  document.documentElement.classList.add('deck-on');

  let currentIdx = 0;
  const initialHash = location.hash.slice(1);
  const initialIdx = sections.findIndex(s => s.dataset.section === initialHash);
  if (initialIdx > 0) {
    sections[0].removeAttribute('data-active');
    sections[0].setAttribute('aria-hidden', 'true');
    sections[initialIdx].setAttribute('data-active', 'true');
    sections[initialIdx].setAttribute('aria-hidden', 'false');
    currentIdx = initialIdx;
  }

  function setActive(idx: number) {
    const id = sections[idx].dataset.section!;
    tocLinks.forEach(l => {
      const on = l.dataset.toc === id;
      l.classList.toggle('active', on);
      if (on) l.setAttribute('aria-current', 'true');
      else l.removeAttribute('aria-current');
    });
    if (progress) progress.textContent = String(idx + 1);
    if (location.hash.slice(1) !== id) {
      history.replaceState(null, '', '#' + id);
    }
  }

  setActive(currentIdx);

  let busy = false;

  function goTo(nextIdx: number) {
    if (busy) return;
    if (nextIdx < 0 || nextIdx >= sections.length || nextIdx === currentIdx) return;
    const back = nextIdx < currentIdx;
    busy = true;
    document.documentElement.classList.toggle('deck-back', back);

    const apply = () => {
      sections[currentIdx].removeAttribute('data-active');
      sections[currentIdx].setAttribute('aria-hidden', 'true');
      sections[nextIdx].setAttribute('data-active', 'true');
      sections[nextIdx].setAttribute('aria-hidden', 'false');
      const inner = sections[nextIdx].querySelector<HTMLElement>('.deck-inner');
      if (inner) inner.scrollTop = 0;
      currentIdx = nextIdx;
      setActive(nextIdx);
    };

    const doc = document as any;
    if (doc.startViewTransition) {
      const t = doc.startViewTransition(apply);
      t.finished.finally(() => { busy = false; });
    } else {
      apply();
      setTimeout(() => { busy = false; }, 50);
    }
  }

  let wheelLock = 0;
  function onWheel(e: WheelEvent) {
    const inner = sections[currentIdx].querySelector<HTMLElement>('.deck-inner');
    if (inner && inner.scrollHeight > inner.clientHeight) {
      const atTop = inner.scrollTop <= 0;
      const atBottom = inner.scrollTop + inner.clientHeight >= inner.scrollHeight - 1;
      if (e.deltaY > 0 && !atBottom) return;
      if (e.deltaY < 0 && !atTop) return;
    }
    e.preventDefault();
    const now = Date.now();
    if (now - wheelLock < 700) return;
    if (Math.abs(e.deltaY) < 8) return;
    wheelLock = now;
    goTo(currentIdx + (e.deltaY > 0 ? 1 : -1));
  }
  window.addEventListener('wheel', onWheel, { passive: false });

  function onKey(e: KeyboardEvent) {
    if (e.target && (e.target as HTMLElement).matches('input, textarea, [contenteditable]')) return;
    if (e.key === 'ArrowDown' || e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === ' ') {
      e.preventDefault();
      goTo(currentIdx + 1);
    } else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft' || e.key === 'PageUp') {
      e.preventDefault();
      goTo(currentIdx - 1);
    } else if (e.key === 'Home') {
      e.preventDefault();
      goTo(0);
    } else if (e.key === 'End') {
      e.preventDefault();
      goTo(sections.length - 1);
    }
  }
  window.addEventListener('keydown', onKey);

  let touchY: number | null = null;
  let touchX: number | null = null;
  function onTouchStart(e: TouchEvent) {
    const t = e.touches[0];
    touchY = t.clientY;
    touchX = t.clientX;
  }
  function onTouchEnd(e: TouchEvent) {
    if (touchY === null || touchX === null) return;
    const t = e.changedTouches[0];
    const dy = t.clientY - touchY;
    const dx = t.clientX - touchX;
    touchY = touchX = null;
    const adx = Math.abs(dx);
    const ady = Math.abs(dy);
    if (Math.max(adx, ady) < 40) return;
    if (ady > adx) {
      goTo(currentIdx + (dy < 0 ? 1 : -1));
    } else {
      goTo(currentIdx + (dx < 0 ? 1 : -1));
    }
  }
  window.addEventListener('touchstart', onTouchStart, { passive: true });
  window.addEventListener('touchend', onTouchEnd, { passive: true });

  function onTocClick(this: HTMLAnchorElement, e: Event) {
    e.preventDefault();
    const id = this.dataset.toc!;
    const idx = sections.findIndex(s => s.dataset.section === id);
    if (idx >= 0) goTo(idx);
  }
  tocLinks.forEach(a => a.addEventListener('click', onTocClick));

  function onHash() {
    const id = location.hash.slice(1);
    const idx = sections.findIndex(s => s.dataset.section === id);
    if (idx >= 0 && idx !== currentIdx) goTo(idx);
  }
  window.addEventListener('hashchange', onHash);

  cleanup = () => {
    window.removeEventListener('wheel', onWheel);
    window.removeEventListener('keydown', onKey);
    window.removeEventListener('touchstart', onTouchStart);
    window.removeEventListener('touchend', onTouchEnd);
    window.removeEventListener('hashchange', onHash);
    tocLinks.forEach(a => a.removeEventListener('click', onTocClick));
    document.documentElement.classList.remove('deck-on', 'deck-back');
  };
}

export function teardownDeck() {
  cleanup?.();
  cleanup = null;
}
