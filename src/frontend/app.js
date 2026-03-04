const runBtn = document.getElementById('runBtn');
const statusEl = document.getElementById('status');
const thinkingEl = document.getElementById('thinking');
const nodesEl = document.getElementById('nodes');
const answerEl = document.getElementById('answer');

function setStatus(msg) { statusEl.textContent = msg; }

function renderNodes(nodes) {
  if (!nodes || nodes.length === 0) return '(no nodes)';
  return nodes.map(n => `• ${n.node_id}\tpage: ${n.page_index ?? '-'}\t${n.title ?? ''}`).join('\n');
}

async function streamAnswer() {
  try {
    runBtn.disabled = true;
    setStatus('Running /answer/stream ...');
    thinkingEl.textContent = '...';
    nodesEl.textContent = '...';
    answerEl.textContent = '';

    const body = {
      query: document.getElementById('question').value,
      model: document.getElementById('model').value || null,
      temperature: parseFloat(document.getElementById('temperature').value) || 0,
    };

    const res = await fetch(`${document.getElementById('apiBase').value}/answer/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/x-ndjson'
      },
      body: JSON.stringify(body),
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
          thinkingEl.textContent = evt.thinking || '(no reasoning)';
          nodesEl.textContent = renderNodes(evt.nodes);
          setStatus('Streaming answer ...');
        } else if (evt.type === 'reason') {
          thinkingEl.textContent += evt.text;
        } else if (evt.type === 'answer') {
          answerEl.textContent += evt.text;
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
