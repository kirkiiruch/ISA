document.addEventListener('DOMContentLoaded', () => {
    const uploadForm = document.getElementById('upload-form');
    const fileInput = document.getElementById('file-input');
    const uploadBtn = document.getElementById('upload-btn');
    const uploadStatus = document.getElementById('upload-status');
    const documentsTbody = document.getElementById('documents-tbody');

    const askForm = document.getElementById('ask-form');
    const questionInput = document.getElementById('question-input');
    const askBtn = document.getElementById('ask-btn');
    const askError = document.getElementById('ask-error');
    const answerContainer = document.getElementById('answer-container');
    const generatingIndicator = document.getElementById('generating-indicator');
    const answerText = document.getElementById('answer-text');
    const sourcesContainer = document.getElementById('sources-container');
    const sourcesList = document.getElementById('sources-list');

    let pollingTimer = null;
    let eventSource = null;

    // Load initial documents
    loadDocuments();

    // 1. Upload Document
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const file = fileInput.files[0];
        if (!file) return;

        uploadBtn.disabled = true;
        uploadBtn.textContent = 'Завантаження...';
        showUploadStatus('', 'hidden');

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/documents', {
                method: 'POST',
                body: formData,
            });

            if (response.status === 202) {
                showUploadStatus('Файл прийнято на обробку!', 'alert-success');
                fileInput.value = '';
                await loadDocuments();
            } else if (response.status === 409) {
                showUploadStatus('Помилка: файл із таким вмістом уже завантажено (дублікат).', 'alert-error');
            } else if (response.status === 415) {
                showUploadStatus('Помилка: непідтримуваний формат файлу. Дозволено лише .pdf, .txt, .md.', 'alert-error');
            } else if (response.status === 413) {
                showUploadStatus('Помилка: розмір файлу перевищує 10 МБ.', 'alert-error');
            } else {
                const data = await response.json().catch(() => ({}));
                showUploadStatus(`Помилка: ${data.detail || 'Не вдалося завантажити файл.'}`, 'alert-error');
            }
        } catch (err) {
            showUploadStatus(`Мережева помилка: ${err.message}`, 'alert-error');
        } finally {
            uploadBtn.disabled = false;
            uploadBtn.textContent = 'Завантажити файл';
        }
    });

    // 2. Load Documents
    async function loadDocuments() {
        try {
            const response = await fetch('/api/documents');
            if (!response.ok) throw new Error('Не вдалося завантажити документи');
            const docs = await response.json();
            renderDocumentsTable(docs);

            // Check if any document is processing, then poll
            const hasProcessing = docs.some(d => d.status === 'processing');
            if (hasProcessing) {
                if (!pollingTimer) {
                    pollingTimer = setInterval(loadDocuments, 3000);
                }
            } else {
                if (pollingTimer) {
                    clearInterval(pollingTimer);
                    pollingTimer = null;
                }
            }
        } catch (err) {
            console.error(err);
        }
    }

    function renderDocumentsTable(docs) {
        if (!docs || docs.length === 0) {
            documentsTbody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center text-muted">Документів ще не завантажено.</td>
                </tr>
            `;
            return;
        }

        documentsTbody.innerHTML = docs.map(doc => {
            const date = new Date(doc.created_at).toLocaleString('uk-UA');
            let statusBadge = '';
            if (doc.status === 'ready') {
                statusBadge = '<span class="badge badge-ready">ready</span>';
            } else if (doc.status === 'processing') {
                statusBadge = '<span class="badge badge-processing">processing...</span>';
            } else {
                statusBadge = '<span class="badge badge-failed">failed</span>';
            }

            return `
                <tr>
                    <td><strong>${escapeHtml(doc.filename)}</strong></td>
                    <td>${statusBadge}</td>
                    <td>${doc.chunks_count}</td>
                    <td>${date}</td>
                    <td>
                        <button class="btn btn-danger" onclick="deleteDocument('${doc.id}')">Видалити</button>
                    </td>
                </tr>
            `;
        }).join('');
    }

    // 3. Delete Document
    window.deleteDocument = async function(id) {
        if (!confirm('Ви впевнені, що хочете видалити цей документ?')) return;

        try {
            const response = await fetch(`/api/documents/${id}`, {
                method: 'DELETE',
            });
            if (response.ok) {
                await loadDocuments();
            } else {
                const data = await response.json().catch(() => ({}));
                alert(`Помилка видалення: ${data.detail || 'Невідома помилка'}`);
            }
        } catch (err) {
            alert(`Мережева помилка: ${err.message}`);
        }
    };

    // 4. Ask Question with SSE
    askForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const question = questionInput.value.trim();
        if (question.length < 3) {
            showAskError('Запитання має містити щонайменше 3 символи.');
            return;
        }

        hideAskError();
        if (eventSource) {
            eventSource.close();
        }

        askBtn.disabled = true;
        askBtn.textContent = 'Генерація...';
        answerContainer.classList.remove('hidden');
        generatingIndicator.classList.remove('hidden');
        answerText.textContent = '';
        sourcesContainer.classList.add('hidden');
        sourcesList.innerHTML = '';

        const url = `/api/ask/stream?question=${encodeURIComponent(question)}`;
        eventSource = new EventSource(url);

        eventSource.addEventListener('sources', (e) => {
            try {
                const sources = JSON.parse(e.data);
                renderSources(sources);
            } catch (err) {
                console.error('Error parsing sources:', err);
            }
        });

        eventSource.addEventListener('token', (e) => {
            try {
                const data = JSON.parse(e.data);
                if (data.text) {
                    answerText.textContent += data.text;
                }
            } catch (err) {
                console.error('Error parsing token:', err);
            }
        });

        eventSource.addEventListener('done', () => {
            cleanUpSSE();
        });

        eventSource.addEventListener('error', (e) => {
            try {
                if (e.data) {
                    const data = JSON.parse(e.data);
                    showAskError(`Помилка генерації: ${data.error || 'Невідома помилка'}`);
                } else {
                    showAskError('Втрачено з\'єднання із сервером генерації.');
                }
            } catch (err) {
                showAskError('Помилка під час отримання відповіді.');
            }
            cleanUpSSE();
        });

        eventSource.onerror = () => {
            cleanUpSSE();
        };
    });

    function cleanUpSSE() {
        if (eventSource) {
            eventSource.close();
            eventSource = null;
        }
        generatingIndicator.classList.add('hidden');
        askBtn.disabled = false;
        askBtn.textContent = 'Запитати';
    }

    function renderSources(sources) {
        if (!sources || sources.length === 0) {
            sourcesContainer.classList.add('hidden');
            return;
        }

        sourcesContainer.classList.remove('hidden');
        sourcesList.innerHTML = sources.map(s => {
            const pageStr = s.page ? ` (стор. ${s.page})` : '';
            return `
                <div class="source-card">
                    <div class="source-header">
                        <span>📄 ${escapeHtml(s.filename)}${pageStr}</span>
                        <span class="source-score">score: ${s.score}</span>
                    </div>
                    <div class="source-snippet">${escapeHtml(s.snippet)}</div>
                </div>
            `;
        }).join('');
    }

    function showUploadStatus(msg, type) {
        uploadStatus.className = `alert-box ${type}`;
        uploadStatus.textContent = msg;
        if (type === 'hidden') {
            uploadStatus.classList.add('hidden');
        }
    }

    function showAskError(msg) {
        askError.textContent = msg;
        askError.classList.remove('hidden');
    }

    function hideAskError() {
        askError.classList.add('hidden');
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
});
