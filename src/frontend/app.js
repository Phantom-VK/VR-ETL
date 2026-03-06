const API_BASE = 'http://localhost:8000';

// ─── DOM refs ────────────────────────────────────────────
const runBtn          = document.getElementById('runBtn');
const chatLog         = document.getElementById('chatLog');
const questionInput   = document.getElementById('question');
const tickerDot       = document.getElementById('tickerDot');
const tickerText      = document.getElementById('tickerText');
const tickerSteps     = document.getElementById('tickerSteps');
const settingsToggle  = document.getElementById('settingsToggle');
const settingsDropdown= document.getElementById('settingsDropdown');
const searchTemp      = document.getElementById('searchTemp');
const answerTemp      = document.getElementById('answerTemp');
const searchTempRange = document.getElementById('searchTempRange');
const answerTempRange = document.getElementById('answerTempRange');

// ─── Pipeline steps shown in the ticker ──────────────────
const PIPELINE_STEPS = [
  { id: 'search',   label: '🔍 Search' },
  { id: 'nodes',    label: '🌲 Nodes'  },
  { id: 'reason',   label: '🧠 Reason' },
  { id: 'answer',   label: '✍️ Answer' },
];

// ─── Chat history (for future multi-turn) ────────────────
const chatHistory = [];

// ═══════════════════════════════════════════════════════════
// RENDER UTILITIES  (Markdown + LaTeX + Mermaid)
// ═══════════════════════════════════════════════════════════

/**
 * Renders text that may contain:
 *  - ```mermaid ... ``` blocks   → rendered as Mermaid diagrams
 *  - \[ ... \]  or  \( ... \)   → rendered by KaTeX (display / inline)
 *  - **bold**, *italic*, etc.   → rendered by marked.js
 *  - <page=N> citations         → styled chip
 *
 * Returns an HTML string safe to set as innerHTML.
 */
function renderRichText(raw) {
  if (!raw) return '';

  // 1. Protect mermaid blocks — swap them for placeholders
  const mermaidBlocks = [];
  let text = raw.replace(/```mermaid\s*([\s\S]*?)```/g, (_, code) => {
    const idx = mermaidBlocks.length;
    mermaidBlocks.push(code.trim());
    return `%%MERMAID_BLOCK_${idx}%%`;
  });

  // 2. Protect display LaTeX  \[ ... \]
  const latexDisplay = [];
  text = text.replace(/\\\[([\s\S]*?)\\\]/g, (_, tex) => {
    const idx = latexDisplay.length;
    latexDisplay.push(tex.trim());
    return `%%LATEX_DISPLAY_${idx}%%`;
  });

  // 3. Protect inline LaTeX  \( ... \)
  const latexInline = [];
  text = text.replace(/\\\(([\s\S]*?)\\\)/g, (_, tex) => {
    const idx = latexInline.length;
    latexInline.push(tex.trim());
    return `%%LATEX_INLINE_${idx}%%`;
  });

  // 4. Style <page=N> citation tags
  text = text.replace(/<page=(\d+)>/g,
    '<span class="cite-chip">p.$1</span>');

  // 5. Run marked.js for Markdown → HTML
  let html = (window.marked && window.marked.parse)
    ? window.marked.parse(text, { breaks: true, gfm: true })
    : text.replace(/\n/g, '<br>');

  // 6. Restore display LaTeX placeholders
  latexDisplay.forEach((tex, idx) => {
    let rendered = tex;
    if (window.katex) {
      try {
        rendered = katex.renderToString(tex, { displayMode: true, throwOnError: false });
      } catch (e) { rendered = `<code>${tex}</code>`; }
    }
    html = html.replace(`%%LATEX_DISPLAY_${idx}%%`, rendered);
  });

  // 7. Restore inline LaTeX placeholders
  latexInline.forEach((tex, idx) => {
    let rendered = tex;
    if (window.katex) {
      try {
        rendered = katex.renderToString(tex, { displayMode: false, throwOnError: false });
      } catch (e) { rendered = `<code>${tex}</code>`; }
    }
    html = html.replace(`%%LATEX_INLINE_${idx}%%`, rendered);
  });

  // 8. Restore Mermaid placeholders as special divs
  mermaidBlocks.forEach((code, idx) => {
    const placeholder = `<div class="mermaid-pending" data-code="${escapeAttr(code)}"></div>`;
    html = html.replace(`%%MERMAID_BLOCK_${idx}%%`, placeholder);
  });

  return html;
}

function escapeAttr(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

/**
 * After setting innerHTML on a container, call this to
 * actually render any .mermaid-pending divs inside it.
 */
function hydrateMermaid(container) {
  if (!window.mermaid) return;
  const pending = container.querySelectorAll('.mermaid-pending');
  if (!pending.length) return;

  pending.forEach(el => {
    const code = el.getAttribute('data-code') || '';
    const wrapper = document.createElement('div');
    wrapper.className = 'mermaid-diagram';

    const mermaidDiv = document.createElement('div');
    mermaidDiv.className = 'mermaid';
    mermaidDiv.textContent = code;

    wrapper.appendChild(mermaidDiv);
    el.replaceWith(wrapper);

    try {
      window.mermaid.initialize({ startOnLoad: false, theme: 'dark' });
      window.mermaid.init(undefined, mermaidDiv);
    } catch (e) {
      console.error('Mermaid render error:', e);
      mermaidDiv.textContent = '[Diagram render error: ' + e.message + ']';
    }
  });
}

// ═══════════════════════════════════════════════════════════
// STATUS TICKER
// ═══════════════════════════════════════════════════════════

function initTickerChips() {
  tickerSteps.innerHTML = '';
  PIPELINE_STEPS.forEach(step => {
    const chip = document.createElement('div');
    chip.className = 'step-chip pending';
    chip.id = `chip-${step.id}`;
    chip.textContent = step.label;
    tickerSteps.appendChild(chip);
  });
}

function setStepState(stepId, state) {
  const chip = document.getElementById(`chip-${stepId}`);
  if (!chip) return;
  chip.className = `step-chip ${state}`;
}

function setTicker(msg, dotState = 'idle') {
  tickerText.textContent = msg;
  tickerDot.className = 'ticker-dot';
  if (dotState === 'working') tickerDot.classList.add('working');
  else if (dotState === 'active') tickerDot.classList.add('active');
  else if (dotState === 'error') tickerDot.classList.add('error');
}

function resetTicker() {
  setTicker('Ready — awaiting your query');
  initTickerChips();
}


// ═══════════════════════════════════════════════════════════
// SETTINGS DROPDOWN
// ═══════════════════════════════════════════════════════════

settingsToggle.addEventListener('click', (e) => {
  e.stopPropagation();
  settingsDropdown.classList.toggle('open');
});
document.addEventListener('click', () => settingsDropdown.classList.remove('open'));
settingsDropdown.addEventListener('click', e => e.stopPropagation());

function syncInputs(rangeEl, numEl) {
  rangeEl.addEventListener('input', () => { numEl.value = rangeEl.value; });
  numEl.addEventListener('input', ()  => { rangeEl.value = numEl.value; });
}
syncInputs(searchTempRange, searchTemp);
syncInputs(answerTempRange, answerTemp);

document.querySelectorAll('.sd-toggle').forEach(btn => {
  btn.addEventListener('click', () => {
    if (btn.title?.includes('soon')) return;
    document.querySelectorAll('.sd-toggle').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
  });
});


// ═══════════════════════════════════════════════════════════
// AUTO-GROW TEXTAREA
// ═══════════════════════════════════════════════════════════

questionInput.addEventListener('input', () => {
  questionInput.style.height = 'auto';
  questionInput.style.height = Math.min(questionInput.scrollHeight, 160) + 'px';
});


// ═══════════════════════════════════════════════════════════
// MESSAGE BUILDERS
// ═══════════════════════════════════════════════════════════

function scrollToBottom() {
  chatLog.scrollTop = chatLog.scrollHeight;
}

function addUserMessage(text) {
  const msg = document.createElement('div');
  msg.className = 'msg user';

  const avatar = document.createElement('div');
  avatar.className = 'avatar user-avatar';
  avatar.textContent = 'U';

  const bubble = document.createElement('div');
  bubble.className = 'bubble';

  const meta = document.createElement('div');
  meta.className = 'bubble-meta';
  meta.textContent = 'You';

  const content = document.createElement('div');
  content.textContent = text;

  bubble.appendChild(meta);
  bubble.appendChild(content);
  msg.appendChild(avatar);
  msg.appendChild(bubble);
  chatLog.appendChild(msg);
  scrollToBottom();
}

/**
 * Creates the streaming AI response bubble.
 * Returns refs + a flush function to do final rich render.
 */
function addAssistantStreamBubble() {
  const msg = document.createElement('div');
  msg.className = 'msg assistant';

  const avatar = document.createElement('div');
  avatar.className = 'avatar ai-avatar';
  avatar.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>`;

  const bubble = document.createElement('div');
  bubble.className = 'bubble';

  const meta = document.createElement('div');
  meta.className = 'bubble-meta';
  meta.textContent = 'VR-ETL Agent';

  // Reasoning section
  const reasonLabel = document.createElement('div');
  reasonLabel.className = 'section-label reason';
  reasonLabel.innerHTML = `<span class="dot"></span> Reasoning`;

  const reasonText = document.createElement('div');
  reasonText.className = 'reason-text typing-cursor';

  // Answer section
  const answerLabel = document.createElement('div');
  answerLabel.className = 'section-label answer';
  answerLabel.innerHTML = `<span class="dot"></span> Answer`;
  answerLabel.style.display = 'none';

  const answerText = document.createElement('div');
  answerText.className = 'answer-text typing-cursor';
  answerText.style.display = 'none';

  bubble.appendChild(meta);
  bubble.appendChild(reasonLabel);
  bubble.appendChild(reasonText);
  bubble.appendChild(answerLabel);
  bubble.appendChild(answerText);

  msg.appendChild(avatar);
  msg.appendChild(bubble);
  chatLog.appendChild(msg);
  scrollToBottom();

  /**
   * During streaming we use plain text for speed.
   * Call flushRich() once streaming is complete to upgrade
   * both sections to full markdown + LaTeX + mermaid.
   */
  function flushRich(fullReason, fullAnswer) {
    // Render reasoning
    reasonText.classList.remove('typing-cursor');
    reasonText.innerHTML = renderRichText(fullReason);
    hydrateMermaid(reasonText);

    // Render answer
    answerText.classList.remove('typing-cursor');
    if (fullAnswer) {
      answerText.innerHTML = renderRichText(fullAnswer);
      hydrateMermaid(answerText);
    }
    scrollToBottom();
  }

  return { reasonText, answerText, answerLabel, flushRich };
}


// ═══════════════════════════════════════════════════════════
// MAIN STREAM HANDLER
// ═══════════════════════════════════════════════════════════

async function streamAnswer() {
  const question = questionInput.value.trim();
  if (!question) return;

  runBtn.disabled = true;
  questionInput.style.height = 'auto';
  initTickerChips();
  setTicker('Sending query to agent…', 'working');

  addUserMessage(question);
  chatHistory.push({ role: 'user', content: question });
  questionInput.value = '';

  const { reasonText, answerText, answerLabel, flushRich } = addAssistantStreamBubble();

  // Show retrieval state until the model starts reasoning
  let hasStartedReasoning = false;
  reasonText.textContent = 'Searching document…';
  reasonText.classList.add('placeholder');

  let fullReason = '';
  let fullAnswer = '';

  try {
    setStepState('search', 'active');
    setTicker('Searching document index…', 'working');

    const payload = {
      query: question,
      search_temperature: parseFloat(searchTemp.value) || 0.1,
      answer_temperature:  parseFloat(answerTemp.value) || 0.2,
      enable_citations: false,
      use_math_tool: true,
    };

    const res = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/x-ndjson',
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok || !res.body) {
      throw new Error(await res.text());
    }

    const reader  = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.trim()) continue;

        let evt;
        try { evt = JSON.parse(line); }
        catch { continue; }

        // ── meta: nodes retrieved ──
        if (evt.type === 'meta') {
          const count = (evt.node_list || []).length;
          setStepState('search', 'done');
          setStepState('nodes', 'active');
          setTicker(`Feeding ${count} node${count !== 1 ? 's' : ''} to LLM…`, 'working');
        }

        // ── tool execution ──
        else if (evt.type === 'tool') {
          if (!hasStartedReasoning) {
            hasStartedReasoning = true;
            reasonText.classList.remove('placeholder');
            reasonText.textContent = '';
          }
          setStepState('nodes', 'done');
          setStepState('reason', 'active');
          const expr = evt.args?.expression || '';
          const result = evt.result || '';
          setTicker(`Math tool: ${expr} → ${result}`, 'working');
          // Accumulate as plain text during stream; will be richly rendered on done
          fullReason += `\n**[math]** \`${expr}\` = \`${result}\`\n`;
          reasonText.textContent = fullReason;  // plain text during stream
        }

        // ── reasoning stream ──
        else if (evt.type === 'reason') {
          if (!hasStartedReasoning) {
            hasStartedReasoning = true;
            reasonText.classList.remove('placeholder');
            reasonText.textContent = '';
          }
          setStepState('nodes', 'done');
          setStepState('reason', 'active');
          setTicker('Reasoning…', 'working');
          fullReason += evt.text;
          reasonText.textContent = fullReason;  // plain text during stream
          scrollToBottom();
        }

        // ── answer stream ──
        else if (evt.type === 'answer') {
          if (!hasStartedReasoning) {
            hasStartedReasoning = true;
            reasonText.classList.remove('placeholder');
            reasonText.textContent = '';
          }
          setStepState('reason', 'done');
          setStepState('answer', 'active');
          setTicker('Writing answer…', 'working');
          if (answerText.style.display === 'none') {
            reasonText.classList.remove('typing-cursor');
            answerLabel.style.display = 'flex';
            answerText.style.display  = 'block';
          }
          fullAnswer += evt.text;
          answerText.textContent = fullAnswer;  // plain text during stream
          scrollToBottom();
        }

        // ── done ──
        else if (evt.type === 'done') {
          setStepState('answer', 'done');
          answerText.classList.remove('typing-cursor');
          reasonText.classList.remove('placeholder');

          // If no answer tokens but we have reasoning, surface reasoning as answer fallback
          if (!fullAnswer && fullReason) {
            answerLabel.style.display = 'flex';
            answerText.style.display  = 'block';
          }

          // ★ KEY: now upgrade both sections to full rich render
          flushRich(fullReason, fullAnswer || fullReason);

          setTicker('Done ✓', 'active');
          chatHistory.push({ role: 'assistant', content: fullAnswer || fullReason });
        }
      }
    }

    // Flush remaining buffer
    if (buffer.trim()) {
      try {
        const evt = JSON.parse(buffer);
        if (evt.type === 'reason') { fullReason += evt.text; }
        if (evt.type === 'answer') { fullAnswer += evt.text; }
        if (evt.type === 'done') {
          reasonText.classList.remove('placeholder');
          if (!fullAnswer && fullReason) {
            answerLabel.style.display = 'flex';
            answerText.style.display  = 'block';
          }
          flushRich(fullReason, fullAnswer || fullReason);
          setTicker('Done ✓', 'active');
        }
      } catch { /* ignore */ }
    }

    // Safety: if stream ended without 'done' event, still do rich render
    if (fullReason || fullAnswer) {
      reasonText.classList.remove('placeholder');
      flushRich(fullReason, fullAnswer);
    }

    if (!fullAnswer && !fullReason) {
      setTicker('No response received.', 'error');
    }

  } catch (err) {
    console.error('[VR-ETL]', err);
    setTicker('Error: ' + err.message, 'error');
    tickerDot.className = 'ticker-dot error';

    reasonText.classList.remove('typing-cursor', 'placeholder');
    reasonText.textContent = '⚠️ ' + err.message;
    reasonText.style.color = 'var(--red)';

  } finally {
    runBtn.disabled = false;
    setTimeout(() => {
      if (tickerText.textContent.startsWith('Done') || tickerText.textContent.startsWith('Error')) {
        resetTicker();
      }
    }, 6000);
  }
}


// ═══════════════════════════════════════════════════════════
// EVENT BINDINGS
// ═══════════════════════════════════════════════════════════

runBtn.addEventListener('click', streamAnswer);

questionInput.addEventListener('keydown', (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
    e.preventDefault();
    streamAnswer();
  }
});

// ── Init ────────────────────────────────────────────────
initTickerChips();
