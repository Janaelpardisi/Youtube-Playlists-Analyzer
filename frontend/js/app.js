/* ─────────────────────────────────────────────────────────────
   YouTube Playlist Analyzer — Frontend Logic (v2)
   Uses the existing HTML element IDs from index.html
   ───────────────────────────────────────────────────────────── */

const API = '';

// ── State ──
let state = {
  currentChannelId: null,
  currentChannelName: '',
  currentPlaylistId: null,
  currentPlaylistName: '',
  currentSessionId: null,
  totalVideos: 0,
  analyzedCount: 0,
  isAnalyzing: false,
  chatHistory: [],
};

// ─────────────────────────────────────────────
// Init
// ─────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadSessions();
  const srch = document.getElementById('srch');
  if (srch) srch.addEventListener('keydown', (e) => { if (e.key === 'Enter') handleSearch(); });
});

// ─────────────────────────────────────────────
// Sessions
// ─────────────────────────────────────────────
async function loadSessions() {
  try {
    const res = await fetch(`${API}/api/sessions`);
    const data = await res.json();
    renderSessions(data.sessions || []);
  } catch (e) { console.error('Failed to load sessions', e); }
}

function renderSessions(sessions) {
  const section = document.getElementById('sec-sessions');
  const grid = document.getElementById('sg');
  const countBadge = document.getElementById('scnt');
  if (!section || !grid) return;

  if (!sessions || sessions.length === 0) {
    section.classList.add('hidden');
    return;
  }
  section.classList.remove('hidden');
  if (countBadge) countBadge.textContent = sessions.length;

  grid.innerHTML = sessions.map(s => {
    const pct = s.total_videos ? Math.round((s.analyzed_count / s.total_videos) * 100) : 0;
    const isComplete = s.status === 'completed';
    const date = new Date(s.last_updated).toLocaleDateString('ar-EG');
    return `
      <div class="sc">
        <div class="sc-top">
          <div class="sc-names">
            <h3>${escHtml(s.playlist_name)}</h3>
            <span>${escHtml(s.channel_name)}</span>
          </div>
          <span class="${isComplete ? 'bd' : 'bp'}">${isComplete ? '&#10003; مكتمل' : '&#9208; جارٍ'}</span>
        </div>
        <div class="mbar"><div class="mbar-f" style="width:${pct}%"></div></div>
        <div class="sc-ft">
          <span class="sc-cnt">${s.analyzed_count}/${s.total_videos} فيديو &bull; ${date}</span>
          <div class="sc-acts">
            <button class="btn-del" onclick="delSess('${s.session_id}', event)">حذف</button>
            <button class="btn-res" onclick="resumeSess('${s.session_id}')">
              ${isComplete ? '&#128065; عرض' : '&#9654; استكمال'}
            </button>
          </div>
        </div>
      </div>`;
  }).join('');
}

async function delSess(sessionId, event) {
  event.stopPropagation();
  if (!confirm('حذف هذه الجلسة؟')) return;
  await fetch(`${API}/api/sessions/${sessionId}`, { method: 'DELETE' });
  loadSessions();
}

async function resumeSess(sessionId) {
  const res = await fetch(`${API}/api/sessions/${sessionId}/results`);
  const data = await res.json();
  if (!data.session) return showErr('الجلسة غير موجودة');

  const session = data.session;
  state.currentSessionId = sessionId;
  state.currentPlaylistId = session.playlist_id;
  state.currentPlaylistName = session.playlist_name;
  state.currentChannelName = session.channel_name;
  state.totalVideos = session.total_videos;
  state.analyzedCount = session.analyzed_count;
  state.chatHistory = [];

  showSec('analysis');
  resetAiPanels();
  renderMeta(session.channel_name, session.playlist_name, session.total_videos);
  updateProg(session.analyzed_count, session.total_videos);
  renderCards(data.videos || []);

  if (session.status === 'completed') {
    setDone();
    showAiToolbar();
    if (session.summary) {
      document.getElementById('summary-content').innerHTML = fmtExp(session.summary);
      document.getElementById('summary-panel').classList.remove('hidden');
    }
    if (session.learning_path) renderLearningPath(session.learning_path);
  } else {
    // Show AI toolbar if at least 1 video is already analyzed
    if (session.analyzed_count > 0) showAiToolbar();
    document.getElementById('bctl').classList.remove('hidden');
    document.getElementById('binf').innerHTML =
      `تم تحليل <strong>${session.analyzed_count}</strong> من <strong>${session.total_videos}</strong>. اضغطي للمتابعة.`;
  }
}

// ─────────────────────────────────────────────
// Search
// ─────────────────────────────────────────────
async function handleSearch() {
  const q = (document.getElementById('srch')?.value || '').trim();
  if (!q) return showErr('أدخلي اسم القناة أو لينك الـ Playlist');
  hideErr();
  setSearchLoad(true);

  try {
    const res = await fetch(`${API}/api/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: q })
    });
    const data = await res.json();
    if (!res.ok) return showErr(data.detail || 'خطأ في البحث');

    if (data.type === 'playlist' && data.playlist) {
      await startFromPl(data.playlist);
    } else if (data.type === 'channels' && data.channels?.length) {
      renderChannels(data.channels);
      showSec('channels');
    } else {
      showErr('لم يتم العثور على نتائج');
    }
  } catch (e) {
    showErr('فشل الاتصال: ' + e.message);
  } finally {
    setSearchLoad(false);
  }
}

// Shim for onclick="doSearch()"
function doSearch() { handleSearch(); }

function setSearchLoad(on) {
  const btn = document.getElementById('srch-btn');
  const txt = document.getElementById('sbt');
  const sp = document.getElementById('ssp');
  if (btn) btn.disabled = on;
  if (txt) txt.classList.toggle('hidden', on);
  if (sp) sp.classList.toggle('hidden', !on);
}

// ─────────────────────────────────────────────
// Channels
// ─────────────────────────────────────────────
function renderChannels(chs) {
  const grid = document.getElementById('chg');
  if (!grid) return;
  grid.innerHTML = chs.map(c => `
    <div class="chc" onclick="selCh('${c.channel_id}', '${escAttr(c.title)}')">
      ${c.thumbnail
      ? `<img class="ch-img" src="${c.thumbnail}" alt="" onerror="this.style.display='none'">`
      : `<div class="ch-pl">${escHtml((c.title || '?').charAt(0))}</div>`}
      <div class="ch-n">
        <h3>${escHtml(c.title)}</h3>
        <p>${escHtml(c.description || '')}</p>
      </div>
    </div>`).join('');
}

async function selCh(channelId, channelName) {
  state.currentChannelId = channelId;
  state.currentChannelName = channelName;
  showSec('playlists');
  document.getElementById('plg').innerHTML = '<div class="loading">&#9203; جارٍ تحميل الـ Playlists...</div>';
  try {
    const res = await fetch(`${API}/api/channels/${channelId}/playlists`);
    const data = await res.json();
    renderPlaylists(data.playlists || []);
  } catch (e) {
    document.getElementById('plg').innerHTML = `<div class="loading" style="color:var(--rd)">خطأ: ${e.message}</div>`;
  }
}

// ─────────────────────────────────────────────
// Playlists
// ─────────────────────────────────────────────
function renderPlaylists(pls) {
  const grid = document.getElementById('plg');
  if (!pls.length) { grid.innerHTML = '<div class="loading">لا توجد Playlists.</div>'; return; }
  grid.innerHTML = pls.map(p => `
    <div class="plc" onclick="selPl('${p.playlist_id}', '${escAttr(p.title)}')">
      ${p.thumbnail ? `<img class="pl-th" src="${p.thumbnail}" alt="">` : '<div class="pl-thp">&#128203;</div>'}
      <div class="pl-in">
        <h3>${escHtml(p.title)}</h3>
        <p>${escHtml(p.description || '')}</p>
        <span class="pl-cnt">&#9654; ${p.video_count} فيديو</span>
      </div>
    </div>`).join('');
}

function selPl(playlistId, playlistName) {
  state.currentPlaylistId = playlistId;
  state.currentPlaylistName = playlistName;
  startFromPl({ playlist_id: playlistId, title: playlistName });
}

async function startFromPl(pl) {
  showSec('analysis');
  state.chatHistory = [];
  resetAiPanels();
  renderMeta(state.currentChannelName || pl.channel_name || '', pl.title || pl.playlist_name, '...');
  document.getElementById('vl').innerHTML = '<div class="loading">&#9203; جارٍ تحميل الفيديوهات...</div>';
  document.getElementById('bctl').classList.add('hidden');
  document.getElementById('done').classList.add('hidden');

  try {
    const res = await fetch(`${API}/api/sessions/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        playlist_id: pl.playlist_id || pl.id,
        channel_id: state.currentChannelId || pl.channel_id || '',
        channel_name: state.currentChannelName || pl.channel_name || 'قناة',
        playlist_name: pl.title || pl.playlist_name
      })
    });
    const data = await res.json();
    if (!res.ok) return showErr(data.detail || 'خطأ في تحميل الـ Playlist');

    state.currentSessionId = data.session_id;
    state.totalVideos = data.total_videos;
    state.analyzedCount = 0;

    renderMeta(state.currentChannelName || pl.channel_name || '', pl.title || pl.playlist_name, data.total_videos);
    updateProg(0, data.total_videos);

    // Fetch and show ALL videos immediately so user can pick which to analyze
    const allRes = await fetch(`${API}/api/sessions/${data.session_id}/results`);
    const allData = await allRes.json();
    document.getElementById('vl').innerHTML = '';
    renderCards(allData.videos || []);

    // Show batch control bar at bottom
    document.getElementById('bctl').classList.remove('hidden');
    document.getElementById('binf').innerHTML =
      `&#128249; اضغطي <strong>"تحليل"</strong> على أي فيديو لتحليله منفرداً، أو <strong>"تحليل الـ 3 التاليين"</strong> للتحليل بالجملة.`;
    loadSessions();
  } catch (e) {
    document.getElementById('vl').innerHTML = `<div class="loading" style="color:var(--rd)">خطأ: ${e.message}</div>`;
  }
}

// ─────────────────────────────────────────────
// Batch Analysis
// ─────────────────────────────────────────────
async function nextBatch() {
  if (state.isAnalyzing || !state.currentSessionId) return;
  state.isAnalyzing = true;

  const btn = document.getElementById('bgo');
  const txt = document.getElementById('bgot');
  const sp = document.getElementById('bgos');
  btn.disabled = true;
  txt.classList.add('hidden');
  sp.classList.remove('hidden');

  addSkels(3);

  try {
    const res = await fetch(`${API}/api/sessions/${state.currentSessionId}/analyze-next`, { method: 'POST' });
    const data = await res.json();
    document.querySelectorAll('.sk-card').forEach(el => el.remove());

    if (!res.ok) return showErr(data.detail || 'خطأ في التحليل');
    if (data.is_complete && (!data.videos || !data.videos.length)) { setDone(); return; }

    state.analyzedCount = data.analyzed_count;
    state.totalVideos = data.total_videos;

    renderCards(data.videos, true);
    updateProg(data.analyzed_count, data.total_videos);

    // Show AI toolbar as soon as we have at least 1 analyzed video
    showAiToolbar();

    if (data.is_complete) {
      setDone();
    } else {
      document.getElementById('binf').innerHTML =
        `تم تحليل <strong>${data.analyzed_count}</strong> من <strong>${data.total_videos}</strong>. هل تكملين الـ 3 التاليين؟`;
    }
    loadSessions();
  } catch (e) {
    document.querySelectorAll('.sk-card').forEach(el => el.remove());
    showErr('خطأ: ' + e.message);
  } finally {
    state.isAnalyzing = false;
    btn.disabled = false;
    txt.classList.remove('hidden');
    sp.classList.add('hidden');
  }
}

function stopIt() {
  document.getElementById('binf').innerHTML = '&#9208; تم الحفظ. أكملي لاحقاً من "جلسات سابقة".';
}

function setDone() {
  document.getElementById('bctl').classList.add('hidden');
  document.getElementById('done').classList.remove('hidden');
  updateProg(state.totalVideos, state.totalVideos);
}

// ─────────────────────────────────────────────
// Single Video Analysis
// ─────────────────────────────────────────────
async function analyzeOneVideo(videoId, btn) {
  if (!state.currentSessionId) return;
  if (btn) { btn.disabled = true; btn.textContent = '⏳'; }

  // Show skeleton in the expansion area
  const expEl = document.getElementById('ve-' + videoId);
  if (expEl) expEl.innerHTML = '<span style="color:var(--t3)">&#9203; Gemini يحلل الفيديو...</span>';
  if (expEl) expEl.classList.add('sh');
  const tog = document.getElementById('vt-' + videoId);
  if (tog) tog.classList.add('op');

  try {
    const res = await fetch(`${API}/api/sessions/${state.currentSessionId}/analyze-video`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ video_id: videoId })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);

    const v = data.video;
    state.analyzedCount = data.analyzed_count;
    state.totalVideos = data.total_videos;
    updateProg(data.analyzed_count, data.total_videos);

    // Update the card in-place
    renderCards([v], false);

    // Remove the analyze button from card
    const card = document.getElementById('vc-' + videoId);
    const analyzeBtn = card?.querySelector('.btn-analyze-single');
    if (analyzeBtn) analyzeBtn.remove();

    // Show AI toolbar as soon as we have at least 1 analyzed video
    showAiToolbar();

    if (data.is_complete) {
      setDone();
    } else {
      document.getElementById('binf').innerHTML =
        `تم تحليل <strong>${data.analyzed_count}</strong> من <strong>${data.total_videos}</strong>.`;
    }
    loadSessions();
  } catch (e) {
    if (expEl) expEl.innerHTML = `<span style="color:var(--rd)">خطأ: ${e.message}</span>`;
    if (btn) { btn.disabled = false; btn.textContent = '▶ تحليل'; }
  }
}
function showAiToolbar() {
  const t = document.getElementById('ai-toolbar');
  if (t) t.classList.remove('hidden');
}

function resetAiPanels() {
  ['summary-panel', 'learning-path-panel', 'chat-panel', 'ai-toolbar'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.classList.add('hidden');
  });
  const cm = document.getElementById('chat-messages');
  if (cm) cm.innerHTML = '';
  state.chatHistory = [];
}

// ─────────────────────────────────────────────
// Feature 2 — Summary
// ─────────────────────────────────────────────
async function generateSummary() {
  if (!state.currentSessionId) return;
  const panel = document.getElementById('summary-panel');
  const content = document.getElementById('summary-content');
  const btn = document.getElementById('btn-summary');
  panel.classList.remove('hidden');
  content.innerHTML = '<div class="ai-loading">&#9203; Gemini يولد الملخص التنفيذي...</div>';
  if (btn) btn.disabled = true;
  panel.scrollIntoView({ behavior: 'smooth', block: 'start' });

  try {
    const res = await fetch(`${API}/api/sessions/${state.currentSessionId}/summary`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);
    content.innerHTML = fmtExp(data.summary);
  } catch (e) {
    content.innerHTML = `<p style="color:var(--rd)">خطأ: ${e.message}</p>`;
  } finally {
    if (btn) btn.disabled = false;
  }
}

// ─────────────────────────────────────────────
// Feature 3 — Learning Path
// ─────────────────────────────────────────────
async function generateLearningPath() {
  if (!state.currentSessionId) return;
  const panel = document.getElementById('learning-path-panel');
  const content = document.getElementById('learning-path-content');
  const btn = document.getElementById('btn-learning-path');
  panel.classList.remove('hidden');
  content.innerHTML = '<div class="ai-loading">&#9203; Gemini يصمم مسار التعلم...</div>';
  if (btn) btn.disabled = true;
  panel.scrollIntoView({ behavior: 'smooth', block: 'start' });

  try {
    const res = await fetch(`${API}/api/sessions/${state.currentSessionId}/learning-path`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);
    renderLearningPath(data.learning_path);
  } catch (e) {
    content.innerHTML = `<p style="color:var(--rd)">خطأ: ${e.message}</p>`;
  } finally {
    if (btn) btn.disabled = false;
  }
}

function renderLearningPath(lp) {
  const content = document.getElementById('learning-path-content');
  const panel = document.getElementById('learning-path-panel');
  if (panel) panel.classList.remove('hidden');
  const phases = lp?.phases || [];
  if (!phases.length) { content.innerHTML = '<p style="color:var(--t3)">لم يتم توليد مسار.</p>'; return; }

  const colors = ['#6366f1', '#10b981', '#f59e0b', '#ef4444'];
  content.innerHTML = `<div class="learning-path-track">
    ${phases.map((ph, i) => `
      <div class="lp-phase" style="--phase-color:${colors[i % colors.length]}">
        <div class="lp-phase-header">
          <div class="lp-phase-num">${i + 1}</div>
          <div>
            <div class="lp-phase-title">${escHtml(ph.title)}</div>
            <div class="lp-phase-desc">${escHtml(ph.description || '')}</div>
          </div>
        </div>
        <div class="lp-videos">
          ${(ph.video_ids || []).map(vid => {
    const card = document.getElementById('vc-' + vid);
    const title = card?.querySelector('.v-ti')?.textContent || vid;
    return `<span class="lp-video-chip" onclick="scrollToVid('${vid}')">${escHtml(title.substring(0, 45))}</span>`;
  }).join('')}
        </div>
      </div>
      ${i < phases.length - 1 ? '<div class="lp-connector">↓</div>' : ''}
    `).join('')}
  </div>`;
}

function scrollToVid(videoId) {
  const card = document.getElementById('vc-' + videoId);
  if (card) {
    card.scrollIntoView({ behavior: 'smooth', block: 'center' });
    card.style.boxShadow = '0 0 0 3px var(--p)';
    setTimeout(() => card.style.boxShadow = '', 2000);
    const exp = document.getElementById('ve-' + videoId);
    if (exp && !exp.classList.contains('sh')) togV(videoId);
  }
}

// ─────────────────────────────────────────────
// Feature 4 — Chat
// ─────────────────────────────────────────────
function toggleChat() {
  const panel = document.getElementById('chat-panel');
  panel.classList.toggle('hidden');
  if (!panel.classList.contains('hidden')) {
    panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
    document.getElementById('chat-input')?.focus();
  }
}

async function sendChatMessage() {
  const input = document.getElementById('chat-input');
  const question = (input?.value || '').trim();
  if (!question || !state.currentSessionId) return;
  input.value = '';

  appendChatMsg('user', question);
  state.chatHistory.push({ role: 'user', content: question });

  const thinkId = appendChatThinking();
  try {
    const res = await fetch(`${API}/api/sessions/${state.currentSessionId}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, history: state.chatHistory.slice(-10) })
    });
    const data = await res.json();
    removeChatThinking(thinkId);
    const answer = res.ok ? data.answer : `خطأ: ${data.detail}`;
    appendChatMsg('assistant', answer, res.ok ? data.referenced_videos : []);
    state.chatHistory.push({ role: 'assistant', content: answer });
  } catch (e) {
    removeChatThinking(thinkId);
    appendChatMsg('assistant', `عذراً، حدث خطأ: ${e.message}`);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const ci = document.getElementById('chat-input');
  if (ci) ci.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChatMessage(); } });
});

function appendChatMsg(role, text, refs = []) {
  const msgs = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = `chat-message chat-${role}`;
  let refsHtml = '';
  if (refs?.length) {
    refsHtml = `<div class="chat-refs"><span class="chat-refs-label">الفيديوهات المرتبطة:</span>
      ${refs.map(v => `<span class="chat-ref-chip" onclick="scrollToVid('${v.video_id}')">&#128249; ${escHtml((v.title || '').substring(0, 35))}</span>`).join('')}
    </div>`;
  }
  div.innerHTML = `<div class="chat-bubble">${fmtExp(text)}${refsHtml}</div>`;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}

function appendChatThinking() {
  const msgs = document.getElementById('chat-messages');
  const id = 'th-' + Date.now();
  const div = document.createElement('div');
  div.className = 'chat-message chat-assistant'; div.id = id;
  div.innerHTML = '<div class="chat-bubble chat-thinking">&#9203; Gemini يفكر...</div>';
  msgs.appendChild(div); msgs.scrollTop = msgs.scrollHeight;
  return id;
}
function removeChatThinking(id) { document.getElementById(id)?.remove(); }

// ─────────────────────────────────────────────
// Render Helpers
// ─────────────────────────────────────────────
function renderMeta(ch, pl, cnt) {
  const el = document.getElementById('plmeta');
  if (el) el.innerHTML = `<h2>${escHtml(pl)}</h2>
    <div class="pl-meta-st"><span>&#128250; ${escHtml(ch)}</span><span>&#127909; ${cnt} فيديو</span></div>`;
}

function updateProg(done, total) {
  const p = total ? Math.round(done / total * 100) : 0;
  const pb = document.getElementById('pb');
  const ptx = document.getElementById('ptx');
  const ppct = document.getElementById('ppct');
  if (pb) pb.style.width = p + '%';
  if (ptx) ptx.textContent = `${done} / ${total} فيديو تم تحليله`;
  if (ppct) ppct.textContent = p + '%';
}

const LEVEL_COLORS = { 'مبتدئ': '#10b981', 'متوسط': '#f59e0b', 'متقدم': '#ef4444' };
const TYPE_COLORS = { 'نظري': '#6366f1', 'تطبيقي': '#3b82f6', 'مراجعة': '#8b5cf6', 'مشروع': '#ec4899' };

function renderCards(vids, anim) {
  const l = document.getElementById('vl');
  (vids || []).forEach(v => {
    const existing = document.getElementById('vc-' + v.video_id);
    if (existing) {
      // Update badge
      const badge = existing.querySelector('.ba,.bp2');
      if (badge && v.analyzed) { badge.className = 'ba'; badge.innerHTML = '&#10003; تم'; }
      // Update explanation
      const expEl = document.getElementById('ve-' + v.video_id);
      if (expEl && v.explanation) { expEl.innerHTML = fmtExp(v.explanation); expEl.classList.add('sh'); }
      // Update tags
      let tagsRow = existing.querySelector('.tags-row');
      if (v.analyzed) {
        const tagsHtml = buildTags(v);
        if (tagsRow) tagsRow.innerHTML = tagsHtml;
        else if (tagsHtml) {
          const vti = existing.querySelector('.v-ti');
          if (vti) { const tr = document.createElement('div'); tr.className = 'tags-row'; tr.innerHTML = tagsHtml; vti.after(tr); }
        }
      }
      // Remove analyze button
      existing.querySelector('.btn-analyze-single')?.remove();
      return;
    }

    const div = document.createElement('div');
    div.className = 'vc'; div.id = 'vc-' + v.video_id;
    if (anim) div.style.animation = 'fu .4s ease';

    const tagsHtml = buildTags(v);
    const exp = v.explanation ? fmtExp(v.explanation) : '<span style="color:var(--t3)">لم يُحلَّل بعد.</span>';
    const analyzeBtn = !v.analyzed
      ? `<button class="btn-analyze-single" onclick="event.stopPropagation();analyzeOneVideo('${v.video_id}', this)" title="تحليل هذا الفيديو">&#9654; تحليل</button>`
      : '';

    div.innerHTML = `
      <div class="vc-hdr" onclick="togV('${v.video_id}')">
        <div class="v-num">${(v.position || 0) + 1}</div>
        ${v.thumbnail ? `<img class="v-img" src="${v.thumbnail}" alt="">` : ''}
        <div class="v-tw">
          <div class="v-ti">${escHtml(v.title || 'فيديو')}</div>
          ${tagsHtml ? `<div class="tags-row">${tagsHtml}</div>` : ''}
          <span class="${v.analyzed ? 'ba' : 'bp2'}">${v.analyzed ? '&#10003; تم' : '&#8987; انتظار'}</span>
        </div>
        ${analyzeBtn}
        <span class="v-tog" id="vt-${v.video_id}">&#9660;</span>
      </div>
      <div class="v-exp ${v.analyzed ? 'sh' : ''}" id="ve-${v.video_id}">${exp}</div>`;
    l.appendChild(div);
  });
}

function buildTags(v) {
  if (!v.analyzed) return '';
  const tags = [];
  if (v.level) tags.push(`<span class="tag-badge" style="--tag-color:${LEVEL_COLORS[v.level] || '#6366f1'}">${escHtml(v.level)}</span>`);
  if (v.type) tags.push(`<span class="tag-badge" style="--tag-color:${TYPE_COLORS[v.type] || '#3b82f6'}">${escHtml(v.type)}</span>`);
  if (v.estimated_minutes) tags.push(`<span class="tag-badge" style="--tag-color:#64748b">&#9201; ${v.estimated_minutes}د</span>`);
  if (v.requires_previous) tags.push(`<span class="tag-badge" style="--tag-color:#78716c">&#9939; يعتمد على سابق</span>`);
  (v.topics || []).slice(0, 3).forEach(t => tags.push(`<span class="tag-badge topic-tag">${escHtml(t)}</span>`));
  return tags.join('');
}

function togV(id) {
  document.getElementById('ve-' + id)?.classList.toggle('sh');
  document.getElementById('vt-' + id)?.classList.toggle('op');
}

function fmtExp(t) {
  if (!t) return '';
  return t
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/^#{1,3}\s+(.+)$/gm, '<h3>$1</h3>')
    .split('\n').join('<br>');
}

function addSkels(n) {
  const l = document.getElementById('vl');
  for (let i = 0; i < n; i++) {
    const d = document.createElement('div');
    d.className = 'vc sk-card'; d.style.padding = '15px';
    d.innerHTML = '<div class="sk m"></div><div class="sk s"></div><div class="sk" style="margin-top:11px;height:10px"></div><div class="sk m" style="height:10px"></div>';
    l.appendChild(d);
  }
}

// ─────────────────────────────────────────────
// Navigation
// ─────────────────────────────────────────────
function showSec(name) {
  ['channels', 'playlists', 'analysis'].forEach(s => {
    document.getElementById('sec-' + s)?.classList.add('hidden');
  });
  document.getElementById('sec-' + name)?.classList.remove('hidden');
}

function goBack(to) { showSec(to); }

// ─────────────────────────────────────────────
// Utils
// ─────────────────────────────────────────────
function showErr(msg) {
  const e = document.getElementById('err');
  if (!e) return;
  e.textContent = msg; e.classList.add('on');
  setTimeout(() => e.classList.remove('on'), 6000);
}
function hideErr() { document.getElementById('err')?.classList.remove('on'); }

function escHtml(str) {
  return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
function escAttr(str) { return String(str || '').replace(/'/g, "\\'"); }
