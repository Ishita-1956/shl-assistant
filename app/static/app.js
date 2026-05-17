/**
 * SHL Assessment Assistant — Chat UI Logic
 */
(function () {
    'use strict';

    // ===== State =====
    const state = {
        messages: [],       // { role, content }
        isLoading: false,
        conversationEnded: false
    };

    // ===== DOM Elements =====
    const chatArea = document.getElementById('chat-area');
    const messagesContainer = document.getElementById('messages-container');
    const welcomeScreen = document.getElementById('welcome-screen');
    const messageInput = document.getElementById('message-input');
    const btnSend = document.getElementById('btn-send');
    const btnNewChat = document.getElementById('btn-new-chat');
    const statusText = document.querySelector('.status-text');

    // ===== API =====
    const API_URL = '/chat';

    async function sendChat(messages) {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ messages })
        });

        if (!response.ok) {
            const err = await response.text();
            throw new Error(`API error ${response.status}: ${err}`);
        }

        return response.json();
    }

    // ===== Message Rendering =====
    function renderMessage(role, content, recommendations, endOfConversation) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${role}`;

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = role === 'assistant' ? 'S' : 'U';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        bubble.textContent = content;
        contentDiv.appendChild(bubble);

        // Render recommendations table
        if (recommendations && recommendations.length > 0) {
            const wrapper = document.createElement('div');
            wrapper.className = 'recommendations-wrapper';

            const table = document.createElement('table');
            table.className = 'rec-table';

            // Header
            const thead = document.createElement('thead');
            thead.innerHTML = `
                <tr>
                    <th>#</th>
                    <th>Assessment</th>
                    <th>Type</th>
                    <th>Keys</th>
                    <th>Duration</th>
                    <th>Languages</th>
                </tr>
            `;
            table.appendChild(thead);

            // Body
            const tbody = document.createElement('tbody');
            recommendations.forEach((rec, i) => {
                const tr = document.createElement('tr');

                // Format languages display
                let langsHtml = rec.languages || 'N/A';

                tr.innerHTML = `
                    <td>${i + 1}</td>
                    <td><a href="${escapeHtml(rec.url)}" target="_blank" rel="noopener">${escapeHtml(rec.name)}</a></td>
                    <td><span class="rec-type-badge">${escapeHtml(rec.test_type)}</span></td>
                    <td>${escapeHtml(rec.keys || 'N/A')}</td>
                    <td>${escapeHtml(rec.duration || 'N/A')}</td>
                    <td>${escapeHtml(langsHtml)}</td>
                `;
                tbody.appendChild(tr);
            });
            table.appendChild(tbody);
            wrapper.appendChild(table);
            contentDiv.appendChild(wrapper);
        }

        msgDiv.appendChild(avatar);
        msgDiv.appendChild(contentDiv);
        messagesContainer.appendChild(msgDiv);

        // End of conversation indicator
        if (endOfConversation) {
            const endDiv = document.createElement('div');
            endDiv.className = 'conversation-ended';
            endDiv.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                    <polyline points="22 4 12 14.01 9 11.01"/>
                </svg>
                Conversation complete (shortlist confirmed)
            `;
            messagesContainer.appendChild(endDiv);
        }

        scrollToBottom();
    }

    function showTypingIndicator() {
        const typing = document.createElement('div');
        typing.className = 'typing-indicator';
        typing.id = 'typing-indicator';

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.style.background = 'var(--accent-gradient)';
        avatar.style.color = 'white';
        avatar.textContent = 'S';

        const dots = document.createElement('div');
        dots.className = 'typing-dots';
        dots.innerHTML = '<span></span><span></span><span></span>';

        typing.appendChild(avatar);
        typing.appendChild(dots);
        messagesContainer.appendChild(typing);

        scrollToBottom();
    }

    function removeTypingIndicator() {
        const typing = document.getElementById('typing-indicator');
        if (typing) typing.remove();
    }

    function scrollToBottom() {
        requestAnimationFrame(() => {
            chatArea.scrollTop = chatArea.scrollHeight;
        });
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // ===== Chat Logic =====
    async function handleSend() {
        const text = messageInput.value.trim();
        if (!text || state.isLoading || state.conversationEnded) return;

        // Hide welcome screen
        if (welcomeScreen) {
            welcomeScreen.style.display = 'none';
        }

        // Add user message
        state.messages.push({ role: 'user', content: text });
        renderMessage('user', text, null, false);
        messageInput.value = '';
        autoResize();

        // Loading state
        state.isLoading = true;
        btnSend.disabled = true;
        statusText.textContent = 'Thinking...';
        showTypingIndicator();

        try {
            const response = await sendChat(state.messages);

            removeTypingIndicator();

            // Add assistant message to state
            state.messages.push({ role: 'assistant', content: response.reply });

            // Render
            renderMessage(
                'assistant',
                response.reply,
                response.recommendations,
                response.end_of_conversation
            );

            if (response.end_of_conversation) {
                state.conversationEnded = true;
                messageInput.disabled = true;
                messageInput.placeholder = 'Conversation ended. Click + for a new chat.';
            }

        } catch (err) {
            removeTypingIndicator();
            console.error('Chat error:', err);

            // Show error message
            const msgDiv = document.createElement('div');
            msgDiv.className = 'message assistant';

            const avatar = document.createElement('div');
            avatar.className = 'message-avatar';
            avatar.style.background = 'var(--accent-gradient)';
            avatar.style.color = 'white';
            avatar.textContent = 'S';

            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';

            const bubble = document.createElement('div');
            bubble.className = 'message-bubble error-bubble';
            bubble.textContent = 'Sorry, something went wrong. Please try again.';

            contentDiv.appendChild(bubble);
            msgDiv.appendChild(avatar);
            msgDiv.appendChild(contentDiv);
            messagesContainer.appendChild(msgDiv);

            scrollToBottom();
        } finally {
            state.isLoading = false;
            btnSend.disabled = false;
            statusText.textContent = 'Online';
        }
    }

    function resetChat() {
        state.messages = [];
        state.isLoading = false;
        state.conversationEnded = false;

        messagesContainer.innerHTML = '';

        if (welcomeScreen) {
            welcomeScreen.style.display = '';
        }

        messageInput.disabled = false;
        messageInput.placeholder = 'Describe your hiring need...';
        messageInput.value = '';
        messageInput.focus();
    }

    // ===== Auto-resize textarea =====
    function autoResize() {
        messageInput.style.height = 'auto';
        messageInput.style.height = Math.min(messageInput.scrollHeight, 150) + 'px';
    }

    // ===== Event Listeners =====
    btnSend.addEventListener('click', handleSend);

    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    });

    messageInput.addEventListener('input', autoResize);

    btnNewChat.addEventListener('click', resetChat);

    // Quick prompts
    document.querySelectorAll('.quick-prompt').forEach(btn => {
        btn.addEventListener('click', () => {
            messageInput.value = btn.dataset.prompt;
            autoResize();
            handleSend();
        });
    });

    // Focus input on load
    messageInput.focus();

})();
