document.addEventListener('DOMContentLoaded', () => {
    // Елементи інтерфейсу чату
    const askForm = document.getElementById('ask-form');
    const questionInput = document.getElementById('question-input');
    const askBtn = document.getElementById('ask-btn');
    const chatMessages = document.getElementById('chat-messages');
    const welcomeScreen = document.getElementById('welcome-screen');

    // Кнопки та форми файлів
    const uploadForm = document.getElementById('upload-form');
    const fileInput = document.getElementById('file-input');
    const addFileBtn = document.getElementById('add-file-btn');
    const viewFilesBtn = document.getElementById('view-files-btn');
    const topDocsBtn = document.getElementById('top-docs-btn');
    const inputDocsCount = document.getElementById('input-docs-count');
    const topDocsCount = document.getElementById('top-docs-count');

    // Модальне вікно документів
    const docsModal = document.getElementById('docs-modal');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const modalSelectFileBtn = document.getElementById('modal-select-file-btn');
    const documentsTbody = document.getElementById('documents-tbody');
    const toastContainer = document.getElementById('toast-container');

    let pollingTimer = null;
    let eventSource = null;

    // Початкове завантаження списку документів
    loadDocuments();

    // 1. Автоматичний ресайз textarea та обробка Enter
    questionInput.addEventListener('input', () => {
        questionInput.style.height = 'auto';
        questionInput.style.height = Math.min(questionInput.scrollHeight, 140) + 'px';
    });

    questionInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (questionInput.value.trim().length > 0 && !askBtn.disabled) {
                askForm.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
            }
        }
    });

    // 2. Обробка кліку по швидких підказках
    document.querySelectorAll('.quick-prompt-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const query = btn.getAttribute('data-query');
            if (query) {
                questionInput.value = query;
                questionInput.dispatchEvent(new Event('input'));
                askForm.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
            }
        });
    });

    // 3. Відправка запитання та отримання відповіді через SSE
    askForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const question = questionInput.value.trim();
        if (!question) {
            return;
        }

        // Прибираємо вітальний екран
        if (welcomeScreen) {
            welcomeScreen.style.display = 'none';
        }

        // Додаємо повідомлення користувача в чат
        appendUserMessage(question);

        // Очищаємо поле введення
        questionInput.value = '';
        questionInput.style.height = 'auto';
        askBtn.disabled = true;

        // Створюємо блок відповіді моделі з індикатором "Обробка"
        const { messageElement, contentElement } = appendAIMessage();
        let currentSources = [];
        let hasReceivedFirstToken = false;
        let isFinished = false;

        // Підтримка передачі параметра top_k=N з тексту запиту для тестування валідації (422)
        let topKParam = 3;
        let cleanQuestion = question;
        const topKMatch = question.match(/(?:^|\s)top_k=(-?\d+)(?:\s|$)/i);
        if (topKMatch) {
            topKParam = parseInt(topKMatch[1], 10);
            const stripped = question.replace(topKMatch[0], ' ').trim();
            if (stripped.length >= 3) {
                cleanQuestion = stripped;
            }
        }

        const url = `/api/ask/stream?question=${encodeURIComponent(cleanQuestion)}&top_k=${topKParam}&_t=${Date.now()}`;
        if (eventSource) {
            eventSource.close();
        }
        eventSource = new EventSource(url);

        eventSource.addEventListener('sources', (ev) => {
            try {
                currentSources = JSON.parse(ev.data) || [];
            } catch (err) {
                console.error('Помилка парсингу джерел:', err);
            }
        });

        eventSource.addEventListener('token', (ev) => {
            try {
                const data = JSON.parse(ev.data);
                if (data.text) {
                    if (!hasReceivedFirstToken) {
                        contentElement.innerHTML = '';
                        hasReceivedFirstToken = true;
                    }
                    contentElement.textContent += data.text;
                    scrollToBottom();
                }
            } catch (err) {
                console.error('Помилка обробки токена:', err);
            }
        });

        eventSource.addEventListener('done', () => {
            isFinished = true;
            cleanUpSSE();
            // Якщо є джерела — додаємо кнопку зі спливаючим віконцем
            if (currentSources && currentSources.length > 0) {
                renderSourcesButton(messageElement, currentSources);
            }
        });

        eventSource.addEventListener('error', async (ev) => {
            if (isFinished) return;
            cleanUpSSE();
            isFinished = true;

            let errMsg = 'Не вдалося згенерувати відповідь.';
            try {
                if (ev.data) {
                    const data = JSON.parse(ev.data);
                    if (data.error) errMsg = data.error;
                } else if (!hasReceivedFirstToken) {
                    const checkRes = await fetch(url);
                    if (checkRes.status === 422) {
                        errMsg = '422 Unprocessable Entity — Некоректні параметри запиту (питання: 3–1000 символів, top_k: 1–10).';
                    }
                }
            } catch (err) {}

            if (!hasReceivedFirstToken) {
                contentElement.innerHTML = `<span style="color: var(--danger)">Помилка: ${escapeHtml(errMsg)}</span>`;
            }
            showToast(errMsg, 'toast-error');
        });
    });

    function cleanUpSSE() {
        if (eventSource) {
            eventSource.close();
            eventSource = null;
        }
        askBtn.disabled = false;
        questionInput.focus();
    }

    function appendUserMessage(text) {
        const row = document.createElement('div');
        row.className = 'message-row user-row';
        row.innerHTML = `
            <div class="message-bubble">
                <div class="message-content">${escapeHtml(text)}</div>
            </div>
            <div class="avatar user-avatar">👤</div>
        `;
        chatMessages.appendChild(row);
        scrollToBottom();
    }

    function appendAIMessage() {
        const row = document.createElement('div');
        row.className = 'message-row ai-row';
        row.innerHTML = `
            <div class="avatar ai-avatar">✨</div>
            <div class="message-bubble">
                <div class="message-content">
                    <div class="processing-indicator">
                        <span class="processing-pulse"></span>
                        <span>Обробка</span>
                    </div>
                </div>
            </div>
        `;
        chatMessages.appendChild(row);
        scrollToBottom();
        return {
            messageElement: row.querySelector('.message-bubble'),
            contentElement: row.querySelector('.message-content'),
        };
    }

    function renderSourcesButton(bubbleElement, sources) {
        const wrapper = document.createElement('div');
        wrapper.className = 'sources-wrapper';

        const sourcesListHtml = sources.map(s => {
            const pageStr = s.page ? ` (стор. ${s.page})` : '';
            const scoreStr = s.score ? `${(s.score * 100).toFixed(0)}%` : '';
            return `
                <div class="source-item">
                    <div class="source-file">
                        <span>📄 ${escapeHtml(s.filename)}${pageStr}</span>
                        <span class="source-score">${scoreStr}</span>
                    </div>
                    <div class="source-snippet">${escapeHtml(s.snippet)}</div>
                </div>
            `;
        }).join('');

        wrapper.innerHTML = `
            <button type="button" class="sources-btn">
                <span>🔍</span> Джерела (${sources.length})
            </button>
            <div class="sources-popover">
                <div class="popover-title">Використані джерела:</div>
                ${sourcesListHtml}
            </div>
        `;

        bubbleElement.appendChild(wrapper);
        scrollToBottom();
    }

    function scrollToBottom() {
        const viewport = document.querySelector('.chat-viewport');
        if (viewport) {
            viewport.scrollTop = viewport.scrollHeight;
        }
    }

    // 4. Завантаження файлів через кнопки
    addFileBtn.addEventListener('click', () => fileInput.click());
    modalSelectFileBtn.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', async () => {
        const file = fileInput.files[0];
        if (!file) return;

        showToast(`Завантаження: ${file.name}...`, 'toast-info');

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/documents', {
                method: 'POST',
                body: formData,
            });

            if (response.status === 202) {
                showToast(`Файл "${file.name}" прийнято в обробку!`, 'toast-success');
                fileInput.value = '';
                await loadDocuments();
            } else if (response.status === 409) {
                showToast('Помилка: файл із таким вмістом уже завантажено (дублікат).', 'toast-error');
            } else if (response.status === 415) {
                showToast('Помилка: непідтримуваний формат. Дозволено лише .pdf, .txt, .md', 'toast-error');
            } else if (response.status === 413) {
                showToast('Помилка: розмір файлу перевищує 10 МБ.', 'toast-error');
            } else {
                const data = await response.json().catch(() => ({}));
                showToast(`Помилка: ${data.detail || 'Не вдалося завантажити файл.'}`, 'toast-error');
            }
        } catch (err) {
            showToast(`Мережева помилка: ${err.message}`, 'toast-error');
        }
    });

    // 5. Модальне вікно списку документів
    function openModal() {
        docsModal.classList.remove('hidden');
        loadDocuments();
    }

    function closeModal() {
        docsModal.classList.add('hidden');
    }

    viewFilesBtn.addEventListener('click', openModal);
    topDocsBtn.addEventListener('click', openModal);
    closeModalBtn.addEventListener('click', closeModal);

    docsModal.addEventListener('click', (e) => {
        if (e.target === docsModal) closeModal();
    });

    // 6. Отримання та відображення списку документів
    async function loadDocuments() {
        try {
            const response = await fetch('/api/documents');
            if (!response.ok) return;
            const docs = await response.json();
            renderDocumentsTable(docs);

            const countStr = `${docs.length}`;
            if (inputDocsCount) inputDocsCount.textContent = countStr;
            if (topDocsCount) topDocsCount.textContent = countStr;

            // Автополлінг якщо є документи в processing
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
            console.error('Не вдалося завантажити документи:', err);
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
            const date = new Date(doc.created_at).toLocaleDateString('uk-UA');
            let statusBadge = '';
            if (doc.status === 'ready') {
                statusBadge = '<span class="badge-status badge-ready">ready</span>';
            } else if (doc.status === 'processing') {
                statusBadge = '<span class="badge-status badge-processing">processing...</span>';
            } else {
                statusBadge = '<span class="badge-status badge-failed">failed</span>';
            }

            return `
                <tr>
                    <td><strong>${escapeHtml(doc.filename)}</strong></td>
                    <td>${statusBadge}</td>
                    <td>${doc.chunks_count}</td>
                    <td>${date}</td>
                    <td>
                        <button class="btn-del" onclick="deleteDocItem('${doc.id}')">Видалити</button>
                    </td>
                </tr>
            `;
        }).join('');
    }

    // 7. Видалення документа
    window.deleteDocItem = async function(id) {
        if (!confirm('Видалити цей документ та всі його чанки?')) return;

        try {
            const response = await fetch(`/api/documents/${id}`, {
                method: 'DELETE',
            });
            if (response.ok) {
                showToast('Документ успішно видалено', 'toast-info');
                await loadDocuments();
            } else {
                const data = await response.json().catch(() => ({}));
                showToast(`Помилка: ${data.detail || 'Не вдалося видалити'}`, 'toast-error');
            }
        } catch (err) {
            showToast(`Мережева помилка: ${err.message}`, 'toast-error');
        }
    };

    function showToast(message, type = 'toast-info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 200);
        }, 3500);
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
});
