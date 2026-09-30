// ═══════════════════════════════════════════════════════════════
//  ARIA PARTICLE BACKGROUND
// ═══════════════════════════════════════════════════════════════
(function initParticles() {
    const canvas = document.getElementById('particleCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let W, H, particles = [];
    const COLORS = ['rgba(139,92,246,', 'rgba(236,72,153,', 'rgba(6,182,212,'];

    function resize() {
        W = canvas.width = window.innerWidth;
        H = canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener('resize', resize);

    function mkParticle() {
        const c = COLORS[Math.floor(Math.random() * COLORS.length)];
        return {
            x: Math.random() * W, y: Math.random() * H,
            r: Math.random() * 1.4 + 0.3,
            vx: (Math.random() - .5) * 0.22,
            vy: (Math.random() - .5) * 0.18,
            a: Math.random() * 0.55 + 0.15,
            da: (Math.random() - .5) * 0.003,
            color: c,
        };
    }
    for (let i = 0; i < 100; i++) particles.push(mkParticle());

    // Draw connecting lines
    function drawLines() {
        for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
                const dx = particles[i].x - particles[j].x;
                const dy = particles[i].y - particles[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 110) {
                    const alpha = (1 - dist / 110) * 0.06;
                    ctx.beginPath();
                    ctx.strokeStyle = `rgba(139,92,246,${alpha})`;
                    ctx.lineWidth = 0.5;
                    ctx.moveTo(particles[i].x, particles[i].y);
                    ctx.lineTo(particles[j].x, particles[j].y);
                    ctx.stroke();
                }
            }
        }
    }

    function loop() {
        ctx.clearRect(0, 0, W, H);
        drawLines();
        particles.forEach(p => {
            p.a += p.da;
            if (p.a > 0.7 || p.a < 0.1) p.da *= -1;
            p.x += p.vx; p.y += p.vy;
            if (p.x < 0) p.x = W; if (p.x > W) p.x = 0;
            if (p.y < 0) p.y = H; if (p.y > H) p.y = 0;
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
            ctx.fillStyle = p.color + p.a + ')';
            ctx.fill();
        });
        requestAnimationFrame(loop);
    }
    loop();
})();

// ═══════════════════════════════════════════════════════════════
//  GLOBAL LOADER DISMISS
// ═══════════════════════════════════════════════════════════════
function dismissLoader() {
    const loader = document.getElementById('globalLoader');
    if (loader) {
        loader.classList.add('hidden');
        setTimeout(() => { if (loader.parentNode) loader.parentNode.removeChild(loader); }, 500);
    }
}
// ═══════════════════════════════════════════════════════════════
//  ARIA TOAST NOTIFICATION SYSTEM
// ═══════════════════════════════════════════════════════════════
const _TOAST_ICONS = { ok: '✅', warn: '⚠️', err: '❌', info: '💠' };
function showToast(title, msg = '', type = 'info', duration = 3800) {
    const host = document.getElementById('ariaToastHost');
    if (!host) return;
    const t = document.createElement('div');
    t.className = `p-toast ${type}`;
    t.innerHTML = `
        <span class="p-toast-icon">${_TOAST_ICONS[type] || '💠'}</span>
        <div class="p-toast-body">
            <div class="p-toast-title">${title}</div>
            ${msg ? `<div class="p-toast-msg">${msg}</div>` : ''}
        </div>
        <button class="p-toast-close" onclick="removeToast(this.parentElement)">×</button>`;
    host.appendChild(t);
    if (duration > 0) setTimeout(() => removeToast(t), duration);
}
function removeToast(el) {
    if (!el || !el.parentNode) return;
    el.classList.add('p-toast-exit');
    setTimeout(() => { if (el.parentNode) el.parentNode.removeChild(el); }, 380);
}

// ═══════════════════════════════════════════════════════════════
//  TYPEWRITER EFFECT
// ═══════════════════════════════════════════════════════════════
function typewrite(el, text, speed = 28) {
    if (!el) return;
    el.textContent = '';
    const cursor = document.createElement('span');
    cursor.className = 'typewriter-cursor';
    el.appendChild(cursor);
    let i = 0;
    const iv = setInterval(() => {
        if (i >= text.length) { clearInterval(iv); return; }
        cursor.insertAdjacentText('beforebegin', text[i++]);
    }, speed);
}

// ═══════════════════════════════════════════════════════════════
//  ANIMATED NUMBER COUNTER
// ═══════════════════════════════════════════════════════════════
function countUp(id, target, duration = 700, decimals = 0) {
    const el = document.getElementById(id);
    if (!el) return;
    const start = parseFloat(el.textContent) || 0;
    const end = parseFloat(target) || 0;
    if (start === end) return;
    const t0 = performance.now();
    function tick(now) {
        const p = Math.min(1, (now - t0) / duration);
        const ease = 1 - Math.pow(1 - p, 3);
        const cur = start + (end - start) * ease;
        el.textContent = decimals ? cur.toFixed(decimals) : Math.round(cur);
        if (p < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
}

// ═══════════════════════════════════════════════════════════════
//  KEYBOARD SHORTCUTS
// ═══════════════════════════════════════════════════════════════
document.addEventListener('keydown', e => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;
    if (e.key === '/') {
        e.preventDefault();
        const srch = document.getElementById('cmdSearch');
        if (srch) { navigateTo('commands'); srch.focus(); }
    }
    if (e.key === 'r' && !e.ctrlKey && !e.metaKey) {
        const active = document.querySelector('.nav-item.active');
        if (active) { const s = active.dataset.section; if (s) loadSection(s); }
    }
    if (e.key === 'Escape') {
        const srch = document.getElementById('cmdSearch');
        if (srch && document.activeElement === srch) srch.blur();
    }
});

// ═══════════════════════════════════════════════════════════════
//  NAVIGATE TO SECTION HELPER
// ═══════════════════════════════════════════════════════════════
function navigateTo(sectionId) {
    const item = document.querySelector(`.nav-item[data-section="${sectionId}"]`);
    if (item) item.click();
}

function togglePasswordField(inputId, btn) {
    const el = document.getElementById(inputId);
    if (!el) return;
    const next = el.type === 'password' ? 'text' : 'password';
    el.type = next;
    if (btn) {
        const showing = next === 'text';
        btn.classList.toggle('is-visible', showing);
        btn.setAttribute('aria-label', showing ? 'Hide password' : 'Show password');
        btn.setAttribute('title', showing ? 'Hide password' : 'Show password');
    }
}

// ── User Profile Loader (topbar sync only) ──
async function loadUserProfile() {
    let data = await fetchJSON('/api/max/user-profile');
    if (!data || !data.ok) {
        const me = await fetchJSON('/api/dash/me');
        if (me && me.ok && me.profile) {
            data = {
                ok: true,
                username: me.profile.username || me.profile.user_id || '—',
                user_id: me.profile.user_id || '',
                avatar_url: me.profile.avatar_url || '',
            };
        }
    }
    if (!data || !data.ok) return;

    // Sync topbar chip
    const tbUser = document.getElementById('topbarUsername');
    if (tbUser) tbUser.textContent = data.username || '—';
    
    const tbAvatar = document.getElementById('topbarAvatar');
    setAvatarImage(tbAvatar, data.avatar_url, data.user_id, { allowFallback: true });
    
    // Sync hero avatar
    const heroAvatar = document.getElementById('heroAvatar');
    setAvatarImage(heroAvatar, data.avatar_url, data.user_id, { allowFallback: true });
}

window.addEventListener('DOMContentLoaded', () => {
    loadUserProfile();
    setInterval(loadUserProfile, 10000);
});
// ── Sidebar Toggle (Mobile) ──
const sidebarToggle = document.getElementById('sidebarToggle');
const sidebar = document.querySelector('.sidebar');
const mainContent = document.querySelector('.main-content');
if (sidebarToggle && sidebar && mainContent) {
    sidebarToggle.addEventListener('change', () => {
        if (sidebarToggle.checked) {
            sidebar.style.left = '-240px';
            mainContent.style.marginLeft = '0';
        } else {
            sidebar.style.left = '';
            mainContent.style.marginLeft = '';
        }
    });
}

// ── Overview Quick / Hero Env Loader ──
async function loadOverviewQuick() {
    // Version info → hero env grid
    fetchJSON('/api/max/version-info').then(data => {
        setText('heroVersion', data?.version || '—');
    });
    // MOTD → hero banner
    fetchJSON('/api/max/motd').then(data => {
        const motd = data?.motd || '';
        const el = document.getElementById('heroMotd');
        if (el && motd) typewrite(el, motd, 22);
    });
}

window.addEventListener('DOMContentLoaded', () => {
    loadOverviewQuick();
});
// ── Navigation ────────────────────────────────────────────────────────────────
const navItems = document.querySelectorAll('.nav-item');
const sections = document.querySelectorAll('.section');
const pageTitle = document.getElementById('pageTitle');
let _meProfile = null;
const _liveOverviewState = { lastCount: null, lastTs: null };
const _notificationState = {
    open: false,
    seenTs: 0,
    events: [],
};

navItems.forEach(item => {
    item.addEventListener('click', () => {
        if (item.dataset.hiddenByRole === 'true') return;
        const target = item.dataset.section;
        navItems.forEach(n => n.classList.remove('active'));
        sections.forEach(s => s.classList.remove('active'));
        item.classList.add('active');
        const targetSection = document.getElementById('section-' + target);
        if (!targetSection) return;
        targetSection.classList.add('active');
        // strip emoji from title — take last text node
        const rawText = item.childNodes[item.childNodes.length - 1].textContent.trim();
        pageTitle.textContent = rawText;
        // Update breadcrumb
        const bc = document.getElementById('topbarBreadcrumb');
        if (bc) bc.textContent = target;
        loadSection(target);
        trackDashboardAction('navigate', `Opened ${target}`);
    });
});

// ── API helpers ───────────────────────────────────────────────────────────────
async function fetchJSON(url) {
    try {
        const r = await fetch(url, { cache: 'no-store', credentials: 'same-origin' });
        if (!r.ok) throw new Error(r.status);
        return await r.json();
    } catch (e) {
        console.warn('Fetch failed:', url, e);
        return null;
    }
}

async function postJSON(url, body) {
    try {
        const r = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            cache: 'no-store',
            credentials: 'same-origin',
            body: JSON.stringify(body),
        });
        return await r.json();
    } catch (e) {
        console.warn('Post failed:', url, e);
        return null;
    }
}

function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val != null ? val : '—';
}

function relativeTime(ts) {
    const n = Number(ts || 0);
    if (!n) return 'just now';
    const nowSec = Date.now() / 1000;
    const diff = Math.max(0, Math.floor(nowSec - n));
    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
}

function esc(s) {
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function defaultAvatarUrl(userId) {
    const id = String(userId || '').trim();
    if (!id || id === '—') return '/static/images/aria-favicon.png';
    const n = Number(id);
    const slot = Number.isFinite(n) ? Math.abs(n) % 5 : 0;
    return `https://cdn.discordapp.com/embed/avatars/${slot}.png`;
}

function isDefaultishAvatarSrc(src) {
    const s = String(src || '');
    if (!s) return true;
    return s.includes('/static/images/aria-favicon') || s.includes('/embed/avatars/');
}

function setAvatarImage(el, avatarUrl, userId, opts = {}) {
    if (!el) return;
    const allowFallback = opts.allowFallback !== false;
    const next = String(avatarUrl || '').trim();
    const fallback = defaultAvatarUrl(userId);

    // Do not overwrite a valid custom avatar with fallback during async races.
    if (next) {
        if (el.src !== next) el.src = next;
    } else if (allowFallback && isDefaultishAvatarSrc(el.src)) {
        el.src = fallback;
    }

    el.onerror = () => {
        if (el.src !== fallback) el.src = fallback;
    };
}

function fmtTs(ts) {
    const n = Number(ts || 0);
    if (!n) return '—';
    const d = new Date(n * 1000);
    if (Number.isNaN(d.getTime())) return '—';
    return d.toLocaleString();
}

// ── Status dot ───────────────────────────────────────────────────────────────
function setGlobalStatus(connected) {
    const dot = document.getElementById('globalStatus');
    const lbl = document.getElementById('globalStatusLabel');
    if (dot && lbl) {
        dot.className = 'status-dot ' + (connected ? 'online' : 'offline');
        lbl.textContent = connected ? 'Connected' : 'Disconnected';
    }
}

// ── Overview ──────────────────────────────────────────────────────────────────
async function loadOverview() {
    const res = await fetchJSON('/api/bot');
    if (!res || !res.data) { setGlobalStatus(false); return; }
    const d = res.data;
    // Cache bot data for use by loadRpc Discord card
    window._botDataCache = d;
    setGlobalStatus(d.connected);
    setText('prefix', d.prefix);
    setText('uptime', d.uptime);
    updateUptimeRing(d.uptime);
    countUp('commandCount', d.command_count, 900);
    countUp('commandsRegistered', d.commands_registered, 800);
    setText('connectionStatus', d.connected ? 'Online' : 'Offline');
    const gatewayParts = [];
    if (d.gateway_latency_ms != null) gatewayParts.push(`${Math.round(Number(d.gateway_latency_ms))} ms`);
    gatewayParts.push(`${Number(d.reconnect_attempts || 0)} retries`);
    if (d.connection_quality != null) gatewayParts.push(`quality ${Math.round(Number(d.connection_quality))}%`);
    setText('gatewayDiagnostics', d.identified ? gatewayParts.join(' · ') : 'Waiting for gateway READY');
    setText('botStatus', d.status || 'online');
    setText('clientType', d.client_type || 'mobile');
    updateLiveOverviewMetrics(d);

   // Show welcome modal on first overview load if not dismissed this session
   if (!window._welcomeModalShown) {
        window._welcomeModalShown = true;
        setTimeout(() => {
            openWelcomeModal();
            loadWelcomeUpdates();
            updateWelcomeVersion(d.ui_version ? `v${d.ui_version}` : 'v1.0.0');
        }, 500);
   }
    // ── Hero Banner ──────────────────────────────────────────────────────────
    const heroBadgeConn = document.getElementById('heroBadgeConn');
    if (heroBadgeConn) {
        heroBadgeConn.textContent = d.connected ? '● Connected' : '● Offline';
        heroBadgeConn.classList.toggle('offline', !d.connected);
    }
    const heroBadgeClient = document.getElementById('heroBadgeClient');
    if (heroBadgeClient) heroBadgeClient.textContent = d.client_type || 'mobile';
    const heroBadgePrefix = document.getElementById('heroBadgePrefix');
    if (heroBadgePrefix) heroBadgePrefix.textContent = `prefix: ${d.prefix || '—'}`;
    const heroStatusDot = document.getElementById('heroStatusDot');
    if (heroStatusDot) heroStatusDot.classList.toggle('offline', !d.connected);
    const heroUserId = document.getElementById('heroUserId');
    if (heroUserId) heroUserId.textContent = d.user_id || '—';
    const heroRuntimeState = document.getElementById('heroRuntimeState');
    if (heroRuntimeState) heroRuntimeState.textContent = d.connected ? 'live' : 'offline';
    const heroCommandEcho = document.getElementById('heroCommandEcho');
    if (heroCommandEcho) heroCommandEcho.textContent = String(d.command_count || 0);

    // ── Hero Banner title with username ─────────────────────────────────────
    const dashboardTitle = document.getElementById('heroDashboardTitle');
    if (dashboardTitle && d.username) {
        dashboardTitle.textContent = `${d.username}`;
    }

    // ── Topbar avatar/username sync ──────────────────────────────────────────
    const tbAvatar = document.getElementById('topbarAvatar');
    setAvatarImage(tbAvatar, d.avatar_url, d.user_id, { allowFallback: false });
    const tbUser = document.getElementById('topbarUsername');
    if (tbUser) {
        tbUser.textContent = d.username || '—';
    }

    // ── Hero avatar ──────────────────────────────────────────────────────────
    const heroAvatar = document.getElementById('heroAvatar');
    setAvatarImage(heroAvatar, d.avatar_url, d.user_id, { allowFallback: false });

    await loadClientSwitcher(d);
    updateSparkline();
    updateToastFeed();
    loadAriaOverviewWidgets();
    loadUserProfile();
}

// ── Welcome Modal Functions ─────────────────────────────────────────────
function openWelcomeModal() {
    const modal = document.getElementById('welcomeModal');
    if (modal) {
        modal.hidden = false;
        document.body.style.overflow = 'hidden';
    }
}

function closeWelcomeModal() {
    const modal = document.getElementById('welcomeModal');
    if (modal) {
        modal.hidden = true;
        document.body.style.overflow = '';
    }
}

function switchWelcomeTab(tabName, btn) {
    // Hide all tab contents
    document.querySelectorAll('.welcome-tab-content').forEach(el => {
        el.classList.remove('active');
    });
    
    // Remove active from all buttons
    document.querySelectorAll('.welcome-tab-btn').forEach(el => {
        el.classList.remove('active');
    });
    
    // Show selected tab
    const tab = document.getElementById(`welcome-tab-${tabName}`);
    if (tab) tab.classList.add('active');
    
    // Mark button as active
    if (btn) btn.classList.add('active');
}

async function loadWelcomeUpdates() {
    try {
        const updatesList = document.getElementById('welcomeUpdatesList');
        if (!updatesList) return;
        
        // Try to get recent commits/updates from the API or fallback
        const updates = [
            { title: 'Live Chat Support', desc: 'Real-time admin dashboard messaging system' },
            { title: 'Dashboard Fixes', desc: 'Profile pictures, notifications, and stats improvements' },
            { title: 'Token Help Page', desc: 'Device-specific instructions for getting your token' },
            { title: 'Boost Management', desc: 'Enhanced boost tracking and analytics' },
            { title: 'Command System', desc: 'Improved command execution and error handling' }
        ];
        
        updatesList.innerHTML = updates.map((u, idx) => `
            <div class="update-item">
                <div class="update-badge">${idx + 1}</div>
                <div class="update-info">
                    <div class="update-version">${u.title}</div>
                    <div class="update-desc">${u.desc}</div>
                </div>
            </div>
        `).join('');
    } catch (e) {
        console.error('[Welcome] Load updates error:', e);
    }
}

function updateWelcomeVersion(version) {
    const verEl = document.getElementById('welcomeVersion');
    if (verEl && version) {
        verEl.textContent = version;
    }
}

async function loadAriaOverviewWidgets() {
    const [summaryRes, sysRes] = await Promise.all([
        fetchJSON('/api/max/system-summary'),
        fetchJSON('/api/max/system-stats'),
    ]);

    // Update fleet snapshot timestamp
    const timeEl = document.getElementById('fleetSnapshotTime');
    if (timeEl) {
        const now = new Date();
        timeEl.textContent = `Updated ${now.toLocaleTimeString('en-US', {hour: '2-digit', minute: '2-digit', second: '2-digit'})}`;
    }

    if (summaryRes && summaryRes.ok && summaryRes.summary) {
        const s = summaryRes.summary;
        setText('ariaHostedTotal', s.hosted_total ?? 0);
        setText('ariaHostedActive', s.hosted_active ?? 0);
        setText('ariaRegisteredUsers', s.users_registered ?? 0);
        setText('ariaSuccessRate', `${Number(s.success_rate || 0).toFixed(1)}%`);
        setText('ariaLatency', `${Math.round(Number(s.avg_response_ms || 0))}ms`);
        setText('ariaCommands', s.total_commands ?? 0);
    }

    if (sysRes && sysRes.ok) {
        const cpu = Number(sysRes.cpu || 0);
        const ram = Number(sysRes.ram || 0);
        const disk = Number(sysRes.disk || 0);
        const sentKb = Math.round(Number((sysRes.net || {}).sent || 0) / 1024);
        const recvKb = Math.round(Number((sysRes.net || {}).recv || 0) / 1024);

        setText('ariaCpu', `${cpu.toFixed(1)}%`);
        setText('ariaRam', `${ram.toFixed(1)}%`);
        setText('ariaDisk', `${disk.toFixed(1)}%`);
        setText('ariaNet', `up ${sentKb}kb | down ${recvKb}kb`);

        const badge = document.getElementById('infraHealthBadge');
        if (badge) {
            const maxUse = Math.max(cpu, ram, disk);
            if (maxUse >= 90) {
                badge.textContent = 'critical';
            } else if (maxUse >= 75) {
                badge.textContent = 'elevated';
            } else {
                badge.textContent = 'healthy';
            }
        }
    }
}

// ── Uptime Ring ────────────────────────────────────────────────────────────
function updateUptimeRing(uptimeStr) {
    // Parse uptime string like "1h 23m 45s"
    let total = 0;
    if (typeof uptimeStr === 'string') {
        const m = uptimeStr.match(/(?:(\d+)h)?\s*(?:(\d+)m)?\s*(?:(\d+)s)?/);
        if (m) {
            total += (parseInt(m[1]||'0',10)||0) * 3600;
            total += (parseInt(m[2]||'0',10)||0) * 60;
            total += (parseInt(m[3]||'0',10)||0);
        }
    }
    // Animate ring: 24h = full circle
    const max = 24*3600;
    const pct = Math.min(1, total / max);
    const offset = 151 - Math.round(151 * pct);
    const fg = document.querySelector('.uptime-fg');
    if (fg) fg.setAttribute('stroke-dashoffset', offset);
}

// ── Sparkline Chart ─────────────────────────────────────────────────────---
async function updateSparkline() {
    const canvas = document.getElementById('sparkline');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0,0,canvas.width,canvas.height);
    // Fetch history
    const res = await fetchJSON('/api/history');
    let entries = (res && res.data && res.data.entries) || [];
    // Group by minute
    const now = Date.now();
    const buckets = Array(20).fill(0);
    entries.forEach(e => {
        let ts = Number(e.timestamp || 0);
        if (!ts || ts > 1e12) ts = Math.floor(ts/1000); // handle ms
        const minAgo = Math.floor((now/1000 - ts)/60);
        if (minAgo >= 0 && minAgo < 20) buckets[19-minAgo]++;
    });
    // Draw sparkline
    const maxVal = Math.max(1, ...buckets);
    ctx.beginPath();
    for (let i=0; i<buckets.length; ++i) {
        const x = 7 + i*6.5;
        const y = 32 - (buckets[i]/maxVal)*28;
        if (i===0) ctx.moveTo(x,y);
        else ctx.lineTo(x,y);
    }
    ctx.strokeStyle = '#accbee';
    ctx.lineWidth = 2.2;
    ctx.shadowColor = '#7fafd6';
    ctx.shadowBlur = 4;
    ctx.stroke();
    ctx.shadowBlur = 0;
    // Fill area
    ctx.lineTo(7+19*6.5,32);
    ctx.lineTo(7,32);
    ctx.closePath();
    ctx.globalAlpha = 0.18;
    ctx.fillStyle = '#accbee';
    ctx.fill();
    ctx.globalAlpha = 1;
}

// ── Toast Feed ─────────────────────────────────────────────────────────---
async function updateToastFeed() {
    const feed = document.getElementById('toastFeed');
    if (!feed) return;
    const res = await fetchJSON('/api/dash/activity');
    let timeline = (res && res.timeline) || [];
    feed.innerHTML = '';
    timeline.slice(-8).reverse().forEach(ev => {
        const t = document.createElement('div');
        t.className = 'toast';
        t.textContent = `[${fmtTs(ev.ts)}] ${ev.action}${ev.details ? ': '+ev.details : ''}`;
        feed.appendChild(t);
    });
}

// ── Live Metrics Refresh ─────────────────────────────────────────────────-
setInterval(() => {
    if (document.getElementById('section-overview')?.classList.contains('active')) {
        updateSparkline();
        updateToastFeed();
        // Optionally, update uptime ring
        const uptime = document.getElementById('uptime');
        if (uptime) updateUptimeRing(uptime.textContent);
    }
}, 7000);

function animateMetricValue(id, newVal, decimals = 0) {
    const el = document.getElementById(id);
    if (!el) return;
    const prev = Number(el.dataset.value || 0);
    const next = Number(newVal || 0);
    const duration = 420;
    const start = performance.now();
    const isInt = decimals === 0;

    function tick(now) {
        const p = Math.min(1, (now - start) / duration);
        const eased = 1 - Math.pow(1 - p, 3);
        const cur = prev + (next - prev) * eased;
        el.textContent = isInt ? String(Math.round(cur)) : cur.toFixed(decimals);
        if (p < 1) requestAnimationFrame(tick);
        else el.dataset.value = String(next);
    }
    requestAnimationFrame(tick);
}

function updateLiveOverviewMetrics(botData) {
    const cmdCount = Number(botData.command_count || 0);
    const now = Date.now();

    let delta = 0;
    let perMin = 0;
    if (_liveOverviewState.lastCount != null && _liveOverviewState.lastTs != null) {
        delta = Math.max(0, cmdCount - _liveOverviewState.lastCount);
        const mins = Math.max((now - _liveOverviewState.lastTs) / 60000, 0.001);
        perMin = delta / mins;
    }

    _liveOverviewState.lastCount = cmdCount;
    _liveOverviewState.lastTs = now;

    animateMetricValue('liveCmdRate', perMin, 1);
    animateMetricValue('liveCmdDelta', delta, 0);

    const rateBar = document.getElementById('liveCmdRateBar');
    const deltaBar = document.getElementById('liveCmdDeltaBar');
    if (rateBar) rateBar.style.width = Math.min(100, Math.round(perMin * 8)) + '%';
    if (deltaBar) deltaBar.style.width = Math.min(100, Math.round(delta * 12)) + '%';

    const pulse = document.getElementById('livePulse');
    const pulseLabel = document.getElementById('livePulseLabel');
    if (pulse) pulse.classList.toggle('live', !!botData.connected);
    if (pulseLabel) pulseLabel.textContent = botData.connected ? 'live stream' : 'offline';

    const clock = document.getElementById('liveClock');
    if (clock) {
        const d = new Date();
        const hh = String(d.getHours()).padStart(2, '0');
        const mm = String(d.getMinutes()).padStart(2, '0');
        const ss = String(d.getSeconds()).padStart(2, '0');
        clock.textContent = `${hh}:${mm}:${ss}`;
    }
}

async function loadClientSwitcher(overviewData = null) {
    const select = document.getElementById('clientTypeSelect');
    if (!select) return;

    let data = overviewData;
    if (!data) {
        const res = await fetchJSON('/api/client');
        if (!res || !res.ok) return;
        data = res;
    }

    const current = String(data.client_type || 'mobile');
    const available = Array.isArray(data.available_clients) && data.available_clients.length
        ? data.available_clients
        : ['web', 'desktop', 'mobile', 'vr'];

    select.innerHTML = available.map(c => `<option value="${esc(c)}">${esc(c)}</option>`).join('');
    select.value = available.includes(current) ? current : available[0];
}

function showClientMsg(msg, ok) {
    const el = document.getElementById('clientMsg');
    if (!el) return;
    el.textContent = msg;
    el.className = 'settings-msg ' + (ok ? 'ok' : 'err');
    setTimeout(() => { el.textContent = ''; el.className = 'settings-msg'; }, 2800);
}

async function applyClientType() {
    const select = document.getElementById('clientTypeSelect');
    if (!select) return;
    const clientType = String(select.value || '').trim();
    if (!clientType) return;

    const res = await postJSON('/api/client', { client_type: clientType });
    if (res && res.ok) {
        showClientMsg(`Client switched to ${res.client_type}`, true);
        trackDashboardAction('client_switch', `Switched client to ${res.client_type}`);
        loadOverview();
    } else {
        showClientMsg((res && res.error) || 'Failed to switch client', false);
    }
}

// ── Commands ─────────────────────────────────────────────────────────────────
let _allCommands = [];

async function loadCommands() {
    const res = await fetchJSON('/api/commands');
    if (!res || !res.data) return;
    _allCommands = res.data.commands || [];
    setText('cmdCountLabel', _allCommands.length + ' commands');
    renderCommands(_allCommands);
}

function renderCommands(list) {
    const tbody = document.getElementById('commandsBody');
    const badge = document.getElementById('cmdBadge');
    if (badge) badge.textContent = list.length + (list.length === 1 ? ' command' : ' commands');
    if (!tbody) return;
    if (!list || list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="empty-row">No commands found</td></tr>';
        return;
    }
    tbody.innerHTML = list.map(c =>
        `<tr>
            <td class="cmd-name">${esc(c.name)}</td>
            <td class="cmd-aliases">${c.aliases && c.aliases.length ? esc(c.aliases.join(', ')) : '<span style="color:var(--muted)">—</span>'}</td>
            <td style="color:var(--muted)">${esc(c.description || '—')}</td>
            <td style="text-align:right;font-weight:700">${Number(c.recent_usage || 0)}</td>
        </tr>`
    ).join('');
}

// live search
document.addEventListener('DOMContentLoaded', () => {
    const searchEl = document.getElementById('cmdSearch');
    if (searchEl) {
        searchEl.addEventListener('input', () => {
            const q = searchEl.value.toLowerCase().trim();
            if (!q) { renderCommands(_allCommands); return; }
            renderCommands(_allCommands.filter(c =>
                c.name.toLowerCase().includes(q) ||
                (c.aliases || []).some(a => a.toLowerCase().includes(q)) ||
                (c.description || '').toLowerCase().includes(q)
            ));
        });
    }
});

// ── Analytics ─────────────────────────────────────────────────────────────────
async function loadAnalytics() {
    const res = await fetchJSON('/api/analytics');
    if (!res || !res.data) return;
    const d = res.data;
    setText('totalCommands', d.total_commands ?? 0);
    countUp('totalCommands', d.total_commands ?? 0, 800);
    setText('successRate', (d.success_rate ?? 100) + '%');
    setText('avgResponseMs', (d.avg_response_ms ?? 0) + 's');

    const wrap = document.getElementById('topCommandsBody');
    if (!wrap) return;
    if (!d.top_commands || d.top_commands.length === 0) {
        wrap.innerHTML = '<div class="empty-row" style="padding:32px 20px">No command data yet</div>';
        return;
    }
    const maxCount = d.top_commands[0].count || 1;
    wrap.innerHTML = d.top_commands.map((c, i) => {
        const pct = Math.round((c.count / maxCount) * 100);
        const rankClass = i === 0 ? 'top-cmd-rank gold' : 'top-cmd-rank';
        return `<div class="top-cmd-row">
            <div class="${rankClass}">${i + 1}</div>
            <div class="top-cmd-name">${esc(c.name)}</div>
            <div class="top-cmd-bar-wrap"><div class="top-cmd-bar" style="width:${pct}%"></div></div>
            <div class="top-cmd-count">${c.count}</div>
        </div>`;
    }).join('');
}

// ── History ───────────────────────────────────────────────────────────────────
async function loadHistory() {
    const res = await fetchJSON('/api/history');
    if (!res || !res.data) return;
    const d = res.data;
    const badge = document.getElementById('historyBadge');
    if (badge) badge.textContent = (d.total ?? 0) + ' entries';

    const feed = document.getElementById('historyFeed');
    if (!feed) return;
    if (!d.entries || d.entries.length === 0) {
        feed.innerHTML = '<div class="log-loading">No history entries yet — Run some commands!</div>';
        return;
    }
    feed.innerHTML = d.entries.slice().reverse().map(e => {
        if (typeof e === 'object' && e !== null) {
            // Improved command name resolution with multiple fallback paths
            const cmd = String(e.command || e.cmd || e.name || e.op || '').trim() || '(unknown)';
            const user = e.user || e.author || e.author_id || e.username || '';
            const guild = e.guild_id || e.guild || e.server || '';
            const chan  = e.channel_id || e.channel || '';
            let ts    = e.timestamp || e.time || '';
            
            // Format timestamp if it's a unix number
            if (ts && !isNaN(ts)) {
                try {
                    ts = new Date(Number(ts) * 1000).toLocaleTimeString('en-US', {hour: '2-digit', minute: '2-digit', second: '2-digit'});
                } catch (ex) {
                    ts = String(ts);
                }
            } else {
                ts = String(ts || '');
            }
            
            const status = e.status || e.result || '';
            const dur = e.duration_ms != null ? `${Math.round(Number(e.duration_ms) || 0)}ms` : '';
            const statusBadge = status === 'success' || status === 'ok'
                ? '<span class="badge badge-ok">ok</span>'
                : status ? `<span class="badge badge-warn">${esc(status)}</span>` : '';
            return `<div class="history-item">
                <div class="history-dot"></div>
                <div class="history-content">
                    <span class="history-cmd">${esc(cmd)}</span>
                    ${statusBadge}
                    <div class="history-meta">${[
                        user  ? '👤 ' + esc(String(user)) : '',
                        guild ? '🏠 ' + esc(String(guild)) : '',
                        chan  ? '# ' + esc(String(chan))   : '',
                        ts   ? '🕐 ' + esc(ts)    : '',
                        dur  ? '⚡ ' + dur   : ''
                    ].filter(Boolean).join(' &nbsp;·&nbsp; ')}</div>
                </div>
            </div>`;
        }
        return `<div class="history-item"><div class="history-dot"></div><div class="history-content"><div class="history-raw">${esc(String(e))}</div></div></div>`;
    }).join('');
}

// ── Boost ─────────────────────────────────────────────────────────────────────

async function loadBoost() {
    const res = await fetchJSON('/api/boost');
    if (!res || !res.data) return;
    const data = res.data;
    const live = data.live || {};
    const total = Number(live.total_slots) || 0;
    const used  = Number(live.slots_used)  || 0;
    const cd    = Number(live.slots_cooldown) || 0;
    const avail = Number(live.slots_available) || 0;

    setText('boostTotalSlots',     total  || '—');
    setText('boostSlotsAvail',     avail  || '—');
    setText('boostSlotsUsed',      used   || '—');
    setText('boostSlotsCd',        cd     || '—');
    setText('boostTracked',        live.tracked_servers   ?? '—');
    setText('boostBoostedServers', live.boosted_servers   ?? '—');
    setText('boostTotalOut',       live.total_boosts      ?? '—');
    setText('boostStatusText',     live.status            || '—');

    // Visual slot bar
    const pct   = total ? Math.round((used / total) * 100) : 0;
    const cdPct = total ? Math.round((cd   / total) * 100) : 0;
    setText('boostSlotPct', pct + '%');
    const fill   = document.getElementById('boostSlotFill');
    const cdFill = document.getElementById('boostSlotCdFill');
    if (fill)   fill.style.width   = pct + '%';
    if (cdFill) { cdFill.style.width = cdPct + '%'; cdFill.style.left = pct + '%'; }

}

// ── Help / Token Guide ───────────────────────────────────────────────────────
function loadHelp() {
    // Just make sure the content is visible
    const section = document.getElementById('section-help');
    if (section) {
        // Reset tabs to show desktop by default
        const tabs = section.querySelectorAll('.help-tab-content');
        tabs.forEach(tab => tab.classList.remove('active'));
        const desktopTab = document.getElementById('help-tab-desktop');
        if (desktopTab) desktopTab.classList.add('active');
        
        const tabBtns = section.querySelectorAll('.help-tab-btn');
        tabBtns.forEach(btn => btn.classList.remove('active'));
        if (tabBtns[0]) tabBtns[0].classList.add('active');
    }
    trackDashboardAction('view_help', 'Opened help guide');
}

function switchHelpTab(tabName, btn) {
    // Hide all tabs
    const tabContents = document.querySelectorAll('.help-tab-content');
    tabContents.forEach(tab => tab.classList.remove('active'));
    
    // Deactivate all buttons
    const tabBtns = document.querySelectorAll('.help-tab-btn');
    tabBtns.forEach(b => b.classList.remove('active'));
    
    // Show selected tab
    const selectedTab = document.getElementById(`help-tab-${tabName}`);
    if (selectedTab) selectedTab.classList.add('active');
    
    // Activate button
    if (btn) btn.classList.add('active');
    
    trackDashboardAction('help_tab_switch', `Switched help tab to ${tabName}`);
}

function copyToClipboard(elementRef) {
    const codeElement = typeof elementRef === 'string'
        ? document.getElementById(elementRef)
        : elementRef;
    if (!codeElement) return;
    
    const code = codeElement.textContent;
    navigator.clipboard.writeText(code).then(() => {
        showToast('Copied', 'Code copied to clipboard!', 'ok');
    }).catch(() => {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = code;
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            showToast('Copied', 'Code copied to clipboard!', 'ok');
        } catch (err) {
            showToast('Copy Failed', 'Could not copy to clipboard', 'err');
        }
        document.body.removeChild(textarea);
    });
}

// ── Settings ─────────────────────────────────────────────────────────────────
async function loadSettings() {
    const res = await fetchJSON('/api/config');
    if (!res || !res.data) return;
    const d = res.data;
    setText('cfgPrefix', d.prefix);
    setText('cfgAutoDelete', d.auto_delete_enabled ? 'Enabled' : 'Disabled');
    setText('cfgDelay', d.auto_delete_delay + 's');
    setText('cfgStatus', d.status || 'online');

    const tog = document.getElementById('newAutoDeleteToggle');
    if (tog) tog.value = d.auto_delete_enabled ? 'true' : 'false';
}

function showSettingsMsg(msg, ok) {
    const el = document.getElementById('settingsMsg');
    if (!el) return;
    el.textContent = msg;
    el.className = 'settings-msg ' + (ok ? 'ok' : 'err');
    setTimeout(() => { el.textContent = ''; el.className = 'settings-msg'; }, 3000);
}

async function applyPrefix() {
    const val = document.getElementById('newPrefixInput').value.trim();
    if (!val) { showSettingsMsg('Enter a prefix first.', false); return; }
    const res = await postJSON('/api/config', { prefix: val });
    if (res && res.ok) {
        showSettingsMsg('Prefix updated to: ' + res.data.prefix, true);
        showToast('Prefix Updated', `New prefix: ${res.data.prefix}`, 'ok');
        trackDashboardAction('config_prefix', `Updated prefix to ${res.data.prefix}`);
        loadSettings();
        loadOverview();
    } else {
        showSettingsMsg('Failed to update prefix.', false);
        showToast('Update Failed', 'Could not update prefix', 'err');
    }
}

async function applyDelay() {
    const val = parseInt(document.getElementById('newDelayInput').value);
    if (isNaN(val) || val < 1) { showSettingsMsg('Enter a valid delay (1–600).', false); return; }
    const res = await postJSON('/api/config', { auto_delete_delay: val });
    if (res && res.ok) {
        showSettingsMsg('Delay updated to: ' + res.data.auto_delete_delay + 's', true);
        showToast('Delay Updated', `Auto-delete: ${res.data.auto_delete_delay}s`, 'ok');
        trackDashboardAction('config_delay', `Updated auto-delete delay to ${res.data.auto_delete_delay}s`);
        loadSettings();
    } else {
        showSettingsMsg('Failed to update delay.', false);
        showToast('Update Failed', 'Could not update delay', 'err');
    }
}

async function applyAutoDelete() {
    const val = document.getElementById('newAutoDeleteToggle').value === 'true';
    const res = await postJSON('/api/config', { auto_delete_enabled: val });
    if (res && res.ok) {
        showSettingsMsg('Auto-delete ' + (val ? 'enabled' : 'disabled'), true);
        trackDashboardAction('config_autodelete', `Set auto-delete ${val ? 'enabled' : 'disabled'}`);
        loadSettings();
    } else {
        showSettingsMsg('Failed to update.', false);
    }
}

// ── Help Modal Functions ──────────────────────────────────────────────────
function openHelpModal() {
    const modal = document.getElementById('helpModal');
    if (modal) {
        modal.removeAttribute('hidden');
        document.body.style.overflow = 'hidden';
    }
}

function closeHelpModal() {
    const modal = document.getElementById('helpModal');
    if (modal) {
        modal.setAttribute('hidden', '');
        document.body.style.overflow = '';
    }
}

function switchHelpTab(tabName, btn) {
    const tabContents = document.querySelectorAll('.help-tab-content');
    tabContents.forEach(tab => tab.classList.remove('active'));
    const tabBtns = document.querySelectorAll('.help-tab-btn');
    tabBtns.forEach(b => b.classList.remove('active'));
    const selectedTab = document.getElementById(`help-tab-${tabName}`);
    if (selectedTab) selectedTab.classList.add('active');
    if (btn) btn.classList.add('active');
}

function copyToClipboard(elementRef) {
    const codeElement = typeof elementRef === 'string'
        ? document.getElementById(elementRef)
        : elementRef;
    if (!codeElement) return;
    const code = codeElement.textContent;
    navigator.clipboard.writeText(code).then(() => {
        showToast('Copied', 'Code copied!', 'ok');
    }).catch(() => {
        const textarea = document.createElement('textarea');
        textarea.value = code;
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            showToast('Copied', 'Code copied!', 'ok');
        } catch (err) {
            showToast('Error', 'Copy failed', 'err');
        }
        document.body.removeChild(textarea);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    const menuBtn = document.getElementById('topbarMenuBtn');
    const menuDropdown = document.getElementById('topbarMenuDropdown');
    if (menuBtn && menuDropdown) {
        menuBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            menuDropdown.hasAttribute('hidden') ? menuDropdown.removeAttribute('hidden') : menuDropdown.setAttribute('hidden', '');
        });
        document.addEventListener('click', () => menuDropdown.setAttribute('hidden', ''));
    }
});

// ── Section router ────────────────────────────────────────────────────────────
function loadSection(name) {
    if (name === 'overview')  loadOverview();
    if (name === 'owner')     loadOwnerPanel();
    if (name === 'commands')  loadCommands();
    if (name === 'analytics') loadAnalytics();
    if (name === 'history')   loadHistory();
    if (name === 'logger')    loadMessageLogger();
    if (name === 'boost')     loadBoost();
    if (name === 'rpc')       loadRpc();
    if (name === 'presence')  loadPresence();
    if (name === 'hosted')    loadHosted();
    if (name === 'logs')      loadLogs();
    if (name === 'users')     loadDashUsers();
    if (name === 'settings')  loadSettings();
    if (name === 'chat')      loadChat();
    if (name === 'system')    loadSystemStats();
    if (name === 'cmdbreakdown') loadCommandBreakdown();
    if (name === 'errors')    loadErrorLogs();
    if (name === 'leaderboard') loadLeaderboard();
    if (name === 'serverinfo') loadServerInfo();
    if (name === 'activitymap') loadActivityMap();
    if (name === 'notifications') loadNotifications();
    if (name === 'advanced-analytics') loadAdvancedAnalytics();
    if (name === 'widgets')   loadWidgets();
}

// ── Maximalist Dashboard Panel Loaders ─────────────────────────────────────
async function loadSystemStats() {
    const res = await fetchJSON('/api/max/system-stats');
    setText('cpuUsage', res && res.cpu != null ? res.cpu + '%' : '—');
    setText('ramUsage', res && res.ram != null ? res.ram + '%' : '—');
    setText('diskUsage', res && res.disk != null ? res.disk + '%' : '—');
    setText('netUsage', res && res.net ? `↑${Math.round(res.net.sent/1024)}KB ↓${Math.round(res.net.recv/1024)}KB` : '—');
    // Timeline chart (placeholder: random walk)
    const canvas = document.getElementById('resourceTimeline');
    if (canvas) {
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0,0,canvas.width,canvas.height);
        ctx.beginPath();
        for (let i=0; i<56; ++i) {
            const y = 50 + 8*Math.sin(i/3 + Date.now()/4000);
            ctx.lineTo(10+i*10, y);
        }
        ctx.strokeStyle = '#06b6d4';
        ctx.lineWidth = 2.2;
        ctx.stroke();
    }
}

async function loadCommandBreakdown() {
    const res = await fetchJSON('/api/max/command-breakdown');
    // Pie chart
    const pie = document.getElementById('cmdPie');
    if (pie && res && res.pie) {
        const ctx = pie.getContext('2d');
        ctx.clearRect(0,0,pie.width,pie.height);
        const data = res.pie;
        const total = data.reduce((a,b)=>a+b.count,0)||1;
        let start = 0;
        data.forEach((c,i) => {
            const val = c.count/total;
            ctx.beginPath();
            ctx.moveTo(130,90);
            ctx.arc(130,90,80,start,start+val*2*Math.PI);
            ctx.closePath();
            ctx.fillStyle = ['#8b5cf6','#ec4899','#06b6d4','#10b981','#f59e0b','#ef4444'][i%6];
            ctx.fill();
            start += val*2*Math.PI;
        });
    }
    // Bar chart
    const bar = document.getElementById('cmdBar');
    if (bar && res && res.bar) {
        const ctx = bar.getContext('2d');
        ctx.clearRect(0,0,bar.width,bar.height);
        const cats = Object.entries(res.bar);
        const max = Math.max(1, ...cats.map(c=>c[1]));
        cats.forEach((c,i) => {
            ctx.fillStyle = ['#8b5cf6','#ec4899','#06b6d4','#10b981','#f59e0b','#ef4444'][i%6];
            ctx.fillRect(30+i*50, 170-(c[1]/max)*140, 36, (c[1]/max)*140);
            ctx.fillStyle = '#fff';
            ctx.font = '13px sans-serif';
            ctx.fillText(c[0], 30+i*50, 175);
        });
    }
}

async function loadErrorLogs() {
    const res = await fetchJSON('/api/max/errors');
    const feed = document.getElementById('errorFeed');
    if (!feed) return;
    if (!res || !res.errors || res.errors.length === 0) {
        feed.innerHTML = '<div class="log-loading">No errors found.</div>';
        return;
    }
    feed.innerHTML = res.errors.slice().reverse().map(e => `<div class="history-item"><div class="history-dot"></div><div class="history-content"><div class="history-raw">${esc(e)}</div></div></div>`).join('');
}

async function loadLeaderboard() {
    const res = await fetchJSON('/api/max/leaderboard');
    const tbody = document.getElementById('leaderboardBody');
    if (!tbody) return;
    if (!res || !res.leaderboard || res.leaderboard.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3">No data</td></tr>';
        return;
    }
    tbody.innerHTML = res.leaderboard.map(u => `<tr><td>${esc(u.username)}</td><td>${u.count}</td><td>${fmtTs(u.last_seen_at)}</td></tr>`).join('');
}

async function loadServerInfo() {
    const res = await fetchJSON('/api/max/server-info');
    const g = res && res.guild || {};
    setText('guildName', g.name || '—');
    setText('guildId', g.id || '—');
    setText('guildMembers', g.members || '—');
    setText('guildRegion', g.region || '—');
}

async function loadActivityMap() {
    const res = await fetchJSON('/api/max/activity-map');
    // Timeline
    const timeline = res && res.timeline || [];
    const tcanvas = document.getElementById('activityTimeline');
    if (tcanvas) {
        const ctx = tcanvas.getContext('2d');
        ctx.clearRect(0,0,tcanvas.width,tcanvas.height);
        ctx.beginPath();
        timeline.forEach((v,i) => {
            const x = 20+i*24;
            const y = 50-(v/Math.max(1,...timeline))*40;
            if (i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
        });
        ctx.strokeStyle = '#f59e0b';
        ctx.lineWidth = 2.2;
        ctx.stroke();
    }
    // Heatmap
    const heatmap = res && res.heatmap || [];
    const hcanvas = document.getElementById('activityHeatmap');
    if (hcanvas) {
        const ctx = hcanvas.getContext('2d');
        ctx.clearRect(0,0,hcanvas.width,hcanvas.height);
        for (let h=0; h<24; ++h) for (let d=0; d<7; ++d) {
            const v = heatmap[h] && heatmap[h][d] || 0;
            ctx.fillStyle = `rgba(139,92,246,${0.08+0.7*(v/Math.max(1,...heatmap.flat()))})`;
            ctx.fillRect(20+d*80, 5+h*5, 70, 4);
        }
    }
}

// ── Discord notification center ───────────────────────────────────────────────

const NOTIF_ICONS = {
    dm:             '✉️',
    mention:        '🔔',
    friend_request: '👋',
    friend_accept:  '✅',
    friend_remove:  '👤',
    guild_join:     '🏠',
    guild_remove:   '🚪',
    ban:            '🔨',
    unban:          '🔓',
    pin:            '📌',
    reaction:       '❤️',
    call:           '📞',
    system:         '⚙️',
};

const NOTIF_COLORS = {
    dm:             '#accbee',
    mention:        '#f59e0b',
    friend_request: '#67e8f9',
    friend_accept:  '#86efac',
    friend_remove:  '#94a3b8',
    guild_join:     '#86efac',
    guild_remove:   '#ef4444',
    ban:            '#ef4444',
    unban:          '#86efac',
    pin:            '#accbee',
    reaction:       '#ec4899',
    call:           '#67e8f9',
    system:         '#94a3b8',
};

async function loadNotifications() {
    // Legacy feed on Notifications section page
    const feed = document.getElementById('notificationFeed');
    if (!feed) return;
    let res = await fetchJSON('/api/discord/notifications');
    if (!res || !res.ok) {
        const fallback = await fetchJSON('/api/max/notifications');
        const events = (fallback && fallback.ok && Array.isArray(fallback.events))
            ? fallback.events.map(e => ({
                title: e.action || 'Activity',
                body: e.details || '',
                author: e.user || '',
                ts: Number(e.ts || 0),
                kind: 'system',
                icon: '⚙️',
            }))
            : [];
        res = { ok: true, notifications: events };
    }
    if (!res || !res.notifications || !res.notifications.length) {
        feed.innerHTML = '<div class="log-loading">No Discord notifications yet.</div>';
        return;
    }
    feed.innerHTML = res.notifications.map(n => {
        const icon = n.icon || NOTIF_ICONS[n.kind] || '🔔';
        const color = NOTIF_COLORS[n.kind] || 'var(--a2)';
        const sub = [n.author, n.guild_id ? `Server ${n.guild_id}` : ''].filter(Boolean).join(' · ');
        return `<div class="history-item">
            <div class="history-dot" style="background:${color}"></div>
            <div class="history-content">
                <span class="history-cmd">${icon} ${esc(n.title)}</span>
                <div class="history-meta">${esc(sub)} · ${relativeTime(n.ts)}</div>
                ${n.body ? `<div class="history-raw">${esc(n.body)}</div>` : ''}
            </div>
        </div>`;
    }).join('');
}

async function refreshNotificationCenter() {
    const bellBadge = document.getElementById('bellBadge');
    const bell      = document.getElementById('topbarBell');
    const list      = document.getElementById('notificationCenterList');
    if (!bellBadge || !bell || !list) return;

    let res = await fetchJSON('/api/discord/notifications');
    if (!res || !res.ok) {
        const fallback = await fetchJSON('/api/max/notifications');
        const events = (fallback && fallback.ok && Array.isArray(fallback.events))
            ? fallback.events.map(e => ({
                title: e.action || 'Activity',
                body: e.details || '',
                author: e.user || '',
                ts: Number(e.ts || 0),
                kind: 'system',
                icon: '⚙️',
                read: false,
            }))
            : [];
        res = { ok: true, notifications: events };
    }
    const notifs = (res && res.ok && Array.isArray(res.notifications)) ? res.notifications : [];
    _notificationState.events = notifs;

    const unread = notifs.filter(n => !n.read && n.ts > Number(_notificationState.seenTs || 0));
    bellBadge.textContent   = String(unread.length || '');
    bellBadge.style.display = unread.length ? 'inline-flex' : 'none';
    bell.classList.toggle('has-unread', unread.length > 0);

    if (!notifs.length) {
        list.innerHTML = '<div class="notification-empty">No Discord notifications yet.</div>';
        return;
    }

    list.innerHTML = notifs.map(n => {
        const isUnread = !n.read && n.ts > Number(_notificationState.seenTs || 0);
        const icon  = n.icon || NOTIF_ICONS[n.kind] || '🔔';
        const color = NOTIF_COLORS[n.kind] || 'var(--a2)';
        const meta  = [n.author, n.guild_id ? 'Server' : (n.channel_id ? 'DM' : '')].filter(Boolean).join(' · ');
        return `<div class="notification-item ${isUnread ? 'unread' : ''}" style="${isUnread ? `border-left:2px solid ${color}` : ''}">
            <div class="notification-item-head">
                <span class="notification-action">${icon} ${esc(n.title)}</span>
                <span class="notification-time">${relativeTime(n.ts)}</span>
            </div>
            ${meta ? `<div class="notification-meta">${esc(meta)}</div>` : ''}
            ${n.body ? `<div class="notification-details">${esc(n.body)}</div>` : ''}
        </div>`;
    }).join('');
}

function markNotificationsSeen() {
    const maxTs = _notificationState.events.reduce(
        (m, n) => Math.max(m, Number(n.ts || 0)),
        Number(_notificationState.seenTs || 0)
    );
    _notificationState.seenTs = maxTs;
    // Mark read on server too
    fetch('/api/discord/notifications/mark_read', { method: 'POST', headers: {'Content-Type':'application/json'}, body: '{}' }).catch(() => {});
    refreshNotificationCenter();
}

function toggleNotificationCenter(forceState = null) {
    const panel = document.getElementById('notificationCenter');
    if (!panel) return;
    const next = forceState == null ? !_notificationState.open : !!forceState;
    _notificationState.open = next;
    panel.hidden = !next;
    if (next) {
        markNotificationsSeen();
    }
}

async function loadAdvancedAnalytics() {
    const res = await fetchJSON('/api/max/advanced-analytics');
    setText('advSuccessRate', res && res.success_rate != null ? res.success_rate+'%' : '—');
    setText('advAvgLatency', res && res.avg_latency != null ? res.avg_latency+'ms' : '—');
    setText('advFailures', res && res.failures != null ? res.failures : '—');
    setText('advLongestCmd', res && res.longest_cmd != null ? res.longest_cmd+'ms' : '—');
}

async function loadWidgets() {
    const grid = document.getElementById('widgetGrid');
    if (!grid) return;
    const res = await fetchJSON('/api/max/widgets');
    if (!res || !res.widgets) {
        grid.innerHTML = '<div class="log-loading">No widgets found.</div>';
        return;
    }
    grid.innerHTML = res.widgets.map(w => `<div class="widget-card">${esc(w.name)}</div>`).join('');
}

// ── RPC ───────────────────────────────────────────────────────────────────────
const RPC_TYPE_LABELS = ['Playing', 'Streaming', 'Listening to', 'Watching', '', 'Competing in'];
const DEFAULT_RPC_APPLICATION_ID = '1494507808329171096';
const RPC_DRAFT_STORAGE_KEY = 'aria_rpc_draft_v1';
let _rpcDraftRestored = false;

const RPC_APP_ID_BY_NAME = [
    { keys: ['spotify'], appId: '1494507808329171096' },
    { keys: ['crunchyroll', 'crunchy roll'], appId: '463097721130188830' },
    { keys: ['youtube music', 'yt music', 'youtube_music'], appId: '880218394199220334' },
    { keys: ['youtube', 'yt'], appId: '880218394199220334' },
    { keys: ['soundcloud', 'sound cloud'], appId: '195323574500409344' },
    { keys: ['netflix'], appId: '883483001462849607' },
    { keys: ['disneyplus', 'disney plus', 'disney+'], appId: '883483001462849607' },
    { keys: ['primevideo', 'prime video', 'amazon prime'], appId: '883483001462849607' },
    { keys: ['twitch'], appId: '488633707456348190' },
    { keys: ['kick'], appId: '1096876388377366548' },
    { keys: ['apple music', 'applemusic'], appId: '886578863147192350' },
    { keys: ['deezer'], appId: '356268235697553409' },
    { keys: ['tidal'], appId: '1041821781058760745' },
    { keys: ['plex'], appId: '910362402908213248' },
    { keys: ['jellyfin'], appId: '969748111193886730' },
    { keys: ['vscode', 'visual studio code', 'code'], appId: '383226320970055681' },
    { keys: ['valorant'], appId: '813612000139853844' },
    { keys: ['discord'], appId: '938956540159881230' },
];

function normalizeRpcActivityName(name) {
    return String(name || '').toLowerCase().replace(/[^a-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim();
}

function inferRpcAppIdFromName(name) {
    const normalized = normalizeRpcActivityName(name);
    if (!normalized) return DEFAULT_RPC_APPLICATION_ID;
    for (const entry of RPC_APP_ID_BY_NAME) {
        if (entry.keys.some(k => normalized.includes(k))) return entry.appId;
    }
    return DEFAULT_RPC_APPLICATION_ID;
}

function inferRpcAppIdFromActivity(name, details = '', state = '') {
    const blob = `${name || ''} ${details || ''} ${state || ''}`.trim();
    return inferRpcAppIdFromName(blob);
}

function resolveRpcPreviewImage(rawValue, applicationId = '') {
    const value = String(rawValue || '').trim();
    if (!value) return '';

    if (value.startsWith('http://') || value.startsWith('https://')) return value;

    const appId = String(applicationId || '').trim();

    // Common Discord RPC image key format (e.g. "large", "cover_art")
    // requires app id to resolve to app-assets CDN URL.
    if (!value.includes('/') && appId) {
        return `https://cdn.discordapp.com/app-assets/${appId}/${encodeURIComponent(value)}.png?size=256`;
    }

    const toCdnPath = (path) => {
        const clean = String(path || '').replace(/^\/+/, '');
        if (!clean) return '';
        if (clean.startsWith('attachments/')) return `https://media.discordapp.net/${clean}`;
        if (clean.startsWith('external/')) return `https://media.discordapp.net/${clean}`;
        if (clean.startsWith('app-assets/')) return `https://cdn.discordapp.com/${clean}`;
        return '';
    };

    if (value.startsWith('mp:')) {
        return toCdnPath(value.slice(3));
    }
    return toCdnPath(value);
}

function getRpcAppIdMode() {
    const mode = (document.getElementById('rpcAppIdMode')?.value || 'auto').toLowerCase();
    return mode === 'custom' ? 'custom' : 'auto';
}

function getEffectiveRpcAppId() {
    const mode = getRpcAppIdMode();
    const custom = (document.getElementById('rpcCustomAppIdInput')?.value || '').trim();
    const name = (document.getElementById('rpcNameInput')?.value || '').trim();
    const details = (document.getElementById('rpcDetailsInput')?.value || '').trim();
    const state = (document.getElementById('rpcStateInput')?.value || '').trim();
    if (mode === 'custom' && custom) return custom;
    return inferRpcAppIdFromActivity(name, details, state);
}

function syncRpcAppIdControls() {
    const customRow = document.getElementById('rpcCustomAppIdRow');
    if (customRow) customRow.style.display = getRpcAppIdMode() === 'custom' ? '' : 'none';
}

function syncRpcStreamingControls() {
    const typeVal = parseInt(document.getElementById('rpcType')?.value, 10) || 0;
    const row = document.getElementById('rpcStreamUrlRow');
    if (row) row.style.display = typeVal === 1 ? '' : 'none';
}

function readRpcDraftFromInputs() {
    const val = id => (document.getElementById(id)?.value || '').trim();
    return {
        type: String(parseInt(document.getElementById('rpcType')?.value, 10) || 0),
        name: val('rpcNameInput'),
        display_name: val('rpcDisplayNameInput'),
        details: val('rpcDetailsInput'),
        state: val('rpcStateInput'),
        streamUrl: val('rpcStreamUrlInput'),
        largeImage: val('rpcLargeImageInput'),
        smallImage: val('rpcSmallImageInput'),
        button1Label: val('rpcButton1Label'),
        button1Url: val('rpcButton1Url'),
        button2Label: val('rpcButton2Label'),
        button2Url: val('rpcButton2Url'),
        appIdMode: getRpcAppIdMode(),
        customAppId: val('rpcCustomAppIdInput'),
    };
}

function saveRpcDraft() {
    try {
        localStorage.setItem(RPC_DRAFT_STORAGE_KEY, JSON.stringify(readRpcDraftFromInputs()));
    } catch (_) {}
}

function applyRpcDraftToInputs(draft) {
    if (!draft || typeof draft !== 'object') return false;
    const setVal = (id, v) => {
        const el = document.getElementById(id);
        if (el) el.value = v != null ? String(v) : '';
    };
    setVal('rpcType', draft.type || '0');
    setVal('rpcNameInput', draft.name || '');
    setVal('rpcDisplayNameInput', draft.display_name || '');
    setVal('rpcDetailsInput', draft.details || '');
    setVal('rpcStateInput', draft.state || '');
    setVal('rpcStreamUrlInput', draft.streamUrl || '');
    setVal('rpcLargeImageInput', draft.largeImage || '');
    setVal('rpcSmallImageInput', draft.smallImage || '');
    setVal('rpcButton1Label', draft.button1Label || '');
    setVal('rpcButton1Url', draft.button1Url || '');
    setVal('rpcButton2Label', draft.button2Label || '');
    setVal('rpcButton2Url', draft.button2Url || '');
    setVal('rpcAppIdMode', draft.appIdMode === 'custom' ? 'custom' : 'auto');
    setVal('rpcCustomAppIdInput', draft.customAppId || '');
    syncRpcAppIdControls();
    syncRpcStreamingControls();
    return true;
}

function restoreRpcDraft() {
    try {
        const raw = localStorage.getItem(RPC_DRAFT_STORAGE_KEY);
        if (!raw) return false;
        const draft = JSON.parse(raw);
        return applyRpcDraftToInputs(draft);
    } catch (_) {
        return false;
    }
}

async function loadRpc() {
    loadRpcProfiles();
    const res = await fetchJSON('/api/rpc');
    if (!res) return;
    const active = res.active || false;
    const act    = res.activity || {};
    const assets = act.assets || {};

    // Active badge
    const badge = document.getElementById('rpcActiveBadge');
    if (badge) {
        badge.textContent = active ? 'Active' : 'Inactive';
        badge.className   = 'badge ' + (active ? 'badge-ok' : 'badge-off');
    }

    // Populate bot identity in card from cached bot data (if overview was loaded)
    const botUsername  = document.getElementById('rpcDiscordUsername');
    const botAvatarEl  = document.getElementById('rpcDiscordAvatar');
    const botStatusDot = document.getElementById('rpcDiscordStatusDot');
    const cachedBot = window._botDataCache || {};
    if (botUsername)  botUsername.textContent          = cachedBot.username  || 'Loading…';
    if (botAvatarEl) {
        const topbarSrc = document.getElementById('topbarAvatar')?.src || '';
        const rpcAvatar = String(cachedBot.avatar_url || topbarSrc || '').trim();
        setAvatarImage(botAvatarEl, rpcAvatar, cachedBot.user_id, { allowFallback: true });
    }
    if (botStatusDot) {
        botStatusDot.className = 'discord-user-dot';
        const s = cachedBot.status || 'online';
        if (s !== 'online') botStatusDot.classList.add(s);
    }

    // Custom status line
    setText('rpcDiscordCustomStatus', active ? (act.state || '') : '');

    // Activity type header
    const headerEl = document.querySelector('.discord-activity-header');
    if (headerEl) headerEl.textContent = RPC_ACTIVITY_HEADERS[act.type ?? 0] || 'Playing a game';

    // Activity text
    setText('rpcPreviewName',    active ? (act.name || '—') : '');
    setText('rpcPreviewDetails', active ? (act.details || '') : '');
    setText('rpcPreviewState',   active ? (act.state   || '') : '');

    // Large art
    const artEl = document.getElementById('rpcDiscordArt');
    if (artEl) {
        const li = resolveRpcPreviewImage(assets.large_image || '', act.application_id || getEffectiveRpcAppId());
        if (active && li) {
            artEl.style.backgroundImage  = `url("${String(li).replace(/"/g, '%22')}")`;
            artEl.style.backgroundSize   = 'cover';
            artEl.style.backgroundColor = 'transparent';
        } else {
            artEl.style.backgroundImage  = 'none';
            artEl.style.backgroundColor = 'var(--a1)';
        }
    }

    // Small art
    const smallArtEl = document.getElementById('rpcDiscordSmallArt');
    if (smallArtEl) {
        const si = resolveRpcPreviewImage(assets.small_image || '', act.application_id || getEffectiveRpcAppId());
        if (active && si) {
            smallArtEl.classList.add('visible');
            smallArtEl.style.backgroundImage = `url("${String(si).replace(/"/g, '%22')}")`;
            smallArtEl.style.backgroundSize  = 'cover';
            smallArtEl.style.backgroundColor = 'transparent';
        } else {
            smallArtEl.classList.remove('visible');
            smallArtEl.style.backgroundImage = 'none';
            smallArtEl.style.backgroundColor = 'var(--a1)';
        }
    }

    // Buttons
    const btnsEl = document.getElementById('rpcDiscordButtons');
    if (btnsEl) {
        const labels = Array.isArray(act.buttons) ? act.buttons.filter(Boolean) : [];
        btnsEl.innerHTML    = labels.map(l => `<div class="discord-btn">${esc(l)}</div>`).join('');
        btnsEl.style.display = labels.length ? '' : 'none';
    }

    // Progress bar (music/timestamps)
    const progressWrap = document.getElementById('rpcDiscordProgressWrap');
    const progressBar  = document.getElementById('rpcPreviewProgress');
    if (act.timestamps && act.timestamps.start && act.timestamps.end) {
        const now   = Date.now();
        const start = Number(act.timestamps.start) * 1000;
        const end   = Number(act.timestamps.end)   * 1000;
        const pct   = Math.max(0, Math.min(100, ((now - start) / Math.max(end - start, 1)) * 100));
        if (progressWrap) progressWrap.style.display = '';
        if (progressBar)  progressBar.style.width    = pct + '%';
        const fmt = s => { const m = Math.floor(s/60); return `${m}:${String(Math.floor(s%60)).padStart(2,'0')}`; };
        setText('rpcDiscordProgressStart', fmt((now - start) / 1000));
        setText('rpcDiscordProgressEnd',   fmt((end - start) / 1000));
    } else {
        if (progressWrap) progressWrap.style.display = 'none';
        if (progressBar)  progressBar.style.width    = '0%';
    }

    // No-activity overlay
    const noAct = document.getElementById('rpcNoActivity');
    if (noAct) {
        if (active && act.name) noAct.classList.remove('visible');
        else                    noAct.classList.add('visible');
    }

    // Meta strip
    setText('rpcPreviewMode',    res.mode   || 'none');
    setText('rpcPreviewTypeId',  act.type != null ? act.type : '—');
    setText('rpcPreviewAppId',   act.application_id || '—');
    setText('rpcPreviewButtons', Array.isArray(act.buttons) ? act.buttons.length : 0);

    if (!_rpcDraftRestored) {
        _rpcDraftRestored = true;
        const restored = restoreRpcDraft();
        if (!restored) {
            const setVal = (id, v) => { const el = document.getElementById(id); if (el) el.value = v || ''; };
            setVal('rpcType',            act.type != null ? String(act.type) : '0');
            setVal('rpcNameInput',       act.name    || '');
            setVal('rpcDisplayNameInput', act.display_name || '');
            setVal('rpcDetailsInput',    act.details || '');
            setVal('rpcStateInput',      act.state   || '');
            setVal('rpcStreamUrlInput',  act.url     || '');
            setVal('rpcLargeImageInput', assets.large_image || '');
            setVal('rpcSmallImageInput', assets.small_image || '');
            const btns    = Array.isArray(act.buttons) ? act.buttons : [];
            const btnUrls = act.metadata && Array.isArray(act.metadata.button_urls) ? act.metadata.button_urls : [];
            setVal('rpcButton1Label', btns[0]    || '');
            setVal('rpcButton1Url',   btnUrls[0] || '');
            setVal('rpcButton2Label', btns[1]    || '');
            setVal('rpcButton2Url',   btnUrls[1] || '');

            const inferredAppId = inferRpcAppIdFromActivity(act.name || '', act.details || '', act.state || '');
            const loadedAppId = String(act.application_id || '').trim();
            const customMode = loadedAppId && loadedAppId !== inferredAppId;
            setVal('rpcAppIdMode', customMode ? 'custom' : 'auto');
            setVal('rpcCustomAppIdInput', customMode ? loadedAppId : '');
            syncRpcAppIdControls();
            syncRpcStreamingControls();
            saveRpcDraft();
        }
    }
    updateRpcPreview();
}

// ── RPC live Discord-card preview ────────────────────────────────────────────
const RPC_ACTIVITY_HEADERS = {
    0: 'Playing a game',
    1: 'Live on Twitch',
    2: 'Listening to',
    3: 'Watching',
    4: 'Custom Status',
    5: 'Competing in',
};

function updateRpcPreview() {
    syncRpcAppIdControls();
    syncRpcStreamingControls();

    let typeVal = document.getElementById('rpcType')?.value;
    if (typeVal === 'custom') typeVal = 'custom';
    else typeVal = parseInt(typeVal) || 0;
    const name      = (document.getElementById('rpcNameInput')?.value    || '').trim();
    const details   = (document.getElementById('rpcDetailsInput')?.value || '').trim();
    const state     = (document.getElementById('rpcStateInput')?.value   || '').trim();
    const streamUrl = (document.getElementById('rpcStreamUrlInput')?.value || '').trim();
    const largeImg  = (document.getElementById('rpcLargeImageInput')?.value  || '').trim();
    const smallImg  = (document.getElementById('rpcSmallImageInput')?.value  || '').trim();
    const btn1Label = (document.getElementById('rpcButton1Label')?.value || '').trim();
    const btn2Label = (document.getElementById('rpcButton2Label')?.value || '').trim();

    // Activity header text
    const headerEl = document.querySelector('.discord-activity-header');
    if (headerEl) headerEl.textContent = RPC_ACTIVITY_HEADERS[typeVal] || 'Playing a game';

    // Text fields in card
    // Use spoofed display name if provided, else real name
    const displayName = (document.getElementById('rpcDisplayNameInput')?.value || '').trim();
    setText('rpcPreviewName', displayName || name || '—');
    setText('rpcPreviewDetails', details || '');
    setText('rpcPreviewState',   typeVal === 1 ? (streamUrl || state || '') : (state || ''));

    // Mini app id display
    const miniAppId = document.getElementById('miniAppId');
    if (miniAppId) {
        let appId = '';
        if (typeVal === 'custom') {
            appId = getEffectiveRpcAppId();
        } else {
            appId = inferRpcAppIdFromActivity(name, details, state);
        }
        miniAppId.textContent = appId && appId !== '1494507808329171096' ? `App ID: ${appId}` : '';
    }

    // Large image
    const artEl = document.getElementById('rpcDiscordArt');
    if (artEl) {
        let appIdForImage = getEffectiveRpcAppId();
        if (typeVal === 'custom') {
            appIdForImage = getEffectiveRpcAppId();
        } else {
            appIdForImage = inferRpcAppIdFromActivity(name, details, state);
        }
        const largePreview = resolveRpcPreviewImage(largeImg, appIdForImage);
        if (largePreview) {
            artEl.style.backgroundImage = `url("${String(largePreview).replace(/"/g, '%22')}")`;
            artEl.style.backgroundSize  = 'cover';
            artEl.style.backgroundColor = 'transparent';
        } else {
            artEl.style.backgroundImage = 'none';
            artEl.style.backgroundColor = 'var(--a1)';
        }
    }

    // Small art visibility
    const smallArtEl = document.getElementById('rpcDiscordSmallArt');
    if (smallArtEl) {
        let appIdForImage = getEffectiveRpcAppId();
        if (typeVal === 'custom') {
            appIdForImage = getEffectiveRpcAppId();
        } else {
            appIdForImage = inferRpcAppIdFromActivity(name, details, state);
        }
        const smallPreview = resolveRpcPreviewImage(smallImg, appIdForImage);
        if (smallPreview) {
            smallArtEl.classList.add('visible');
            smallArtEl.style.backgroundImage = `url("${String(smallPreview).replace(/"/g, '%22')}")`;
            smallArtEl.style.backgroundSize  = 'cover';
            smallArtEl.style.backgroundColor = 'transparent';
        } else {
            smallArtEl.classList.remove('visible');
            smallArtEl.style.backgroundImage = 'none';
            smallArtEl.style.backgroundColor = 'var(--a1)';
        }
    }

    // Buttons
    const btnsEl = document.getElementById('rpcDiscordButtons');
    if (btnsEl) {
        const labels = [btn1Label, btn2Label].filter(Boolean);
        btnsEl.innerHTML = labels.map(l => `<div class="discord-btn">${esc(l)}</div>`).join('');
        btnsEl.style.display = labels.length ? '' : 'none';
    }

    // Toggle no-activity overlay
    const noAct = document.getElementById('rpcNoActivity');
    if (noAct) {
        if (name) noAct.classList.remove('visible');
        else      noAct.classList.add('visible');
    }

    // Update meta strip
    setText('rpcPreviewTypeId', typeVal);
    setText('rpcPreviewAppId', getEffectiveRpcAppId());
    saveRpcDraft();
}

function showRpcMsg(msg, ok) {
    const el = document.getElementById('rpcMsg');
    if (!el) return;
    el.textContent = msg;
    el.className = 'settings-msg ' + (ok ? 'ok' : 'err');
    setTimeout(() => { el.textContent = ''; el.className = 'settings-msg'; }, 3000);
}

async function applyRpc() {
    let type = document.getElementById('rpcType').value;
    if (type === 'custom') type = 0; // fallback to Playing for custom
    else type = parseInt(type) || 0;
    const name = document.getElementById('rpcNameInput').value.trim();
    const display_name = (document.getElementById('rpcDisplayNameInput')?.value || '').trim();
    const details = document.getElementById('rpcDetailsInput').value.trim();
    const state = document.getElementById('rpcStateInput').value.trim();
    const streamUrl = (document.getElementById('rpcStreamUrlInput')?.value || '').trim();
    const largeImage = (document.getElementById('rpcLargeImageInput')?.value || '').trim();
    const smallImage = (document.getElementById('rpcSmallImageInput')?.value || '').trim();
    const button1Label = (document.getElementById('rpcButton1Label')?.value || '').trim();
    const button1Url = (document.getElementById('rpcButton1Url')?.value || '').trim();
    const button2Label = (document.getElementById('rpcButton2Label')?.value || '').trim();
    const button2Url = (document.getElementById('rpcButton2Url')?.value || '').trim();
    const appId = getEffectiveRpcAppId();
    if (!name) { showRpcMsg('Name is required.', false); return; }

    if (type === 1) {
        const twitchOk = /^https?:\/\/(www\.)?twitch\.tv\/[A-Za-z0-9_]+/i.test(streamUrl);
        if (!twitchOk) {
            showRpcMsg('Streaming type requires a valid Twitch URL.', false);
            return;
        }
    }

    // Keep the previewed activity name identical to the payload sent to Discord.
    const activity = { type, name: display_name || name, application_id: appId };
    if (details) activity.details = details;
    if (state) activity.state = state;
    if (type === 1 && streamUrl) activity.url = streamUrl;
    
    // Build assets object properly for Discord API
    const assets = {};
    if (largeImage) assets.large_image = largeImage;
    if (smallImage) assets.small_image = smallImage;
    if (Object.keys(assets).length > 0) activity.assets = assets;
    
    // Build buttons properly - Discord API expects buttons array of labels and metadata.button_urls array
    const buttonLabels = [];
    const buttonUrls = [];
    if (button1Label && button1Url) {
        buttonLabels.push(button1Label);
        buttonUrls.push(button1Url);
    }
    if (button2Label && button2Url) {
        buttonLabels.push(button2Label);
        buttonUrls.push(button2Url);
    }
    if (buttonLabels.length > 0) {
        activity.buttons = buttonLabels;
        activity.metadata = { button_urls: buttonUrls };
    }

    saveRpcDraft();
    
    const res = await postJSON('/api/rpc', { action: 'set', activity });
    if (res && res.ok) {
        showRpcMsg('RPC set.', true);
        trackDashboardAction('rpc_set', `Set RPC ${name}`);
        loadRpc();
    } else {
        showRpcMsg((res && res.error) || 'Failed to set RPC.', false);
    }
}

async function clearRpc() {
    const res = await postJSON('/api/rpc', { action: 'stop' });
    if (res && res.ok) {
        showRpcMsg('RPC cleared.', true);
        trackDashboardAction('rpc_clear', 'Stopped RPC activity');
        loadRpc();
    } else {
        showRpcMsg('Failed to stop RPC.', false);
    }
}

function showRpcProfileMsg(message, state = '') {
    const el = document.getElementById('rpcProfileMsg');
    if (!el) return;
    el.textContent = message;
    el.className = `rpc-profile-feedback${state ? ` ${state}` : ''}`;
}

let _rpcRotationOrder = [];
document.getElementById('rpcRotationPresets')?.addEventListener('change', event => {
    const select = event.currentTarget;
    const selected = new Set(Array.from(select.selectedOptions, option => option.value));
    _rpcRotationOrder = _rpcRotationOrder.filter(name => selected.has(name));
    for (const option of select.options) {
        if (option.selected && !_rpcRotationOrder.includes(option.value)) _rpcRotationOrder.push(option.value);
    }
});

async function loadRpcProfiles() {
    const data = await fetchJSON('/api/rpc/profiles');
    if (!data || !data.ok) return;

    const presets = Array.isArray(data.presets) ? data.presets : [];
    const rotationNames = data.rotation?.presets || [];
    const presetSelect = document.getElementById('rpcPresetSelect');
    const rotationSelect = document.getElementById('rpcRotationPresets');
    const intervalInput = document.getElementById('rpcRotationInterval');
    const selectedPreset = presetSelect?.value || '';

    for (const select of [presetSelect, rotationSelect]) {
        if (!select) continue;
        select.replaceChildren();
        if (!presets.length && select === presetSelect) {
            select.add(new Option('No presets saved', ''));
        }
        for (const name of presets) {
            const option = new Option(name, name);
            if (select === rotationSelect) option.selected = rotationNames.includes(name);
            select.add(option);
        }
    }
    _rpcRotationOrder = rotationNames.filter(name => presets.includes(name));
    if (presetSelect && presets.includes(selectedPreset)) presetSelect.value = selectedPreset;
    if (intervalInput && data.rotation?.interval) intervalInput.value = data.rotation.interval;
    if (data.rotation_running) {
        showRpcProfileMsg(`Rotation active · ${rotationNames.join(' → ')} · ${data.rotation.interval}s`, 'success');
    } else if (data.rotation) {
        showRpcProfileMsg(`Rotation ready · ${rotationNames.join(' → ')} · ${data.rotation.interval}s`);
    } else {
        showRpcProfileMsg(presets.length ? `${presets.length} preset${presets.length === 1 ? '' : 's'} saved` : 'Save an activity to create your first preset.');
    }
}

async function saveRpcPreset() {
    const name = (document.getElementById('rpcPresetName')?.value || '').trim();
    if (!name) { showRpcProfileMsg('Enter a preset name first.', 'error'); return; }
    const res = await postJSON('/api/rpc/profiles/preset', { action: 'save', name });
    if (!res?.ok) { showRpcProfileMsg(res?.error || 'Preset could not be saved.', 'error'); return; }
    document.getElementById('rpcPresetName').value = '';
    showRpcProfileMsg(`Saved “${name}”.`, 'success');
    await loadRpcProfiles();
}

async function loadRpcPreset() {
    const name = document.getElementById('rpcPresetSelect')?.value || '';
    if (!name) { showRpcProfileMsg('Choose a saved preset first.', 'error'); return; }
    const res = await postJSON('/api/rpc/profiles/preset', { action: 'load', name });
    if (!res?.ok) { showRpcProfileMsg(res?.error || 'Preset could not be loaded.', 'error'); return; }
    showRpcProfileMsg(`Loaded “${name}”.`, 'success');
    loadRpc();
}

async function deleteRpcPreset() {
    const name = document.getElementById('rpcPresetSelect')?.value || '';
    if (!name) { showRpcProfileMsg('Choose a saved preset first.', 'error'); return; }
    if (!window.confirm(`Delete the RPC preset “${name}”?`)) return;
    const res = await postJSON('/api/rpc/profiles/preset', { action: 'delete', name });
    if (!res?.ok) { showRpcProfileMsg(res?.error || 'Preset could not be deleted.', 'error'); return; }
    showRpcProfileMsg(`Deleted “${name}”.`, 'success');
    await loadRpcProfiles();
}

async function setRpcRotation() {
    const select = document.getElementById('rpcRotationPresets');
    const selected = new Set(Array.from(select?.selectedOptions || [], option => option.value));
    const presets = _rpcRotationOrder.filter(name => selected.has(name));
    for (const option of select?.options || []) {
        if (option.selected && !presets.includes(option.value)) presets.push(option.value);
    }
    const interval = Number.parseInt(document.getElementById('rpcRotationInterval')?.value, 10);
    if (presets.length < 2) { showRpcProfileMsg('Select at least two presets in rotation order.', 'error'); return; }
    const res = await postJSON('/api/rpc/profiles/rotation', { action: 'set', presets, interval });
    if (!res?.ok) { showRpcProfileMsg(res?.error || 'Rotation could not be saved.', 'error'); return; }
    showRpcProfileMsg(`Rotation saved · ${presets.join(' → ')} · ${interval}s`, 'success');
    await loadRpcProfiles();
}

async function controlRpcRotation(action) {
    const res = await postJSON('/api/rpc/profiles/rotation', { action });
    if (!res?.ok) { showRpcProfileMsg(res?.error || `Rotation ${action} failed.`, 'error'); return; }
    const messages = { start: 'Rotation started.', stop: 'Rotation stopped.', clear: 'Rotation configuration cleared.' };
    showRpcProfileMsg(messages[action] || 'Rotation updated.', 'success');
    await loadRpcProfiles();
}

// ── Presence ───────────────────────────────────────────────────────────────────
const PRESENCE_BADGES = {
    online:    'badge-ok',
    idle:      'badge-warn',
    dnd:       'badge-pink',
    invisible: 'badge-off',
};

async function loadPresence() {
    const [presRes, afkRes] = await Promise.all([
        fetchJSON('/api/presence'),
        fetchJSON('/api/afk'),
    ]);
    if (presRes) {
        const status = presRes.status || 'unknown';
        const badge = document.getElementById('presenceBadge');
        if (badge) {
            badge.textContent = status.charAt(0).toUpperCase() + status.slice(1);
            badge.className = 'badge ' + (PRESENCE_BADGES[status] || 'badge-off');
        }
    }
    if (afkRes) {
        const afkBadge = document.getElementById('afkBadge');
        if (afkBadge) {
            afkBadge.textContent = afkRes.active ? 'AFK' : 'Off';
            afkBadge.className = 'badge ' + (afkRes.active ? 'badge-warn' : 'badge-off');
        }
        const afkInput = document.getElementById('afkMessageInput');
        if (afkInput && afkRes.message) afkInput.placeholder = afkRes.message;
    }
}

function showPresenceMsg(id, msg, ok) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = msg;
    el.className = 'settings-msg ' + (ok ? 'ok' : 'err');
    setTimeout(() => { el.textContent = ''; el.className = 'settings-msg'; }, 3000);
}

async function setPresence(status) {
    const res = await postJSON('/api/presence', { status });
    if (res && res.ok) {
        showPresenceMsg('presenceMsg', 'Status set to: ' + status, true);
        trackDashboardAction('presence_set', `Set status to ${status}`);
        loadPresence();
        loadOverview();
    } else {
        showPresenceMsg('presenceMsg', (res && res.error) || 'Failed to set status.', false);
    }
}

async function toggleAfk(action) {
    const message = document.getElementById('afkMessageInput').value.trim() || 'AFK';
    const res = await postJSON('/api/afk', { action, message });
    if (res && res.ok) {
        showPresenceMsg('afkMsg', res.active ? ('AFK enabled: ' + (res.message || '')) : 'AFK cleared.', true);
        trackDashboardAction('afk_toggle', res.active ? 'Enabled AFK' : 'Disabled AFK');
        loadPresence();
    } else {
        showPresenceMsg('afkMsg', (res && res.error) || 'AFK system unavailable.', false);
    }
}

// ── Hosted ────────────────────────────────────────────────────────────────────
async function loadHosted() {
    const res = await fetchJSON('/api/hosted');
    if (!res) return;
    setText('hostedTotal', res.total ?? 0);
    setText('hostedActive', res.active_count ?? 0);
    const badge = document.getElementById('hostedBadge');
    if (badge) badge.textContent = res.total ?? 0;
    const tbody = document.getElementById('hostedBody');
    if (!tbody) return;
    if (!res.hosted || res.hosted.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="empty-row">No hosted users found</td></tr>';
        return;
    }

    tbody.innerHTML = res.hosted.map(u => {
        let statusBadge = `<span class="badge ${u.active ? 'badge-ok' : 'badge-off'}">${u.active ? '● Active' : '○ Inactive'}</span>`;
        let warn = '';
        if (!u.active) {
            warn = '<div style="color:#e74c3c;font-size:12px;margin-top:2px">Not connected — commands will not work</div>';
        }
        return `<tr>
            <td class="cmd-name" style="font-size:11px">${esc(u.token_id || '—')}</td>
            <td>${esc(u.username || '—')}</td>
            <td class="cmd-aliases">${esc(u.user_id || '—')}</td>
            <td class="cmd-aliases">${esc(u.prefix || '—')}</td>
            <td class="cmd-aliases">${esc(u.client_type || 'unknown')}</td>
            <td>${statusBadge}${warn}</td>
            <td class="cmd-aliases">${esc(fmtTs(u.connected_at) || '—')}</td>
            <td>
                <button class="btn btn-danger-soft" style="padding:4px 10px;font-size:11px" onclick="disconnectHostedInstance('${encodeURIComponent(u.token_ref || '')}')">Remove</button>
            </td>
        </tr>`;
    }).join('');
}

async function connectHostedToken() {
    const tokenInput = document.getElementById('hostTokenInput');
    const prefixInput = document.getElementById('hostPrefixInput');
    const token = tokenInput ? tokenInput.value.trim() : '';
    const prefix = prefixInput ? prefixInput.value.trim() : '$';
    if (!token) {
        showPresenceMsg('hostedActionMsg', 'Token is required.', false);
        return;
    }
    const res = await postJSON('/api/hosted/connect', { token, prefix });
    if (res && res.ok) {
        showPresenceMsg('hostedActionMsg', res.message || 'Instance connected.', true);
        trackDashboardAction('host_connect', 'Connected a hosted instance');
        if (tokenInput) tokenInput.value = '';
        await loadHosted();
        await loadOverview();
        return;
    }
    showPresenceMsg('hostedActionMsg', (res && res.error) || 'Failed to connect instance.', false);
}

async function disconnectHostedInstance(encodedTokenId) {
    const token_id = decodeURIComponent(encodedTokenId || '');
    if (!token_id) return;
    if (!confirm('Disconnect this hosted instance?')) return;
    const res = await postJSON('/api/hosted/disconnect', { token_id });
    if (res && res.ok) {
        showPresenceMsg('hostedActionMsg', 'Hosted instance disconnected.', true);
        trackDashboardAction('host_disconnect', `Disconnected ${token_id.slice(0, 8)}...`);
        await loadHosted();
        await loadOverview();
        return;
    }
    showPresenceMsg('hostedActionMsg', (res && res.error) || 'Failed to disconnect instance.', false);
}

// ── Dashboard Users (login management) ───────────────────────────────────────
async function loadDashUsers() {
    await loadDashProfile();
    await loadMyActivityTimeline();
    const res = await fetchJSON('/api/dash/users');
    if (!res) {
        const tbody = document.getElementById('dashUsersBody');
        if (tbody) tbody.innerHTML = '<tr><td colspan="4" class="empty-row">Admin only</td></tr>';
        return;
    }
    const count = res.total ?? 0;
    const el = document.getElementById('dashUsersTotal');
    if (el) el.textContent = count + (count === 1 ? ' account' : ' accounts');
    const tbody = document.getElementById('dashUsersBody');
    if (!tbody) return;
    if (!res.users || res.users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="empty-row">No dashboard accounts yet</td></tr>';
        return;
    }
    tbody.innerHTML = res.users.map(u =>
        `<tr>
            <td class="cmd-aliases">${esc(u.user_id)}</td>
            <td style="font-weight:600">${esc(u.username)}</td>
            <td class="cmd-aliases">${esc(u.instance_id || '—')}</td>
            <td><button class="btn btn-danger-soft" onclick="removeDashUser('${esc(u.user_id)}')" style="padding:4px 12px;font-size:11px">Remove</button></td>
        </tr>`
    ).join('');

    await loadAccessRequests();
}

function showDashAccountMsg(msg, ok) {
    const el = document.getElementById('dashAccountMsg');
    if (!el) return;
    el.textContent = msg;
    el.className = 'settings-msg ' + (ok ? 'ok' : 'err');
    setTimeout(() => { el.textContent = ''; el.className = 'settings-msg'; }, 4000);
}

function showAccessReqBulkMsg(msg, ok) {
    const el = document.getElementById('accessReqBulkMsg');
    if (!el) return;
    el.textContent = msg;
    el.className = 'settings-msg ' + (ok ? 'ok' : 'err');
    setTimeout(() => { el.textContent = ''; el.className = 'settings-msg'; }, 5000);
}

function applyRoleVisibility(profile) {
    const isAdmin = !!(profile && profile.is_admin);
    const isOwner = !!(profile && profile.is_owner);
    document.querySelectorAll('[data-owner-only="true"]').forEach(el => {
        el.hidden = !isOwner;
        if (el.classList.contains('nav-item')) el.dataset.hiddenByRole = String(!isOwner);
    });
    const adminOnly = document.querySelectorAll('[data-admin-only="true"], .admin-only');
    adminOnly.forEach(el => {
        if (isAdmin) {
            el.style.display = '';
            if (el.classList.contains('nav-item')) el.dataset.hiddenByRole = 'false';
        } else {
            el.style.display = 'none';
            if (el.classList.contains('nav-item')) el.dataset.hiddenByRole = 'true';
        }
    });

    const usersTitle = document.getElementById('dashUsersTotal');
    if (usersTitle && !isAdmin) usersTitle.textContent = 'My account';

    const active = document.querySelector('.nav-item.active');
    if (active && (active.hidden || active.dataset.hiddenByRole === 'true')) {
        const fallback = document.querySelector('.nav-item[data-section="overview"]');
        if (fallback) fallback.click();
    }
}

async function loadOwnerPanel() {
    const res = await fetchJSON('/api/owner/summary');
    if (!res || !res.ok) {
        setText('ownerGatewayState', 'Unavailable');
        setText('ownerIdentityState', 'Unavailable');
        return;
    }

    const data = res.data || {};
    setText('ownerAccountTotal', data.total_accounts ?? 0);
    setText('ownerAdminTotal', data.admin_accounts ?? 0);
    setText('ownerPendingTotal', data.pending_requests ?? 0);
    setText('ownerGatewayState', data.connected ? 'Connected' : 'Offline');
    setText('ownerGatewayLatency', `Latency ${data.gateway_latency_ms == null ? '—' : `${data.gateway_latency_ms} ms`}`);
    setText('ownerIdentityState', data.connected ? 'ready' : 'offline');
    setText('ownerIdentityName', data.username || '—');
    setText('ownerIdentityId', data.user_id || '—');

    const accounts = Array.isArray(data.accounts) ? data.accounts : [];
    setText('ownerAccountBadge', `${accounts.length} accounts`);
    const accountBody = document.getElementById('ownerAccountBody');
    if (accountBody) {
        accountBody.innerHTML = accounts.length ? accounts.map(account => {
            const username = String(account.username || 'Unnamed account');
            return `<tr data-username="${esc(username.toLowerCase())}">
                <td class="owner-account-name">${esc(username)}</td>
                <td>${esc(account.role || 'user')}</td>
                <td>${fmtTs(account.created_at)}</td>
                <td>${fmtTs(account.last_login_at)}</td>
            </tr>`;
        }).join('') : '<tr><td colspan="4" class="empty-row">No accounts yet.</td></tr>';
    }

    const resetRequests = Array.isArray(data.password_reset_requests) ? data.password_reset_requests : [];
    setText('ownerResetBadge', `${resetRequests.length} pending`);
    const resetList = document.getElementById('ownerResetRequestsList');
    if (resetList) {
        resetList.innerHTML = resetRequests.length ? resetRequests.map(item => {
            const requestId = esc(item.id || '');
            const username = esc(item.username || 'Account');
            return `<article class="owner-reset-request">
                <div class="owner-reset-request-main"><strong>${username}</strong><span>${esc(item.reason || 'Password reset requested')}</span><small>${relativeTime(item.timestamp)}</small></div>
                <div class="owner-reset-request-actions">
                    <button class="btn btn-primary" type="button" onclick="approveAccessRequest('${requestId}', 'password_reset')">Approve reset</button>
                    <button class="btn btn-ghost" type="button" onclick="denyAccessRequest('${requestId}')" aria-label="Deny reset request for ${username}">Deny</button>
                </div>
            </article>`;
        }).join('') : '<div class="log-loading">No pending password reset requests.</div>';
    }
}

function filterOwnerAccounts() {
    const query = String(document.getElementById('ownerAccountSearch')?.value || '').trim().toLowerCase();
    document.querySelectorAll('#ownerAccountBody tr[data-username]').forEach(row => {
        row.hidden = !row.dataset.username.includes(query);
    });
}

function showOwnerResetCredential(username, password) {
    const overlay = document.getElementById('ownerResetCredential');
    if (!overlay) return;
    setText('ownerResetCredentialUser', username || 'Account');
    setText('ownerResetCredentialValue', password || '');
    overlay.hidden = false;
    document.getElementById('ownerResetDialogTitle')?.focus();
}

async function copyOwnerResetCredential() {
    const password = document.getElementById('ownerResetCredentialValue')?.textContent || '';
    if (!password) return;
    try {
        await navigator.clipboard.writeText(password);
        showOwnerResetMessage('Temporary password copied. This view will not be available again.', true);
    } catch {
        showOwnerResetMessage('Clipboard unavailable. Select the temporary password to copy it.', false);
    }
}

function dismissOwnerResetCredential() {
    const overlay = document.getElementById('ownerResetCredential');
    if (overlay) overlay.hidden = true;
    setText('ownerResetCredentialValue', '');
    setText('ownerResetCredentialUser', 'Account');
}

function showOwnerResetMessage(message, ok) {
    const el = document.getElementById('ownerResetMessage');
    if (!el) return;
    el.textContent = message;
    el.className = 'owner-reset-message settings-msg ' + (ok ? 'ok' : 'err');
}

async function loadDashProfile() {
    const res = await fetchJSON('/api/dash/me');
    if (!res || !res.ok) {
        setText('meUsername', '—');
        setText('meUserId', '—');
        setText('meRole', '—');
        setText('meInstance', '—');
        setText('pendingRequests', 0);
        setText('meLastLogin', '—');
        setText('meLastSeen', '—');
        return;
    }

    const p = res.profile || {};
    _meProfile = p;
    const s = res.summary || {};
    setText('meUsername', p.username || '—');
    setText('meUserId', p.user_id || '—');
    setText('meRole', p.role || 'user');
    setText('meInstance', p.instance_id || '—');
    setText('pendingRequests', s.pending_requests ?? 0);
    setText('meLastLogin', fmtTs(p.last_login_at));
    setText('meLastSeen', fmtTs(p.last_seen_at));

    const card = document.getElementById('accessRequestsCard');
    if (card) card.style.display = p.is_admin ? 'block' : 'none';
    applyRoleVisibility(p);
}

async function loadMyActivityTimeline() {
    const feed = document.getElementById('activityTimelineFeed');
    const badge = document.getElementById('activityTimelineBadge');
    if (!feed || !badge) return;

    const res = await fetchJSON('/api/dash/activity');
    if (!res || !res.ok) {
        badge.textContent = '0';
        feed.innerHTML = '<div class="log-loading">Unable to load timeline.</div>';
        return;
    }

    const timeline = Array.isArray(res.timeline) ? res.timeline : [];
    badge.textContent = String(timeline.length);
    if (!timeline.length) {
        feed.innerHTML = '<div class="log-loading">No recent account actions yet.</div>';
        return;
    }

    feed.innerHTML = timeline.slice().reverse().map(t => {
        const action = esc(t.action || 'activity');
        const details = esc(t.details || '');
        const ts = fmtTs(t.ts);
        return `<div class="history-item">
            <div class="history-dot"></div>
            <div class="history-content">
                <span class="history-cmd">${action}</span>
                <div class="history-meta">🕐 ${esc(ts)}</div>
                ${details ? `<div class="history-raw">${details}</div>` : ''}
            </div>
        </div>`;
    }).join('');
}

async function changeMyPassword() {
    const oldPassword = document.getElementById('oldPasswordInput').value;
    const newPassword = document.getElementById('newPasswordInput').value;
    if (!oldPassword || !newPassword) {
        showDashAccountMsg('Enter both current and new password.', false);
        return;
    }
    const res = await postJSON('/api/dash/change-password', {
        old_password: oldPassword,
        new_password: newPassword,
    });
    if (res && res.ok) {
        showDashAccountMsg('Password updated.', true);
        trackDashboardAction('password_change', 'Updated dashboard password');
        document.getElementById('oldPasswordInput').value = '';
        document.getElementById('newPasswordInput').value = '';
        loadMyActivityTimeline();
    } else {
        showDashAccountMsg((res && res.error) || 'Failed to update password.', false);
    }
}

async function loadAccessRequests() {
    const card = document.getElementById('accessRequestsCard');
    const body = document.getElementById('accessReqBody');
    const badge = document.getElementById('accessReqBadge');
    if (!card || !body || !badge) return;

    const res = await fetchJSON('/api/dash/requests');
    if (!res || !res.ok) {
        body.innerHTML = '<tr><td colspan="5" class="empty-row">Admin only</td></tr>';
        return;
    }

    const reqs = res.requests || [];
    badge.textContent = String(reqs.length);
    if (!reqs.length) {
        body.innerHTML = '<tr><td colspan="5" class="empty-row">No account requests</td></tr>';
        return;
    }

    body.innerHTML = reqs.slice().reverse().map(r => {
        const id = esc(r.id || '');
        const reqType = String(r.type || 'access').toLowerCase();
        const reqLabel = reqType === 'password_reset' ? 'Password Reset' : 'Access';
        const targetUser = reqType === 'password_reset'
            ? (r.user_id || r.approved_uid || '—')
            : (r.username || r.user_id || '—');
        const details = reqType === 'password_reset'
            ? (r.reason || 'Password reset requested')
            : (r.reason || '—');
        const status = String(r.status || 'pending').toLowerCase();
        const statusClass = status === 'approved' ? 'badge-ok' : status === 'denied' ? 'badge-pink' : 'badge-warn';
        const actions = status === 'pending'
            ? `<button class="btn btn-primary" style="padding:4px 10px;font-size:11px" onclick="approveAccessRequest('${id}', '${esc(reqType)}')">Approve</button>
               <button class="btn btn-danger-soft" style="padding:4px 10px;font-size:11px" onclick="denyAccessRequest('${id}')">Deny</button>`
            : '<span style="color:var(--muted);font-size:12px">Complete</span>';

        return `<tr>
            <td style="font-weight:600">${esc(reqLabel)}</td>
            <td>${esc(targetUser)}</td>
            <td style="color:var(--muted)">${esc(details)}</td>
            <td><span class="badge ${statusClass}">${esc(status)}</span></td>
            <td>${actions}</td>
        </tr>`;
    }).join('');
}

async function approveAccessRequest(reqId, reqType = 'access') {
    const isPasswordReset = String(reqType || '').toLowerCase() === 'password_reset';
    if (isPasswordReset && !confirm('Rotate this account password and show the generated temporary password once?')) return;
    const customUserId = isPasswordReset ? '' : (prompt('Optional: set custom user_id (leave empty for auto)') || '');
    const customPassword = isPasswordReset ? '' : (prompt('Optional: set custom password (leave empty for auto)') || '');
    const body = {};
    if (customUserId.trim()) body.user_id = customUserId.trim();
    if (customPassword.trim()) body.password = customPassword.trim();

    try {
        const r = await fetch(`/api/dash/requests/${encodeURIComponent(reqId)}/approve`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.content || '',
            },
            body: JSON.stringify(body),
        });
        const res = await r.json();
        if (res && res.ok) {
            if (isPasswordReset) {
                showOwnerResetCredential(res.username, res.password);
                showOwnerResetMessage('Reset approved. Copy the generated password now; it will not be stored in this panel.', true);
            } else {
                showDashUsersMsg(`Approved account ${res.user_id}.`, true);
            }
            trackDashboardAction('request_approve', `Approved request ${reqId}`);
            loadAccessRequests();
            loadDashUsers();
            loadOwnerPanel();
        } else {
            showDashUsersMsg((res && res.error) || 'Approve failed.', false);
        }
    } catch {
        showDashUsersMsg('Approve request failed.', false);
    }
}

async function denyAccessRequest(reqId) {
    try {
        const r = await fetch(`/api/dash/requests/${encodeURIComponent(reqId)}/deny`, { method: 'POST' });
        const res = await r.json();
        if (res && res.ok) {
            showDashUsersMsg('Request denied.', true);
            trackDashboardAction('request_deny', `Denied request ${reqId}`);
            loadAccessRequests();
            loadDashUsers();
            loadOwnerPanel();
        } else {
            showDashUsersMsg((res && res.error) || 'Deny failed.', false);
        }
    } catch {
        showDashUsersMsg('Deny request failed.', false);
    }
}

function showDashUsersMsg(msg, ok) {
    const el = document.getElementById('dashUsersMsg') || document.getElementById('ownerResetMessage');
    if (!el) return;
    el.textContent = msg;
    el.className = 'settings-msg ' + (ok ? 'ok' : 'err');
    setTimeout(() => { el.textContent = ''; el.className = 'settings-msg'; }, 4000);
}

async function addDashUser() {
    const uid = document.getElementById('newDashUserId').value.trim();
    const uname = document.getElementById('newDashUsername').value.trim();
    const pw = document.getElementById('newDashPassword').value;
    if (!uid || !pw) { showDashUsersMsg('User ID and password required.', false); return; }
    const res = await postJSON('/api/dash/register', { user_id: uid, username: uname || uid, password: pw });
    if (res && res.ok) {
        showDashUsersMsg(`Login created for ${uid}`, true);
        trackDashboardAction('account_create', `Created account ${uid}`);
        document.getElementById('newDashPassword').value = '';
        loadDashUsers();
    } else {
        showDashUsersMsg((res && res.error) || 'Failed.', false);
    }
}

async function removeDashUser(uid) {
    try {
        const r = await fetch(`/api/dash/register/${uid}`, { method: 'DELETE' });
        const res = await r.json();
        if (res && res.ok) { showDashUsersMsg(`Removed ${uid}`, true); trackDashboardAction('account_remove', `Removed account ${uid}`); loadDashUsers(); }
        else showDashUsersMsg((res && res.error) || 'Failed.', false);
    } catch(e) { showDashUsersMsg('Request failed.', false); }
}

async function approveAllPendingRequests() {
    const res = await postJSON('/api/dash/requests/approve-all-pending', {});
    if (res && res.ok) {
        const count = Number(res.approved_count || 0);
        const sample = Array.isArray(res.approved) && res.approved.length
            ? ` First: ${res.approved[0].user_id}/${res.approved[0].password}`
            : '';
        showAccessReqBulkMsg(`Approved ${count} pending request(s).${sample}`, true);
        trackDashboardAction('request_bulk_approve', `Bulk approved ${count} requests`);
        loadAccessRequests();
        loadDashUsers();
    } else {
        showAccessReqBulkMsg((res && res.error) || 'Bulk approve failed.', false);
    }
}

async function denyAllPendingRequests() {
    const res = await postJSON('/api/dash/requests/deny-all-pending', {});
    if (res && res.ok) {
        const count = Number(res.denied_count || 0);
        showAccessReqBulkMsg(`Denied ${count} pending request(s).`, true);
        trackDashboardAction('request_bulk_deny', `Bulk denied ${count} requests`);
        loadAccessRequests();
        loadDashUsers();
    } else {
        showAccessReqBulkMsg((res && res.error) || 'Bulk deny failed.', false);
    }
}

async function trackDashboardAction(action, details = '') {
    if (!_meProfile) return;
    if (!action) return;
    await postJSON('/api/dash/activity', { action, details });
}

// ── Logs ──────────────────────────────────────────────────────────────────────
async function loadLogs() {
    const container = document.getElementById('logContainer');
    const countEl   = document.getElementById('logLineCount');
    const cmdFeed   = document.getElementById('commandExecFeed');
    const sniperFeed = document.getElementById('sniperFeed');
    const gatewayFeed = document.getElementById('gatewayFeed');
    if (!container) return;
    container.innerHTML = '<div class="log-loading">Fetching logs…</div>';
    const res = await fetchJSON('/api/logs?lines=100');
    if (!res || !res.lines) {
        container.innerHTML = '<div class="log-loading">Failed to load logs.</div>';
        return;
    }

    const summary = res.summary || {};
    const connectedUser = summary.connected_user || {};
    setText('logsConnectedUser', connectedUser.username || '—');
    setText('logsConnectedUserId', connectedUser.user_id || '—');
    setText('logsCommandTotal', summary.command_total ?? 0);
    setText('logsCommandEvents', summary.command_events ?? 0);
    setText('logsSniperEvents', summary.sniper_events ?? 0);
    setText('logsGatewayEvents', summary.gateway_events ?? 0);
    setText('logsErrorEvents', summary.error_events ?? 0);

    const events = res.events || {};
    const commandEvents = events.commands || [];
    const sniperEvents = events.snipers || [];
    const gatewayEvents = events.gateway || [];
    const errorEvents = events.errors || [];

    if (cmdFeed) {
        if (!commandEvents.length) {
            cmdFeed.innerHTML = '<div class="log-loading">No command execution logs yet.</div>';
        } else {
            cmdFeed.innerHTML = commandEvents.slice().reverse().map(e => {
                const duration = e.duration_ms != null ? `${Math.round(e.duration_ms)}ms` : '—';
                const status = String(e.status || 'success').toLowerCase();
                const statusBadge = status === 'failed'
                    ? '<span class="badge badge-pink">failed</span>'
                    : '<span class="badge badge-ok">ok</span>';
                return `<div class="history-item">
                    <div class="history-dot"></div>
                    <div class="history-content">
                        <span class="history-cmd">${esc(e.command || '(unknown)')}</span>
                        <span class="badge badge-warn">#${esc(String(e.number || '0'))}</span>
                        ${statusBadge}
                        <div class="history-meta">${[
                            e.user ? '👤 ' + esc(e.user) : '',
                            e.guild ? '🏠 ' + esc(e.guild) : '',
                            e.time ? '🕐 ' + esc(e.time) : '',
                            '⚡ ' + esc(duration),
                        ].filter(Boolean).join(' &nbsp;·&nbsp; ')}</div>
                    </div>
                </div>`;
            }).join('');
        }
    }

    if (sniperFeed) {
        if (!sniperEvents.length) {
            sniperFeed.innerHTML = '<div class="log-loading">No sniper logs yet.</div>';
        } else {
            sniperFeed.innerHTML = sniperEvents.slice().reverse().map(e => `
                <div class="history-item">
                    <div class="history-dot"></div>
                    <div class="history-content">
                        ${e.time ? `<div class="history-meta">🕐 ${esc(e.time)}</div>` : ''}
                        <div class="history-raw">${esc(e.raw || '')}</div>
                    </div>
                </div>
            `).join('');
        }
    }

    if (gatewayFeed) {
        const merged = gatewayEvents.concat(errorEvents).slice(-100);
        if (!merged.length) {
            gatewayFeed.innerHTML = '<div class="log-loading">No gateway/error logs yet.</div>';
        } else {
            gatewayFeed.innerHTML = merged.slice().reverse().map(e => {
                const lo = String(e.raw || '').toLowerCase();
                const badge = (lo.includes('error') || lo.includes('exception') || lo.includes('failed'))
                    ? '<span class="badge badge-pink">error</span>'
                    : '<span class="badge badge-warn">gateway</span>';
                return `<div class="history-item">
                    <div class="history-dot"></div>
                    <div class="history-content">
                        ${badge}
                        ${e.time ? `<div class="history-meta">🕐 ${esc(e.time)}</div>` : ''}
                        <div class="history-raw">${esc(e.raw || '')}</div>
                    </div>
                </div>`;
            }).join('');
        }
    }

    if (res.lines.length === 0) {
        container.innerHTML = '<div class="log-loading">No log output yet.</div>';
        return;
    }
    if (countEl) countEl.textContent = res.lines.length + ' lines';
    container.innerHTML = res.lines.map(l => {
        const lo = l.toLowerCase();
        const cls = (lo.includes('[error]') || lo.includes('[auth-error]') || lo.includes('traceback') || lo.includes('exception'))
                  ? 'log-error'
                  : (lo.includes('[warning]') || lo.includes('[warn]'))
                  ? 'log-warn'
                  : lo.includes('[rpc]')
                  ? 'log-rpc'
                  : lo.includes('[gateway]')
                  ? 'log-gateway'
                  : (lo.includes('success') || lo.includes('connected') || lo.includes('ready'))
                  ? 'log-success'
                  : '';
        return `<div class="log-line ${cls}">${esc(l)}</div>`;
    }).join('');
    container.scrollTop = container.scrollHeight;
}

// ── Refresh button ────────────────────────────────────────────────────────────
document.getElementById('refreshBtn')?.addEventListener('click', () => {
    const active = document.querySelector('.nav-item.active');
    if (active) {
        loadSection(active.dataset.section);
        showToast('Refreshed', `Section "${active.dataset.section}" reloaded`, 'ok', 2200);
    }
});

// ── Auto-refresh every 30s ────────────────────────────────────────────────────
setInterval(() => {
    const active = document.querySelector('.nav-item.active');
    if (active) loadSection(active.dataset.section);
}, 30000);

// Faster overview heartbeat for more "live" feeling metrics.
setInterval(() => {
    const active = document.querySelector('.nav-item.active');
    if (active && active.dataset.section === 'overview') loadOverview();
}, 7000);

// ── Initial load ──────────────────────────────────────────────────────────────
async function bootDashboard() {
    const initialRequests = Promise.allSettled([
        loadOverview(),
        loadDashProfile(),
        refreshNotificationCenter(),
    ]);
    const timeout = new Promise(resolve => setTimeout(() => resolve(false), 8000));
    const isSynced = await Promise.race([initialRequests.then(() => true), timeout]);
    setText('loaderStatus', isSynced ? 'RUNTIME / INITIAL SYNC COMPLETE' : 'RUNTIME / CONTINUING CONNECTION');
    setTimeout(dismissLoader, 300);
}
bootDashboard();
// Welcome toast
setTimeout(() => showToast('Welcome back 👋', 'Aria dashboard loaded successfully', 'ok', 4000), 1200);

document.addEventListener('DOMContentLoaded', () => {
    const bell = document.getElementById('topbarBell');
    const panel = document.getElementById('notificationCenter');
    const clearBtn = document.getElementById('notificationClearBtn');

    if (bell) {
        bell.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleNotificationCenter();
        });
    }

    if (clearBtn) {
        clearBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            fetch('/api/discord/notifications', { method: 'DELETE' }).catch(() => {});
            _notificationState.events = [];
            _notificationState.seenTs = Date.now() / 1000;
            refreshNotificationCenter();
        });
    }

    document.addEventListener('click', (e) => {
        if (!_notificationState.open) return;
        if (!panel) return;
        if (panel.contains(e.target) || (bell && bell.contains(e.target))) return;
        toggleNotificationCenter(false);
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && _notificationState.open) {
            toggleNotificationCenter(false);
        }
    });
});

// ── Live Chat Support System ─────────────────────────────────────────────────
let _chatState = {
    sessions: [],
    currentSessionId: null,
    autoRefreshInterval: null
};

async function loadChat() {
    try {
        const chatLayout = document.getElementById('chat-layout') || document.querySelector('.chat-layout');
        if (!chatLayout) return;

        loadChatSessions();
        
        // Set up auto-refresh
        if (_chatState.autoRefreshInterval) clearInterval(_chatState.autoRefreshInterval);
        _chatState.autoRefreshInterval = setInterval(loadChatSessions, 3000);
    } catch (e) {
        console.error('[Chat] Load error:', e);
    }
}

async function loadChatSessions() {
    try {
        const sessionsList = document.getElementById('chatSessionsList');
        if (!sessionsList) return;
        
        const res = await fetchJSON('/api/chat/sessions');
        if (!res || res.error) return;
        
        _chatState.sessions = res.sessions || [];
        
        // Clear and rebuild list
        sessionsList.innerHTML = '';
        
        if (_chatState.sessions.length === 0) {
            sessionsList.innerHTML = '<div style="padding:12px;text-align:center;color:var(--muted);font-size:0.9em">No active chats</div>';
            return;
        }
        
        _chatState.sessions.forEach(session => {
            const item = document.createElement('div');
            item.className = 'chat-session-item' + (session.session_id === _chatState.currentSessionId ? ' active' : '');
            item.dataset.sessionId = session.session_id;
            item.onclick = () => openChatSession(session.session_id, item);
            
            const unreadCount = (session.unread_count || 0);
            const unreadBadge = unreadCount > 0 ? `<span class="unread-badge">${unreadCount}</span>` : '';
            
            item.innerHTML = `
                <div class="session-user">
                    <strong>${escapeHtml(session.username)}</strong>
                    ${unreadBadge}
                </div>
                <div class="session-meta" style="font-size:0.8em;color:var(--muted)">
                    ${session.resolved ? '<span style="color:#ff4757">Resolved</span>' : '<span style="color:#2ed573">Active</span>'}
                    • ${formatTime(session.last_updated)}
                </div>
            `;
            
            sessionsList.appendChild(item);
        });

        if (_chatState.currentSessionId) {
            const activeItem = Array.from(sessionsList.children).find(
                item => item.dataset.sessionId === _chatState.currentSessionId
            );
            if (activeItem) {
                await openChatSession(_chatState.currentSessionId, activeItem);
            }
        }
    } catch (e) {
        console.error('[Chat] Load sessions error:', e);
    }
}

async function openChatSession(sessionId, clickedItem = null) {
    try {
        _chatState.currentSessionId = sessionId;
        
        const chatViewer = document.getElementById('chatViewer');
        const emptyState = document.getElementById('chatEmptyState');
        const messagesContainer = document.getElementById('chatMessages');
        
        if (!chatViewer || !messagesContainer) return;
        
        // Show viewer, hide empty state
        chatViewer.style.display = 'flex';
        emptyState.style.display = 'none';
        
        // Update active highlight
        document.querySelectorAll('.chat-session-item').forEach(item => {
            item.classList.remove('active');
        });
        if (clickedItem) clickedItem.classList.add('active');
        
        // Find session data
        const session = _chatState.sessions.find(s => s.session_id === sessionId);
        if (!session) return;
        
        // Update header
        const header = document.querySelector('.chat-viewer-header');
        if (header) {
            const username = document.querySelector('.chat-viewer-username');
            const userId = document.querySelector('.chat-viewer-userid');
            
            if (username) username.textContent = session.username;
            if (userId) userId.textContent = `ID: ${session.user_id}`;
        }
        
        // Load messages
        const msgRes = await fetchJSON(`/api/chat/messages/${sessionId}`);
        if (!msgRes || msgRes.error) {
            messagesContainer.innerHTML = '<div style="padding:12px;color:var(--muted)">Failed to load messages</div>';
            return;
        }
        
        const messages = msgRes.messages || [];
        messagesContainer.innerHTML = '';
        
        if (messages.length === 0) {
            messagesContainer.innerHTML = '<div style="padding:12px;color:var(--muted);text-align:center">No messages yet</div>';
        } else {
            messages.forEach(msg => {
                const msgEl = document.createElement('div');
                msgEl.className = `chat-message ${msg.from === 'admin' ? 'admin' : 'user'}`;
                msgEl.innerHTML = `
                    <div class="msg-content">${escapeHtml(msg.text)}</div>
                    <div class="msg-time">${new Date(msg.ts * 1000).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</div>
                `;
                messagesContainer.appendChild(msgEl);
            });
        }
        
        // Auto-scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        // Update input field data
        const input = document.getElementById('chatInput');
        if (input) input.dataset.sessionId = sessionId;
        
    } catch (e) {
        console.error('[Chat] Open session error:', e);
    }
}

function closeChatViewer() {
    const chatViewer = document.getElementById('chatViewer');
    const emptyState = document.getElementById('chatEmptyState');
    
    if (chatViewer) chatViewer.style.display = 'none';
    if (emptyState) emptyState.style.display = 'flex';
    
    _chatState.currentSessionId = null;
    
    document.querySelectorAll('.chat-session-item').forEach(item => {
        item.classList.remove('active');
    });
}

async function sendChatMessage() {
    try {
        const input = document.getElementById('chatInput');
        if (!input || !input.value.trim()) return;
        
        const sessionId = input.dataset.sessionId;
        if (!sessionId) {
            showToast('Error', 'No session selected', 'err');
            return;
        }
        
        const message = input.value.trim();
        input.value = '';
        
        const res = await postJSON('/api/chat/send', {
            session_id: sessionId,
            message: message
        });
        
        if (res && res.ok) {
            // Reload messages
            const msgRes = await fetchJSON(`/api/chat/messages/${sessionId}`);
            if (msgRes && msgRes.messages) {
                const messagesContainer = document.getElementById('chatMessages');
                messagesContainer.innerHTML = '';
                
                msgRes.messages.forEach(msg => {
                    const msgEl = document.createElement('div');
                    msgEl.className = `chat-message ${msg.from === 'admin' ? 'admin' : 'user'}`;
                    msgEl.innerHTML = `
                        <div class="msg-content">${escapeHtml(msg.text)}</div>
                        <div class="msg-time">${new Date(msg.ts * 1000).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</div>
                    `;
                    messagesContainer.appendChild(msgEl);
                });
                
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
        } else {
            showToast('Error', res?.message || 'Failed to send message', 'err');
        }
    } catch (e) {
        console.error('[Chat] Send message error:', e);
        showToast('Error', 'Failed to send message', 'err');
    }
}

async function resolveChat() {
    try {
        if (!_chatState.currentSessionId) return;
        
        if (!confirm('Mark this chat as resolved?')) return;
        
        const res = await postJSON('/api/chat/resolve', {
            session_id: _chatState.currentSessionId
        });
        
        if (res && res.ok) {
            showToast('Success', 'Chat marked as resolved', 'ok');
            closeChatViewer();
            loadChatSessions();
        } else {
            showToast('Error', res?.message || 'Failed to resolve chat', 'err');
        }
    } catch (e) {
        console.error('[Chat] Resolve error:', e);
        showToast('Error', 'Failed to resolve chat', 'err');
    }
}

// Chat input send button
document.addEventListener('DOMContentLoaded', () => {
    const sendBtn = document.getElementById('chatSendBtn');
    const input = document.getElementById('chatInput');
    const closeBtn = document.getElementById('chatCloseBtn');
    const resolveBtn = document.getElementById('chatResolveBtn');
    
    if (sendBtn) sendBtn.addEventListener('click', sendChatMessage);
    if (input) input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChatMessage();
        }
    });
    if (closeBtn) closeBtn.addEventListener('click', closeChatViewer);
    if (resolveBtn) resolveBtn.addEventListener('click', resolveChat);
});

setInterval(() => {
    refreshNotificationCenter();
}, 7000);

function renderMessageLoggerState(data) {
    const config = data.config || {};
    const toggles = {
        loggerEnabled: 'enabled',
        loggerMentions: 'mentions',
        loggerEdits: 'edits',
        loggerDeletes: 'deletes',
        loggerIgnoreSelf: 'ignore_self',
    };
    for (const [id, key] of Object.entries(toggles)) {
        const input = document.getElementById(id);
        if (input) input.checked = Boolean(config[key]);
    }

    const badge = document.getElementById('loggerStateBadge');
    if (badge) {
        badge.textContent = config.enabled ? 'Enabled' : 'Disabled';
        badge.className = `badge ${config.enabled ? 'badge-ok' : 'badge-off'}`;
    }
    const scopeMode = document.getElementById('loggerScopeMode');
    const scopeId = document.getElementById('loggerScopeId');
    if (scopeMode) scopeMode.value = config.scope?.mode || 'all';
    if (scopeId) {
        scopeId.value = config.scope?.id || '';
        scopeId.hidden = !['guild', 'channel'].includes(scopeMode?.value);
    }

    const keywordList = document.getElementById('loggerKeywordList');
    if (keywordList) {
        keywordList.replaceChildren();
        for (const keyword of config.keywords || []) {
            const chip = document.createElement('span');
            chip.className = 'logger-keyword-chip';
            const label = document.createElement('span');
            label.textContent = keyword;
            const remove = document.createElement('button');
            remove.type = 'button';
            remove.textContent = '×';
            remove.setAttribute('aria-label', `Remove keyword ${keyword}`);
            remove.addEventListener('click', () => removeLoggerKeyword(keyword));
            chip.append(label, remove);
            keywordList.appendChild(chip);
        }
    }

    const feed = Array.isArray(data.feed) ? data.feed : [];
    const feedBody = document.getElementById('loggerFeedBody');
    const count = document.getElementById('loggerFeedCount');
    if (count) count.textContent = `${feed.length} event${feed.length === 1 ? '' : 's'}`;
    if (!feedBody) return;
    feedBody.replaceChildren();
    if (!feed.length) {
        const row = document.createElement('tr');
        const cell = document.createElement('td');
        cell.className = 'empty-row';
        cell.colSpan = 5;
        cell.textContent = config.enabled ? 'No matching events yet.' : 'Logger is disabled.';
        row.appendChild(cell);
        feedBody.appendChild(row);
        return;
    }

    const labels = { mention: 'Mention', keyword: 'Keyword', edit: 'Edited', delete: 'Deleted' };
    for (const item of feed) {
        const row = document.createElement('tr');
        const values = [
            labels[item.kind] || item.kind || 'Event',
            item.author || 'Unknown',
            item.content || (item.kind === 'edit' ? item.after : '') || '(no text)',
            item.guild_id ? `Server ${item.guild_id} · Channel ${item.channel_id}` : `DM · ${item.channel_id}`,
            item.ts ? new Date(Number(item.ts) * 1000).toLocaleString() : '—',
        ];
        for (const value of values) {
            const cell = document.createElement('td');
            cell.textContent = value;
            row.appendChild(cell);
        }
        if (item.before) row.title = `Before edit: ${item.before}`;
        feedBody.appendChild(row);
    }
}

async function loadMessageLogger() {
    const data = await fetchJSON('/api/message-logger');
    if (data?.ok) renderMessageLoggerState(data);
}

async function saveMessageLoggerConfig(config) {
    const data = await postJSON('/api/message-logger', { action: 'config', config });
    if (!data?.ok) {
        showToast('Logger', data?.error || 'Settings could not be saved.', 'err');
        return;
    }
    renderMessageLoggerState(data);
}

async function addLoggerKeyword() {
    const input = document.getElementById('loggerKeywordInput');
    const keyword = (input?.value || '').trim();
    if (!keyword) return;
    const data = await postJSON('/api/message-logger', { action: 'keyword_add', keyword });
    if (!data?.ok) {
        showToast('Logger', data?.error || 'Keyword could not be added.', 'err');
        return;
    }
    input.value = '';
    renderMessageLoggerState(data);
}

async function removeLoggerKeyword(keyword) {
    const data = await postJSON('/api/message-logger', { action: 'keyword_remove', keyword });
    if (data?.ok) renderMessageLoggerState(data);
    else showToast('Logger', data?.error || 'Keyword could not be removed.', 'err');
}

async function clearMessageLoggerFeed() {
    if (!window.confirm('Clear the current message logger feed?')) return;
    const data = await postJSON('/api/message-logger', { action: 'clear' });
    if (data?.ok) renderMessageLoggerState(data);
    else showToast('Logger', data?.error || 'Feed could not be cleared.', 'err');
}

async function refreshMessageLogger() {
    await loadMessageLogger();
}

setInterval(() => {
    if (document.querySelector('.nav-item.active')?.dataset.section === 'logger') {
        loadMessageLogger();
    }
}, 5000);

document.addEventListener('DOMContentLoaded', () => {
    const toggleMap = {
        loggerEnabled: 'enabled',
        loggerMentions: 'mentions',
        loggerEdits: 'edits',
        loggerDeletes: 'deletes',
        loggerIgnoreSelf: 'ignore_self',
    };
    for (const [id, key] of Object.entries(toggleMap)) {
        document.getElementById(id)?.addEventListener('change', event => {
            saveMessageLoggerConfig({ [key]: event.currentTarget.checked });
        });
    }

    const scopeMode = document.getElementById('loggerScopeMode');
    const scopeId = document.getElementById('loggerScopeId');
    const saveScope = () => {
        const mode = scopeMode?.value || 'all';
        if (scopeId) scopeId.hidden = !['guild', 'channel'].includes(mode);
        saveMessageLoggerConfig({ scope: { mode, id: scopeId?.value || '' } });
    };
    scopeMode?.addEventListener('change', saveScope);
    scopeId?.addEventListener('change', saveScope);
    document.getElementById('loggerKeywordInput')?.addEventListener('keydown', event => {
        if (event.key === 'Enter') {
            event.preventDefault();
            addLoggerKeyword();
        }
    });
});
