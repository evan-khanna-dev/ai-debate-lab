const TYPING_SPEED = 20; // ms per character

const topicForm = document.getElementById('topicForm');
const topicInput = document.getElementById('topicInput');
const startBtn = document.getElementById('startBtn');
const welcomeScreen = document.getElementById('welcomeScreen');
const messagesContainer = document.getElementById('messagesContainer');
const messages = document.getElementById('messages');
const debateTopic = document.getElementById('debateTopic');
const judgeSummary = document.getElementById('judgeSummary');
const debateList = document.getElementById('debateList');
const newDebateBtn = document.getElementById('newDebateBtn');
const downloadReportBtn = document.getElementById('downloadReportBtn');
const botANameInput = document.getElementById('botAName');
const botBNameInput = document.getElementById('botBName');
const botARoleInput = document.getElementById('botARole');
const botBRoleInput = document.getElementById('botBRole');

let currentRunId = null;
const messageQueue = [];
let isDisplayingBlock = false;
let loadingRunId = null;
let loadAbortController = null;
let inProgressTopic = null;

function getRoleLabel(role) {
  const labels = { pro: 'PRO', con: 'CON', moderator: 'Moderator', judge: 'Judge' };
  return labels[role] || role;
}

function getAvatarLetter(name) {
  return (name || '?')[0].toUpperCase();
}

function animateTyping(element, text, onComplete) {
  element.textContent = '';
  let i = 0;
  const cursor = document.createElement('span');
  cursor.className = 'typing-cursor';
  element.appendChild(cursor);

  function type() {
    if (i < text.length) {
      const char = text[i];
      element.insertBefore(document.createTextNode(char), cursor);
      i++;
      if (i % 5 === 0) scrollToLatestMessage();
      setTimeout(type, TYPING_SPEED);
    } else {
      cursor.remove();
      scrollToLatestMessage();
      if (onComplete) onComplete();
    }
  }
  type();
}

function addMessage(speaker, role, text, animate = true, onComplete, roleLabelOverride) {
  const div = document.createElement('div');
  div.className = `message ${role} message-block`;

  const baseLabel = getRoleLabel(role);
  const roleLabel = (roleLabelOverride != null && roleLabelOverride !== baseLabel)
    ? baseLabel + " (" + roleLabelOverride + ")"
    : (roleLabelOverride != null ? roleLabelOverride : baseLabel);
  div.innerHTML = `
    <div class="message-avatar">${getAvatarLetter(speaker)}</div>
    <div class="message-body">
      <div class="message-header">
        <span class="message-speaker">${escapeHtml(speaker)}</span>
        <span class="message-role">${escapeHtml(roleLabel)}</span>
      </div>
      <div class="message-text"></div>
    </div>
  `;

  const textEl = div.querySelector('.message-text');
  messages.appendChild(div);
  scrollToLatestMessage();

  if (animate) {
    animateTyping(textEl, text, () => {
      textEl.innerHTML = formatMessageText(text);
      if (onComplete) onComplete();
    });
  } else {
    textEl.innerHTML = formatMessageText(text);
    if (onComplete) onComplete();
  }
}

function scrollToLatestMessage() {
  const last = messages.lastElementChild;
  if (last) last.scrollIntoView({ behavior: 'smooth', block: 'end' });
}

function processMessageQueue() {
  if (isDisplayingBlock || messageQueue.length === 0) return;

  const item = messageQueue.shift();
  isDisplayingBlock = true;

  if (item.isJudge) {
    showJudgeSummary(item.text);
    scrollToLatestMessage();
    isDisplayingBlock = false;
    if (item.run_id) {
      setTimeout(() => {
        currentRunId = item.run_id;
        updateDownloadReportButton();
      }, 1000);
    }
    processMessageQueue();
    return;
  }

  addMessage(item.speaker, item.role, item.text, true, () => {
    isDisplayingBlock = false;
    processMessageQueue();
  }, item.role_label);
}

function enqueueMessage(speaker, role, text, isJudge = false, roleLabel, runId = null) {
  messageQueue.push({ speaker, role, text, isJudge, role_label: roleLabel, run_id: runId });
  processMessageQueue();
}

function formatMessageText(text) {
  return escapeHtml(text).replace(/\n/g, '<br>');
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function showWelcome() {
  welcomeScreen.style.display = 'flex';
  messagesContainer.style.display = 'none';
  currentRunId = null;
  updateDownloadReportButton();
}

function showDebate(topic) {
  welcomeScreen.style.display = 'none';
  messagesContainer.style.display = 'flex';
  debateTopic.textContent = topic;
  messages.innerHTML = '';
  judgeSummary.style.display = 'none';
  judgeSummary.innerHTML = '';
  messageQueue.length = 0;
  isDisplayingBlock = false;
  updateDownloadReportButton();
}

function showJudgeSummary(text) {
  judgeSummary.innerHTML = `
    <div class="judge-summary-title">
      <span class="message-avatar" style="width:28px;height:28px;font-size:12px;">J</span>
      Judge's Verdict
    </div>
    <div class="judge-summary-content">${formatMessageText(text)}</div>
  `;
  judgeSummary.style.display = 'block';
  scrollToLatestMessage();
}

function updateDownloadReportButton() {
  if (currentRunId) {
    downloadReportBtn.style.display = '';
    downloadReportBtn.href = `/api/debates/${encodeURIComponent(currentRunId)}/report.pdf`;
    downloadReportBtn.setAttribute('download', '');
  } else {
    downloadReportBtn.style.display = 'none';
    downloadReportBtn.removeAttribute('href');
  }
}

async function startDebate(topic, botAName, botBName) {
  currentRunId = null;
  inProgressTopic = topic;
  showDebate(topic);
  startBtn.disabled = true;
  refreshDebateList();

  try {
    const body = { topic };
    if (botAName) body.bot_a_name = botAName;
    if (botBName) body.bot_b_name = botBName;
    if (botARoleInput && botARoleInput.value.trim()) body.bot_a_role = botARoleInput.value.trim();
    if (botBRoleInput && botBRoleInput.value.trim()) body.bot_b_role = botBRoleInput.value.trim();
    const maxTurns = parseInt(document.getElementById('maxTurns').value) || 4;
    body.max_turns = maxTurns;
    const response = await fetch('/api/debate/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.error || 'Failed to start debate');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split('\n\n');
      buffer = events.pop() || '';

      for (const event of events) {
        const line = event.split('\n').find((l) => l.startsWith('data: '));
        if (line) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.done) {
              inProgressTopic = null;
              refreshDebateList();
              return;
            }
            if (data.speaker && data.text !== undefined) {
              const role = data.role || (data.speaker === 'Athena' ? 'pro' : data.speaker === 'Dion' ? 'con' : data.speaker === 'Moderator' ? 'moderator' : 'judge');
              const runId = data.run_id || null;
              enqueueMessage(data.speaker, role, data.text, role === 'judge', data.role_label, runId);
            }
          } catch (e) {
            console.warn('Parse SSE:', e);
          }
        }
      }
    }
  } catch (err) {
    addMessage('System', 'moderator', `Error: ${err.message}`, false);
    inProgressTopic = null;
    refreshDebateList();
  } finally {
    startBtn.disabled = false;
  }
}

function loadPastDebate(runId) {
  if (loadAbortController) loadAbortController.abort();
  loadAbortController = new AbortController();
  loadingRunId = runId;
  currentRunId = null;
  showDebate('Loading…');
  updateDownloadReportButton();

  fetch(`/api/debates/${runId}`, { signal: loadAbortController.signal })
    .then((r) => r.json())
    .then((data) => {
      if (data.run_id !== loadingRunId) return;
      currentRunId = null;
      showDebate(data.topic);

      for (const msg of data.transcript || []) {
        const role = msg.role || (msg.speaker === 'Athena' ? 'pro' : msg.speaker === 'Dion' ? 'con' : msg.speaker === 'Moderator' ? 'moderator' : 'judge');
        if (role === 'judge') {
          showJudgeSummary(msg.text);
          setTimeout(() => {
            currentRunId = data.run_id;
            updateDownloadReportButton();
          }, 1000);
        } else {
          addMessage(msg.speaker, role, msg.text, false, undefined, msg.role_label);
        }
      }

      refreshDebateList();
    })
    .catch((err) => {
      if (err.name === 'AbortError') return;
      addMessage('System', 'moderator', 'Failed to load debate.', false);
    });
}

function refreshDebateList() {
  fetch('/api/debates')
    .then((r) => r.json())
    .then((runs) => {
      if (inProgressTopic) {
        runs = [{ run_id: '', topic: inProgressTopic, in_progress: true }, ...runs];
      }
      if (runs.length === 0) {
        debateList.innerHTML = '<div class="debate-list-empty">No past debates yet</div>';
        return;
      }

      debateList.innerHTML = runs
        .map((r) => {
          const inProgress = r.in_progress === true;
          const date = inProgress ? 'In progress…' : (r.timestamp ? new Date(r.timestamp).toLocaleDateString() : '');
          const active = inProgress || r.run_id === currentRunId ? ' active' : '';
          const runId = inProgress ? '' : r.run_id;
          return `
            <div class="debate-item${active}${inProgress ? ' debate-item-in-progress' : ''}" data-run-id="${escapeHtml(runId)}" data-in-progress="${inProgress ? '1' : '0'}">
              <div class="debate-item-title">${escapeHtml(r.topic)}</div>
              <div class="debate-item-date">${escapeHtml(date)}</div>
            </div>
          `;
        })
        .join('');

      debateList.querySelectorAll('.debate-item').forEach((el) => {
        if (el.dataset.inProgress === '1') return;
        el.addEventListener('click', () => {
          const id = el.dataset.runId;
          if (id) loadPastDebate(id);
        });
      });
    })
    .catch(() => {});
}

topicForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const topic = topicInput.value.trim();
  if (!topic) return;
  const botAName = (botANameInput && botANameInput.value.trim()) || undefined;
  const botBName = (botBNameInput && botBNameInput.value.trim()) || undefined;
  startDebate(topic, botAName, botBName);
});

newDebateBtn.addEventListener('click', () => {
  topicInput.value = '';
  showWelcome();
});

refreshDebateList();