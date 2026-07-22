const protocolModal = document.querySelector('[data-testid="protocol-modal"]');
const showProtocolButton = document.querySelector('[data-testid="show-protocol"]');
const closeProtocolButton = document.querySelector('[data-testid="close-protocol"]');
const evidenceButton = document.querySelector('[data-testid="toggle-evidence"]');
const evidencePanel = document.querySelector('[data-testid="evidence-panel"]');
const acceptButton = document.querySelector('[data-testid="accept-sample"]');
const acceptanceToast = document.querySelector('[data-testid="acceptance-toast"]');

function openProtocol() {
  protocolModal.hidden = false;
  document.body.style.overflow = 'hidden';
  closeProtocolButton.focus();
}

function closeProtocol() {
  protocolModal.hidden = true;
  document.body.style.overflow = '';
  showProtocolButton.focus();
}

showProtocolButton.addEventListener('click', openProtocol);
closeProtocolButton.addEventListener('click', closeProtocol);

protocolModal.addEventListener('click', (event) => {
  if (event.target === protocolModal) closeProtocol();
});

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && !protocolModal.hidden) closeProtocol();
});

evidenceButton.addEventListener('click', () => {
  const willOpen = evidencePanel.hidden;
  evidencePanel.hidden = !willOpen;
  evidenceButton.setAttribute('aria-expanded', String(willOpen));
  evidenceButton.innerHTML = willOpen
    ? '收起计算证据 <span aria-hidden="true">↑</span>'
    : '展开计算证据 <span aria-hidden="true">↓</span>';
});

let toastTimer;
acceptButton.addEventListener('click', () => {
  acceptButton.textContent = '样例已标记通过';
  acceptButton.disabled = true;
  acceptanceToast.hidden = false;
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => {
    acceptanceToast.hidden = true;
  }, 2600);
});
