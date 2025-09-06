document.addEventListener('DOMContentLoaded', () => {
  const video = document.getElementById('introVideo');
  const skipBtn = document.getElementById('skipBtn');
  let navigated = false;

  function goToOrb() {
    if (navigated) return;
    navigated = true;
    const next = new URL('voiceOrb.html', location.href).href;
    location.href = next;
  }

  async function ensureAudioContext() {
    try {
      const ac = new (window.AudioContext || window.webkitAudioContext)();
      if (ac.state === 'suspended') await ac.resume();
      // keep a reference to avoid immediate GC in some browsers (no-op)
      window.__introAudioCtx = ac;
      console.log('AudioContext resumed (intro)');
    } catch (e) {
      console.warn('AudioContext resume failed', e);
    }
  }

  // click the video to unmute / resume audio (keeps styles unchanged)
  if (video) {
    video.addEventListener('click', async () => {
      await ensureAudioContext();
      if (video.muted) {
        video.muted = false;
        video.volume = 1;
        video.play().catch(() => {});
      } else {
        // toggle mute if user clicks again
        video.muted = true;
      }
    });

    // when video ends, navigate to orb page
    video.addEventListener('ended', () => goToOrb());
  }

  // skip button already exists in markup; wire it to navigate
  if (skipBtn) skipBtn.addEventListener('click', () => goToOrb());

  // allow embedded parent to instruct skipping
  window.addEventListener('message', (ev) => {
    try {
      const d = ev.data;
      if (!d || typeof d.type !== 'string') return;
      if (d.type === 'intro-skip' || d.type === 'intro-ended' || d.type === 'intro-transition') {
        goToOrb();
      }
    } catch (e) { /* ignore malformed messages */ }
  });

  // Optional: on first user gesture anywhere resume audio to reduce play blocking
  function onFirstGesture() {
    ensureAudioContext();
    document.removeEventListener('click', onFirstGesture);
    document.removeEventListener('keydown', onFirstGesture);
    document.removeEventListener('touchstart', onFirstGesture);
  }
  document.addEventListener('click', onFirstGesture, { once: true });
  document.addEventListener('keydown', onFirstGesture, { once: true });
  document.addEventListener('touchstart', onFirstGesture, { once: true });
});
