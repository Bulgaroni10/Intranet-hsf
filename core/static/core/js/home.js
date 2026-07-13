const UNITS = {
  HMSF: 'Hospital e Maternidade São Francisco',
  HSFVF: 'Hospital Sagrada Família Vila Formosa',
  HSFMA: 'Hospital Sagrada Família Mauá',
  HSFSR: 'Hospital São Francisco São Roque',
  HSFOS: 'Hospital São Francisco Osasco',
  HSFCA: 'Hospital São Francisco Carapicuíba',
  OPS: 'Operadora / Plano de Saúde'
};

const UNIT_LOGOS = {
  HMSF: '/static/core/img/logo-hsf.png',
  HSFVF: '/static/core/img/logo-sagrada-familia.png',
  HSFMA: '/static/core/img/logo-sagrada-familia.png',
  HSFSR: '/static/core/img/logo-hsf.png',
  HSFOS: '/static/core/img/logo-hsf.png',
  HSFCA: '/static/core/img/logo-hsf.png',
  OPS: '/static/core/img/logo-hsf.png'
};

function getCsrfToken() {
  const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');

  if (csrfInput) {
    return csrfInput.value;
  }

  return '';
}

async function ensureGlobalSidebar() {
  if (
    document.querySelector('.gsf-sidebar') ||
    document.getElementById('login-screen') ||
    window.location.pathname === '/'
  ) {
    return;
  }

  try {
    const response = await fetch('/portal/sidebar/', {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });

    if (!response.ok || response.redirected) return;

    const sidebarHtml = await response.text();
    if (!sidebarHtml.includes('gsf-sidebar')) return;

    document.body.insertAdjacentHTML('afterbegin', sidebarHtml);
    document.body.classList.add('gsf-legacy-with-sidebar');
  } catch (error) {
    console.error('Erro ao carregar a sidebar global:', error);
  }
}

function updateLoginLogo() {
  const unitSelect = document.getElementById('sel-unidade');
  const loginLogo = document.getElementById('login-unit-logo');

  if (!unitSelect || !loginLogo) return;

  const unit = unitSelect.value;

  if (unit && UNIT_LOGOS[unit]) {
    loginLogo.src = UNIT_LOGOS[unit];
  } else {
    loginLogo.src = UNIT_LOGOS.HMSF;
  }
}

function showLoginError(message) {
  const err = document.getElementById('err-msg');

  if (!err) return;

  err.textContent = `⚠ ${message}`;
  err.classList.add('show');
}

function hideLoginError() {
  const err = document.getElementById('err-msg');

  if (!err) return;

  err.classList.remove('show');
}

async function doLogin() {
  const userInput = document.getElementById('inp-user');
  const passwordInput = document.getElementById('inp-pw');

  const user = userInput ? userInput.value.trim().toLowerCase() : '';
  const pw = passwordInput ? passwordInput.value : '';

  if (!user || !pw) {
    showLoginError('Preencha usuário e senha.');
    return;
  }

  hideLoginError();

  try {
    const response = await fetch('/login/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken()
      },
      body: JSON.stringify({
        username: user,
        password: pw
      })
    });

    const data = await response.json();

    if (!response.ok || !data.ok) {
      showLoginError(data.message || 'Não foi possível realizar o login.');
      return;
    }

    if (data.user && data.user.primeiro_acesso) {
      alert('Primeiro acesso identificado. Em breve vamos direcionar para troca obrigatória de senha.');
    }

    window.location.href = data.redirect_url || '/portal/';

  } catch (error) {
    showLoginError('Erro ao comunicar com o servidor.');
    console.error(error);
  }
}

async function doLogout() {
  try {
    const response = await fetch('/logout/', {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCsrfToken()
      }
    });

    const data = await response.json();

    window.location.href = data.redirect_url || '/';

  } catch (error) {
    console.error(error);
    window.location.href = '/';
  }
}

function normalizeText(text) {
  return text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim();
}

function filterModules(query) {
  const q = normalizeText(query);
  const cards = document.querySelectorAll('.card');

  let visibleCards = 0;

  cards.forEach(card => {
    const content = normalizeText(`${card.textContent} ${card.dataset.module || ''}`);
    const match = !q || content.includes(q);

    card.style.display = match ? '' : 'none';

    if (match) {
      visibleCards++;
    }
  });

  document.querySelectorAll('.category-section').forEach(section => {
    const hasVisibleCard = Array.from(section.querySelectorAll('.card'))
      .some(card => card.style.display !== 'none');

    section.style.display = hasVisibleCard ? '' : 'none';
  });

  const noResults = document.getElementById('no-results');

  if (noResults) {
    noResults.style.display = visibleCards === 0 ? 'block' : 'none';
  }
}

function injectChatBadgeStyle() {
  if (document.getElementById('chat-badge-style')) return;

  const style = document.createElement('style');
  style.id = 'chat-badge-style';

  style.textContent = `
    .chat-unread-badge {
      display: none;
      align-items: center;
      justify-content: center;
      min-width: 18px;
      height: 18px;
      padding: 0 6px;
      margin-left: 6px;
      border-radius: 999px;
      background: #ef4444;
      color: #ffffff;
      font-size: 11px;
      font-weight: 900;
      line-height: 1;
      box-shadow: 0 0 0 2px rgba(15, 15, 15, 0.95);
    }

    .chat-unread-badge.show {
      display: inline-flex;
    }

    .top-chat-btn,
    .quick-action[href="/conversas/"] {
      position: relative;
    }
  `;

  document.head.appendChild(style);
}

function getChatButtons() {
  return Array.from(document.querySelectorAll('a[href="/conversas/"]'));
}

function ensureChatBadge(button) {
  let badge = button.querySelector('.chat-unread-badge');

  if (!badge) {
    badge = document.createElement('span');
    badge.className = 'chat-unread-badge';
    badge.setAttribute('aria-label', 'Conversas não lidas');
    button.appendChild(badge);
  }

  return badge;
}

function updateChatUnreadBadge(total) {
  const buttons = getChatButtons();

  buttons.forEach(button => {
    const badge = ensureChatBadge(button);

    if (total > 0) {
      badge.textContent = total > 99 ? '99+' : String(total);
      badge.classList.add('show');
      button.setAttribute('title', `${total} conversa(s) não lida(s)`);
    } else {
      badge.textContent = '';
      badge.classList.remove('show');
      button.removeAttribute('title');
    }
  });
}

async function carregarContadorConversasNaoLidas() {
  const buttons = getChatButtons();

  if (!buttons.length) return;

  try {
    const response = await fetch('/conversas/contador-nao-lidas/', {
      method: 'GET',
      headers: {
        'X-Requested-With': 'XMLHttpRequest'
      }
    });

    if (!response.ok) return;

    const data = await response.json();

    if (!data.ok) return;

    updateChatUnreadBadge(Number(data.total || 0));

  } catch (error) {
    console.error('Erro ao carregar contador de conversas não lidas:', error);
  }
}

document.addEventListener('DOMContentLoaded', function () {
  const searchInput = document.getElementById('search-input');
  const passwordInput = document.getElementById('inp-pw');
  const unitSelect = document.getElementById('sel-unidade');

  if (searchInput) {
    searchInput.addEventListener('input', function () {
      filterModules(this.value);
    });
  }

  if (passwordInput) {
    passwordInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        doLogin();
      }
    });
  }

  if (unitSelect) {
    unitSelect.addEventListener('change', updateLoginLogo);
    updateLoginLogo();
  }

  ensureGlobalSidebar().then(carregarContadorConversasNaoLidas);
  injectChatBadgeStyle();
  carregarContadorConversasNaoLidas();

  setInterval(function () {
    carregarContadorConversasNaoLidas();
  }, 10000);
});
