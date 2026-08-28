(() => {
  'use strict';

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------------- math helpers ---------------- */

  const clamp = (v, min = 0, max = 1) => Math.min(max, Math.max(min, v));
  const lerp = (a, b, t) => a + (b - a) * t;
  const smoothstep = (t) => t * t * (3 - 2 * t);

  // Maps scroll position to a 0-1 progress within [start, end], eased.
  const segmentInOut = (value, start, end) => {
    if (end === start) return value >= end ? 1 : 0;
    const t = clamp((value - start) / (end - start));
    return smoothstep(t);
  };

  /* ---------------- header ---------------- */

  const header = document.querySelector('[data-header]');

  /* ---------------- cinematic scene ---------------- */

  const cinema = document.querySelector('[data-cinema]');
  const world = document.querySelector('[data-world]');

  const layers = {
    bg: document.querySelector('[data-layer="bg"]'),
    botanicalBack: document.querySelector('[data-layer="botanical-back"]'),
    product: document.querySelector('[data-layer="product"]'),
    botanicalFore: document.querySelector('[data-layer="botanical-fore"]'),
    title: document.querySelector('[data-layer="title"]'),
    shade: document.querySelector('[data-layer="shade"]'),
    intro: document.querySelector('[data-layer="intro"]'),
    storyProduct: document.querySelector('[data-layer="story-product"]'),
    storyCollection: document.querySelector('[data-layer="story-collection"]'),
  };

  const planter = document.querySelector('.planter');

  let ticking = false;
  let lastScrollY = -1;

  function updateHeader(scrollY) {
    if (!header) return;
    header.dataset.scrolled = scrollY > 40 ? 'true' : 'false';
  }

  function renderScene(scrollY) {
    if (!cinema) return;

    const cinemaTop = cinema.offsetTop;
    const local = scrollY - cinemaTop; // px scrolled within the cinema section

    // --- Segment 1: Introduction, 0 -> 650px ---
    const introOut = segmentInOut(local, 0, 650);

    if (layers.title) {
      const titleY = lerp(0, -120, introOut);
      const titleScale = lerp(1, 1.08, introOut);
      layers.title.style.transform = `translateY(${titleY}px) scale(${titleScale})`;
    }
    if (layers.intro) {
      layers.intro.style.opacity = String(1 - introOut);
      layers.intro.style.transform = `translateY(${lerp(0, 24, introOut)}px)`;
    }
    if (layers.botanicalBack) {
      layers.botanicalBack.style.transform = `translateY(${lerp(0, -40, introOut)}px)`;
    }

    // --- Segment 2: Product close-up, 560 -> 1620px ---
    const closeUp = segmentInOut(local, 560, 1620);

    if (planter) {
      const scale = lerp(1, 2.35, closeUp);
      const y = lerp(0, -140, closeUp);
      const rotate = lerp(0, 6, closeUp);
      planter.style.transform = `translateY(${y}px) rotate(${rotate}deg) scale(${scale})`;
    }
    if (layers.product) {
      layers.product.style.opacity = String(1 - clamp((closeUp - 0.82) / 0.18));
    }
    if (layers.bg) {
      layers.bg.style.filter = `blur(${lerp(0, 6, closeUp)}px) brightness(${lerp(1, 1.04, closeUp)})`;
    }
    if (layers.botanicalFore) {
      layers.botanicalFore.style.transform = `translateY(${lerp(0, 60, closeUp)}px)`;
      layers.botanicalFore.style.opacity = String(lerp(0.55, 0.15, closeUp));
    }
    if (layers.storyProduct) {
      const revealStart = segmentInOut(local, 900, 1620);
      const fadeOut = segmentInOut(local, 2150, 2500);
      layers.storyProduct.style.opacity = String(clamp(revealStart - fadeOut));
      layers.storyProduct.style.transform = `translateY(${lerp(50, 0, revealStart)}px)`;
      layers.storyProduct.style.pointerEvents = revealStart > 0.4 && fadeOut < 0.5 ? 'auto' : 'none';
    }

    // --- Segment 3: Collections, 2500 -> 3700px ---
    const collectionIn = segmentInOut(local, 2500, 3300);

    if (layers.storyCollection) {
      layers.storyCollection.style.opacity = String(collectionIn);
      layers.storyCollection.style.transform = `translateY(${lerp(60, 0, collectionIn)}px)`;
      layers.storyCollection.style.pointerEvents = collectionIn > 0.5 ? 'auto' : 'none';
    }
    if (layers.shade) {
      layers.shade.style.opacity = String(lerp(0, 1, collectionIn));
    }
  }

  function onScroll() {
    lastScrollY = window.scrollY || window.pageYOffset;
    if (!ticking) {
      ticking = true;
      requestAnimationFrame(() => {
        updateHeader(lastScrollY);
        if (!prefersReducedMotion) renderScene(lastScrollY);
        ticking = false;
      });
    }
  }

  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll);
  onScroll();

  /* ---------------- infinite collection slider ---------------- */

  const sliderRoot = document.querySelector('[data-slider]');
  const track = document.querySelector('[data-slider-track]');
  const prevBtn = document.querySelector('[data-slider-prev]');
  const nextBtn = document.querySelector('[data-slider-next]');

  if (sliderRoot && track && track.children.length > 0) {
    const originalCards = Array.from(track.children);
    const setLength = originalCards.length;

    // Build 3 cloned sets so the visible "middle" set can be scrolled infinitely.
    const buildClone = () =>
      originalCards.map((card) => {
        const clone = card.cloneNode(true);
        clone.setAttribute('aria-hidden', 'true');
        clone.tabIndex = -1;
        return clone;
      });

    const before = buildClone();
    const after = buildClone();
    before.forEach((c) => track.insertBefore(c, track.firstChild));
    after.forEach((c) => track.appendChild(c));

    const allCards = Array.from(track.children);
    const cardStep = () => {
      const card = allCards[setLength];
      const style = getComputedStyle(track);
      const gap = parseFloat(style.gap || style.columnGap || '24');
      return card.getBoundingClientRect().width + gap;
    };

    function normalizeToMiddle() {
      const step = cardStep();
      track.scrollLeft = step * setLength;
    }

    // Position at the middle set on load (after layout settles).
    requestAnimationFrame(() => requestAnimationFrame(normalizeToMiddle));
    window.addEventListener('resize', normalizeToMiddle);

    let normalizeTimer = null;
    track.addEventListener('scroll', () => {
      if (normalizeTimer) clearTimeout(normalizeTimer);
      normalizeTimer = setTimeout(() => {
        const step = cardStep();
        const min = step * setLength * 0.5;
        const max = step * setLength * 1.5;
        if (track.scrollLeft < min || track.scrollLeft > max) {
          normalizeToMiddle();
        }
      }, 120);
    }, { passive: true });

    function scrollByCards(direction) {
      const step = cardStep();
      track.scrollBy({ left: direction * step, behavior: 'smooth' });
    }

    // Note: page is RTL, so "next" visually moves toward the start of the DOM
    // in most RTL scroll implementations; direction is inverted accordingly.
    prevBtn && prevBtn.addEventListener('click', () => scrollByCards(1));
    nextBtn && nextBtn.addEventListener('click', () => scrollByCards(-1));

    allCards.forEach((card) => {
      card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          card.querySelector('a')?.click();
        }
      });
    });
  }
})();
