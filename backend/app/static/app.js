const rows = document.getElementById('rows');
const addRowBtn = document.getElementById('add-row');
const form = document.getElementById('analyze-form');
const resultsEl = document.getElementById('results');
const toast = document.getElementById('toast');
const rowTemplate = document.getElementById('row-template');
const resultTemplate = document.getElementById('result-template');
const uploadForm = document.getElementById('upload-form');
const uploadFile = document.getElementById('upload-file');
const uploadMinute = document.getElementById('upload-minute');

const showToast = (message) => {
  toast.textContent = message;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 2000);
};

const addRow = (url = '', minute = 10) => {
  const node = rowTemplate.content.cloneNode(true);
  const row = node.querySelector('.row');
  const urlInput = row.querySelector('input[type="url"]');
  const minuteInput = row.querySelector('input[type="number"]');
  const removeBtn = row.querySelector('.remove');

  urlInput.value = url;
  minuteInput.value = minute;

  removeBtn.addEventListener('click', () => {
    row.remove();
  });

  rows.appendChild(node);
};

const buildPayload = () => {
  const items = [];
  rows.querySelectorAll('.row').forEach((row) => {
    const url = row.querySelector('input[type="url"]').value.trim();
    const startMinute = Number(row.querySelector('input[type="number"]').value || 10);
    if (url) {
      items.push({ url, start_minute: startMinute });
    }
  });
  return { items };
};

const formatScore = (value) => `${Number(value).toFixed(2)}%`;

const createResultCard = (result) => {
  const node = resultTemplate.content.cloneNode(true);
  const container = node.querySelector('.result');
  const title = node.querySelector('.result-title');
  const subtitle = node.querySelector('.result-subtitle');
  const melody = node.querySelector('.melody');
  const frequency = node.querySelector('.frequency');
  const combined = node.querySelector('.combined');
  const audio = node.querySelector('audio');
  const shareBtn = node.querySelector('.share');

  title.textContent = result.url;
  subtitle.textContent = `Segment analysé : ${result.start_minute} → ${result.end_minute} min`;
  melody.textContent = formatScore(result.melody_score);
  frequency.textContent = formatScore(result.frequency_score);
  combined.textContent = formatScore(result.combined_score);
  audio.src = result.audio_url;

  shareBtn.addEventListener('click', async () => {
    const text = `Résultat prosodie\n${result.url}\nMélodie: ${formatScore(result.melody_score)}\nFréquence: ${formatScore(result.frequency_score)}\nProsodie globale: ${formatScore(result.combined_score)}`;
    if (navigator.share) {
      try {
        await navigator.share({ title: 'Prosodie', text, url: window.location.href });
      } catch (err) {
        showToast('Partage annulé.');
      }
      return;
    }

    try {
      await navigator.clipboard.writeText(text);
      showToast('Résultat copié dans le presse-papiers.');
    } catch (err) {
      showToast('Impossible de copier le résultat.');
    }
  });

  resultsEl.appendChild(container);
};

addRow();

addRowBtn.addEventListener('click', () => addRow());

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  resultsEl.innerHTML = '';

  const payload = buildPayload();
  if (!payload.items.length) {
    showToast('Ajoutez au moins un lien.');
    return;
  }

  const submitBtn = form.querySelector('button[type="submit"]');
  submitBtn.disabled = true;
  submitBtn.textContent = 'Analyse en cours...';

  try {
    const response = await fetch('/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Erreur lors de l’analyse.');
    }

    const data = await response.json();
    data.results.forEach(createResultCard);
  } catch (err) {
    showToast(err.message);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Analyser la prosodie';
  }
});

uploadForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  resultsEl.innerHTML = '';

  if (!uploadFile.files.length) {
    showToast('Choisissez un fichier audio.');
    return;
  }

  const formData = new FormData();
  formData.append('file', uploadFile.files[0]);
  formData.append('start_minute', uploadMinute.value || '10');

  const submitBtn = uploadForm.querySelector('button[type="submit"]');
  submitBtn.disabled = true;
  submitBtn.textContent = 'Analyse en cours...';

  try {
    const response = await fetch('/analyze-upload', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Erreur lors de l’analyse.');
    }

    const data = await response.json();
    data.results.forEach(createResultCard);
  } catch (err) {
    showToast(err.message);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Analyser le MP3';
  }
});
