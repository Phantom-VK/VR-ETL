const API_BASE = 'http://localhost:8000';
const runBtn = document.getElementById('runBtn');
const statusEl = document.getElementById('status');
const thinkingEl = document.getElementById('thinking');
const answerEl = document.getElementById('answer');

function setStatus(msg) { statusEl.textContent = msg; }

async function streamAnswer() {
  try {
    runBtn.disabled = true;
    setStatus('Running ...');
    thinkingEl.textContent = '...';
    answerEl.textContent = '';

    const url = `${API_BASE}/chat`;
    const payload = {
      query: document.getElementById('question').value,
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
          thinkingEl.textContent = evt.thinking || '';
          setStatus('Streaming answer ...');
        } else if (evt.type === 'reason') {
          thinkingEl.textContent += evt.text;
        } else if (evt.type === 'answer') {
          answerEl.textContent += evt.text;
        } else if (evt.type === 'metadata') {
          thinkingEl.textContent += `\n[meta] ${JSON.stringify(evt.metadata)}`;
        } else if (evt.type === 'token') {
          // backward compatibility
          answerEl.textContent += evt.text;
        } else if (evt.type === 'done') {
          setStatus('Done');
        }
      }
    }
    if (buffer.trim()) {
      try {
        const evt = JSON.parse(buffer);
        if (evt.type === 'token') answerEl.textContent += evt.text;
        if (evt.type === 'done') setStatus('Done');
      } catch (e) {}
    }
    if (statusEl.textContent.startsWith('Running')) setStatus('Done');
  } catch (err) {
    console.error(err);
    setStatus('Error: ' + err.message);
  } finally {
    runBtn.disabled = false;
  }
}

runBtn.addEventListener('click', streamAnswer);
