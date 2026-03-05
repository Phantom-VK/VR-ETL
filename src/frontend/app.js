
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
const chatHistory = []; // [{role:'user'|'assistant', content:str}]

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
  // state: 'pending' | 'active' | 'done'
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

// Sync range ↔ number inputs
function syncInputs(rangeEl, numEl) {
  rangeEl.addEventListener('input', () => { numEl.value = rangeEl.value; });
  numEl.addEventListener('input', ()  => { rangeEl.value = numEl.value; });
}
syncInputs(searchTempRange, searchTemp);
syncInputs(answerTempRange, answerTemp);

// Mode toggle
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
 * Returns refs to the live text elements so we can append to them.
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

  return { reasonText, answerText, answerLabel };
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

  // Add user message
  addUserMessage(question);
  chatHistory.push({ role: 'user', content: question });
  questionInput.value = '';

  // Build streaming bubble
  const { reasonText, answerText, answerLabel } = addAssistantStreamBubble();

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
      // Future: include history for multi-turn
      // history: chatHistory.slice(0, -1),
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
      buffer = lines.pop(); // keep incomplete line

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
          setStepState('nodes', 'done');
          setStepState('reason', 'active');
          const expr = evt.args?.expression || '';
          const res  = evt.result || '';
          setTicker(`Math tool: ${expr} → ${res}`, 'working');
          fullReason += `\n[math] ${expr} = ${res}\n`;
          reasonText.textContent = fullReason;
        }

        // ── reasoning stream ──
        else if (evt.type === 'reason') {
          setStepState('nodes', 'done');
          setStepState('reason', 'active');
          setTicker('Reasoning…', 'working');
          fullReason += evt.text;
          reasonText.textContent = fullReason;
          scrollToBottom();
        }

        // ── answer stream ──
        else if (evt.type === 'answer') {
          setStepState('reason', 'done');
          setStepState('answer', 'active');
          setTicker('Writing answer…', 'working');
          // Show answer section on first chunk
          if (answerText.style.display === 'none') {
            reasonText.classList.remove('typing-cursor');
            answerLabel.style.display = 'flex';
            answerText.style.display  = 'block';
          }
          fullAnswer += evt.text;
          answerText.textContent = fullAnswer;
          scrollToBottom();
        }

        // ── done ──
        else if (evt.type === 'done') {
          setStepState('answer', 'done');
          answerText.classList.remove('typing-cursor');
          // If no answer tokens arrived but we have reasoning, surface reasoning as answer fallback
          if (!fullAnswer && fullReason) {
            answerLabel.style.display = 'flex';
            answerText.style.display  = 'block';
            answerText.textContent = fullReason;
          }
          setTicker('Done ✓', 'active');
          // Save to history
          chatHistory.push({ role: 'assistant', content: fullAnswer || fullReason });
        }
      }
    }

    // Flush remaining buffer
    if (buffer.trim()) {
      try {
        const evt = JSON.parse(buffer);
        if (evt.type === 'reason') { fullReason += evt.text; reasonText.textContent = fullReason; }
        if (evt.type === 'answer') { fullAnswer += evt.text; answerText.textContent = fullAnswer; }
        if (evt.type === 'done')   { 
          if (!fullAnswer && fullReason) {
            answerLabel.style.display = 'flex';
            answerText.style.display  = 'block';
            answerText.textContent = fullReason;
          }
          setTicker('Done ✓', 'active'); 
        }
      } catch { /* ignore */ }
    }

    // Cleanup cursors
    reasonText.classList.remove('typing-cursor');
    answerText.classList.remove('typing-cursor');

    if (!fullAnswer && !fullReason) {
      setTicker('No response received.', 'error');
    }

  } catch (err) {
    console.error('[VR-ETL]', err);
    setTicker('Error: ' + err.message, 'error');
    tickerDot.className = 'ticker-dot error';

    // Show error inline
    reasonText.classList.remove('typing-cursor');
    reasonText.textContent = '⚠️ ' + err.message;
    reasonText.style.color = 'var(--red)';

  } finally {
    runBtn.disabled = false;
    // Auto-reset ticker after 6 seconds
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
  // Shift+Enter = newline (default behaviour — no override needed)
});

// ── Init ────────────────────────────────────────────────
initTickerChips();
