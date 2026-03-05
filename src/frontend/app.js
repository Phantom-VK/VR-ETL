const API_BASE = 'http://localhost:8000';

const runBtn = document.getElementById('runBtn');
const statusEl = document.getElementById('status');
const chatLog = document.getElementById('chatLog');
const questionInput = document.getElementById('question');

function setStatus(msg) {
  statusEl.textContent = msg;
}

function addMessage(role, content, opts = {}) {
  const msg = document.createElement('div');
  msg.className = `msg ${role}`;

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = role === 'user' ? 'U' : 'AI';

  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  if (opts.label) {
    const lbl = document.createElement('div');
    lbl.className = 'label';
    lbl.textContent = opts.label;
    bubble.appendChild(lbl);
  }
  const textEl = document.createElement('div');
  textEl.innerText = content;
  bubble.appendChild(textEl);

  msg.appendChild(avatar);
  msg.appendChild(bubble);
  chatLog.appendChild(msg);
  chatLog.scrollTop = chatLog.scrollHeight;
  return { msg, bubble, textEl };
}

function addAssistantStreams() {
  const msg = document.createElement('div');
  msg.className = 'msg assistant';

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = 'AI';

  const bubble = document.createElement('div');
  bubble.className = 'bubble';

  const reasonLabel = document.createElement('div');
  reasonLabel.className = 'label';
  reasonLabel.textContent = 'Reasoning';
  const reasonEl = document.createElement('div');
  reasonEl.className = 'reason';
  reasonEl.innerText = '';

  const answerLabel = document.createElement('div');
  answerLabel.className = 'label';
  answerLabel.textContent = 'Answer';
  const answerEl = document.createElement('div');
  answerEl.className = 'answer';
  answerEl.innerText = '';

  bubble.appendChild(reasonLabel);
  bubble.appendChild(reasonEl);
  bubble.appendChild(answerLabel);
  bubble.appendChild(answerEl);

  msg.appendChild(avatar);
  msg.appendChild(bubble);
  chatLog.appendChild(msg);
  chatLog.scrollTop = chatLog.scrollHeight;
  return { reasonEl, answerEl };
}

async function streamAnswer() {
  try {
    const question = questionInput.value.trim();
    if (!question) return;

    runBtn.disabled = true;
    setStatus('Sending...');

    addMessage('user', question);
    questionInput.value = '';

    const { reasonEl, answerEl } = addAssistantStreams();

    const url = `${API_BASE}/chat`;
    const payload = {
      query: question,
      search_temperature: parseFloat(document.getElementById('searchTemp').value) || 0.1,
      answer_temperature: parseFloat(document.getElementById('answerTemp').value) || 0.2,
      enable_citations: false,
    };

    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/x-ndjson'
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok || !res.body) throw new Error(await res.text());

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let lines = buffer.split('\n');
      buffer = lines.pop();
      for (const line of lines) {
        if (!line.trim()) continue;
        const evt = JSON.parse(line);
        if (evt.type === 'meta') {
          const count = (evt.node_list || []).length;
          setStatus(`Retrieving nodes... (${count})`);
        } else if (evt.type === 'reason') {
          setStatus('Reasoning...');
          reasonEl.textContent += evt.text;
        } else if (evt.type === 'answer') {
          setStatus('Answering...');
          answerEl.textContent += evt.text;
        } else if (evt.type === 'done') {
          setStatus('Done');
        }
      }
    }
    if (buffer.trim()) {
      try {
        const evt = JSON.parse(buffer);
        if (evt.type === 'reason') reasonEl.textContent += evt.text;
        if (evt.type === 'answer') answerEl.textContent += evt.text;
        if (evt.type === 'done') setStatus('Done');
      } catch (e) {}
    }
    if (statusEl.textContent.startsWith('Sending')) setStatus('Done');
  } catch (err) {
    console.error(err);
    setStatus('Error: ' + err.message);
    addMessage('assistant', 'Error: ' + err.message, { label: 'System' });
  } finally {
    runBtn.disabled = false;
  }
}

runBtn.addEventListener('click', streamAnswer);
questionInput.addEventListener('keydown', (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
    streamAnswer();
  }
});
