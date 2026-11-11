/* Classic-script spinner controller. Scoped to [data-cc-spinner] roots. */
(function (global) {
  'use strict';

  var FALLBACK_GLYPH = '✻';

  function readWords() {
    var data = global.document.getElementById('cc-spinner-data');
    if (!data) return [];
    try {
      var words = JSON.parse(data.textContent || '[]');
      return Array.isArray(words) ? words.filter(function (word) {
        return typeof word === 'string' && word.length > 0;
      }) : [];
    } catch (error) {
      return [];
    }
  }

  function randomWord(words) {
    if (!words.length) return FALLBACK_GLYPH;
    return words[Math.floor(Math.random() * words.length)];
  }

  function initRoot(root) {
    if (!root || root.getAttribute('data-cc-spinner-ready') === 'true') return;
    root.setAttribute('data-cc-spinner-ready', 'true');
    root.setAttribute('data-paused', 'false');

    var words = readWords();
    var paused = false;
    var wordNode = root.querySelector('[data-spinner-word]');
    var pauseButton = root.querySelector('[data-spinner-pause]');
    var nextButton = root.querySelector('[data-spinner-next]');
    var downloadButton = root.querySelector('[data-spinner-download]');
    var glyph = root.querySelector('[data-spinner-glyph]');

    if (glyph) {
      glyph.classList.add('cc-spinner-glyph');
      glyph.setAttribute('aria-hidden', 'true');
    }
    if (wordNode) wordNode.textContent = randomWord(words);

    function updatePause() {
      root.setAttribute('data-paused', paused ? 'true' : 'false');
      if (pauseButton) {
        pauseButton.setAttribute('aria-pressed', paused ? 'true' : 'false');
        var label = pauseButton.getAttribute(paused ? 'data-label-resume' : 'data-label-pause');
        if (label) pauseButton.textContent = label;
      }
    }

    if (nextButton) {
      nextButton.addEventListener('click', function () {
        if (wordNode) wordNode.textContent = randomWord(words);
      });
    }

    if (pauseButton) {
      pauseButton.addEventListener('click', function () {
        paused = !paused;
        updatePause();
      });
    }

    if (downloadButton) {
      downloadButton.addEventListener('click', function () {
        var blob = new global.Blob([words.join('\n') + '\n'], { type: 'text/plain;charset=utf-8' });
        var url = global.URL.createObjectURL(blob);
        var link = global.document.createElement('a');
        link.href = url;
        link.download = 'claude-code-spinner-verbs-2.1.322.txt';
        link.hidden = true;
        global.document.body.appendChild(link);
        link.click();
        if (link.parentNode) link.parentNode.removeChild(link);
        global.setTimeout(function () { global.URL.revokeObjectURL(url); }, 0);
      });
    }

    updatePause();
  }

  function initAll() {
    var roots = global.document.querySelectorAll('[data-cc-spinner]');
    Array.prototype.forEach.call(roots, initRoot);
  }

  function mount(root) {
    initRoot(root);
  }

  if (global.document) {
    if (global.document.readyState === 'loading') {
      global.document.addEventListener('DOMContentLoaded', initAll, { once: true });
    } else {
      initAll();
    }
  }

  global.CCSpinner = { mount: mount };
}(typeof globalThis !== 'undefined' ? globalThis : window));
