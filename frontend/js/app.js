/**
 * STOCKMAN - Main Application JavaScript
 * Handles chat, voice, settings, and API interactions
 */

// ============================================
// Configuration
// ============================================

const API_BASE = '';  // Same origin

// ============================================
// State
// ============================================

let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];
let currentVoiceMode = null;  // 'chat' or 'text'

// ============================================
// DOM Elements
// ============================================

const elements = {
    // Chat
    chatContainer: document.getElementById('chat-container'),
    messages: document.getElementById('messages'),
    messageInput: document.getElementById('message-input'),
    sendBtn: document.getElementById('send-btn'),

    // Briefing
    briefingCard: document.getElementById('briefing-card'),
    quoteText: document.getElementById('quote-text'),
    quoteAuthor: document.getElementById('quote-author'),
    briefingContent: document.getElementById('briefing-content'),

    // Voice
    voiceChatBtn: document.getElementById('voice-chat-btn'),
    voiceTextBtn: document.getElementById('voice-text-btn'),
    voiceModal: document.getElementById('voice-modal'),
    voiceStatus: document.getElementById('voice-status'),
    stopVoiceBtn: document.getElementById('stop-voice-btn'),

    // Settings
    settingsBtn: document.getElementById('settings-btn'),
    settingsModal: document.getElementById('settings-modal'),
    closeSettings: document.getElementById('close-settings'),
    tabBtns: document.querySelectorAll('.tab-btn'),
    portfolioList: document.getElementById('portfolio-list'),
    watchlistList: document.getElementById('watchlist-list'),

    // Portfolio inputs
    portfolioTicker: document.getElementById('portfolio-ticker'),
    portfolioShares: document.getElementById('portfolio-shares'),
    portfolioPrice: document.getElementById('portfolio-price'),
    addPortfolioBtn: document.getElementById('add-portfolio-btn'),

    // Watchlist inputs
    watchlistTicker: document.getElementById('watchlist-ticker'),
    addWatchlistBtn: document.getElementById('add-watchlist-btn'),

    // Profile
    userName: document.getElementById('user-name'),
    saveProfileBtn: document.getElementById('save-profile-btn'),
    enableNotificationsBtn: document.getElementById('enable-notifications-btn'),

    // Loading
    loading: document.getElementById('loading')
};

// ============================================
// Initialization
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    loadBriefing();
    loadSettings();
    registerServiceWorker();
});

function initEventListeners() {
    // Send message
    elements.sendBtn.addEventListener('click', sendMessage);
    elements.messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Voice buttons
    elements.voiceChatBtn.addEventListener('click', () => startVoice('chat'));
    elements.voiceTextBtn.addEventListener('click', () => startVoice('text'));
    elements.stopVoiceBtn.addEventListener('click', stopVoice);

    // Settings
    elements.settingsBtn.addEventListener('click', openSettings);
    elements.closeSettings.addEventListener('click', closeSettings);
    elements.settingsModal.querySelector('.modal-overlay').addEventListener('click', closeSettings);

    // Tabs
    elements.tabBtns.forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    // Portfolio
    elements.addPortfolioBtn.addEventListener('click', addToPortfolio);
    elements.portfolioTicker.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') addToPortfolio();
    });

    // Watchlist
    elements.addWatchlistBtn.addEventListener('click', addToWatchlist);
    elements.watchlistTicker.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') addToWatchlist();
    });

    // Profile
    elements.saveProfileBtn.addEventListener('click', saveProfile);
    elements.enableNotificationsBtn.addEventListener('click', requestNotificationPermission);

    // Voice modal overlay
    elements.voiceModal.querySelector('.modal-overlay').addEventListener('click', stopVoice);
}

// ============================================
// Chat Functions
// ============================================

async function sendMessage() {
    const message = elements.messageInput.value.trim();
    if (!message) return;

    // Clear input
    elements.messageInput.value = '';

    // Add user message to UI
    addMessage('user', message);

    // Show loading
    showLoading();

    try {
        const response = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, is_voice: false })
        });

        const data = await response.json();

        if (data.reply) {
            addMessage('assistant', data.reply);
        }
    } catch (error) {
        console.error('Chat error:', error);
        addMessage('assistant', 'Sorry, I encountered an error. Please try again.');
    } finally {
        hideLoading();
    }
}

function addMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    messageDiv.innerHTML = `
        <div class="message-content">${escapeHtml(content)}</div>
        <div class="message-time">${time}</div>
    `;

    elements.messages.appendChild(messageDiv);

    // Scroll to bottom
    elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
}

// ============================================
// Voice Functions
// ============================================

async function startVoice(mode) {
    currentVoiceMode = mode;

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = (e) => {
            audioChunks.push(e.data);
        };

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            await processVoice(audioBlob, mode);

            // Stop all tracks
            stream.getTracks().forEach(track => track.stop());
        };

        mediaRecorder.start();
        isRecording = true;

        // Show voice modal
        elements.voiceModal.classList.remove('hidden');
        elements.voiceStatus.textContent = mode === 'chat'
            ? 'Listening... Talk to Stockman'
            : 'Listening... Speak your message';

    } catch (error) {
        console.error('Microphone error:', error);
        alert('Could not access microphone. Please check permissions.');
    }
}

function stopVoice() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
    }

    elements.voiceModal.classList.add('hidden');
}

async function processVoice(audioBlob, mode) {
    showLoading();

    try {
        // Transcribe audio
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.webm');

        const transcribeResponse = await fetch(`${API_BASE}/api/voice/transcribe`, {
            method: 'POST',
            body: formData
        });

        const { text } = await transcribeResponse.json();

        if (!text) {
            hideLoading();
            return;
        }

        if (mode === 'text') {
            // Voice to text - just put in input
            elements.messageInput.value = text;
            hideLoading();
        } else {
            // Voice chat - send message and get audio response
            addMessage('user', text);

            const chatResponse = await fetch(`${API_BASE}/api/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text, is_voice: true })
            });

            const { reply } = await chatResponse.json();
            addMessage('assistant', reply);

            // Synthesize speech
            await speakResponse(reply);
        }
    } catch (error) {
        console.error('Voice processing error:', error);
        addMessage('assistant', 'Sorry, I had trouble understanding that. Please try again.');
    } finally {
        hideLoading();
    }
}

async function speakResponse(text) {
    try {
        const response = await fetch(`${API_BASE}/api/voice/synthesize`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });

        const { audio } = await response.json();

        if (audio) {
            // Convert hex to ArrayBuffer
            const bytes = new Uint8Array(audio.match(/.{1,2}/g).map(byte => parseInt(byte, 16)));
            const audioBlob = new Blob([bytes], { type: 'audio/mpeg' });
            const audioUrl = URL.createObjectURL(audioBlob);

            const audioElement = new Audio(audioUrl);
            audioElement.play();
        }
    } catch (error) {
        console.error('Speech synthesis error:', error);
    }
}

// ============================================
// Briefing Functions
// ============================================

async function loadBriefing() {
    try {
        const response = await fetch(`${API_BASE}/api/briefing`);
        const data = await response.json();

        if (data.quote) {
            elements.quoteText.textContent = `"${data.quote.quote}"`;
            elements.quoteAuthor.textContent = `— ${data.quote.author}`;
        }

        if (data.briefing_text) {
            elements.briefingContent.textContent = data.briefing_text;
        }

        if (data.greeting) {
            // Could show greeting somewhere
        }

        elements.briefingCard.classList.remove('hidden');

    } catch (error) {
        console.error('Briefing error:', error);
        // Hide briefing card on error
    }
}

// ============================================
// Settings Functions
// ============================================

function openSettings() {
    elements.settingsModal.classList.remove('hidden');
    loadPortfolio();
    loadWatchlist();
    loadProfile();
}

function closeSettings() {
    elements.settingsModal.classList.add('hidden');
}

function switchTab(tabName) {
    // Update tab buttons
    elements.tabBtns.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.add('hidden');
        content.classList.remove('active');
    });

    const activeTab = document.getElementById(`${tabName}-tab`);
    if (activeTab) {
        activeTab.classList.remove('hidden');
        activeTab.classList.add('active');
    }
}

async function loadPortfolio() {
    try {
        const response = await fetch(`${API_BASE}/api/portfolio`);
        const { portfolio } = await response.json();

        elements.portfolioList.innerHTML = portfolio.length ? '' : `
            <div class="empty-state">
                <p>No stocks in portfolio yet. Add some below!</p>
            </div>
        `;

        portfolio.forEach(stock => {
            const item = document.createElement('div');
            item.className = 'stock-item';
            item.innerHTML = `
                <div class="stock-info">
                    <span class="stock-ticker">${stock.ticker}</span>
                    <span class="stock-details">${stock.shares || 0} shares @ $${stock.avg_price || 0}</span>
                </div>
                <button class="remove-btn" onclick="removeFromPortfolio('${stock.ticker}')">Remove</button>
            `;
            elements.portfolioList.appendChild(item);
        });
    } catch (error) {
        console.error('Load portfolio error:', error);
    }
}

async function addToPortfolio() {
    const ticker = elements.portfolioTicker.value.trim().toUpperCase();
    const shares = parseFloat(elements.portfolioShares.value) || 0;
    const price = parseFloat(elements.portfolioPrice.value) || 0;

    if (!ticker) return;

    try {
        await fetch(`${API_BASE}/api/portfolio/add`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker, shares, price })
        });

        elements.portfolioTicker.value = '';
        elements.portfolioShares.value = '';
        elements.portfolioPrice.value = '';

        loadPortfolio();
    } catch (error) {
        console.error('Add portfolio error:', error);
    }
}

async function removeFromPortfolio(ticker) {
    try {
        await fetch(`${API_BASE}/api/portfolio/${ticker}`, { method: 'DELETE' });
        loadPortfolio();
    } catch (error) {
        console.error('Remove portfolio error:', error);
    }
}

async function loadWatchlist() {
    try {
        const response = await fetch(`${API_BASE}/api/watchlist`);
        const { watchlist } = await response.json();

        elements.watchlistList.innerHTML = watchlist.length ? '' : `
            <div class="empty-state">
                <p>No stocks in watchlist. Add some to track!</p>
            </div>
        `;

        watchlist.forEach(stock => {
            const item = document.createElement('div');
            item.className = 'stock-item';
            item.innerHTML = `
                <div class="stock-info">
                    <span class="stock-ticker">${stock.ticker}</span>
                    <span class="stock-details">Added ${new Date(stock.added_at).toLocaleDateString()}</span>
                </div>
                <button class="remove-btn" onclick="removeFromWatchlist('${stock.ticker}')">Remove</button>
            `;
            elements.watchlistList.appendChild(item);
        });
    } catch (error) {
        console.error('Load watchlist error:', error);
    }
}

async function addToWatchlist() {
    const ticker = elements.watchlistTicker.value.trim().toUpperCase();
    if (!ticker) return;

    try {
        await fetch(`${API_BASE}/api/watchlist/add`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker })
        });

        elements.watchlistTicker.value = '';
        loadWatchlist();
    } catch (error) {
        console.error('Add watchlist error:', error);
    }
}

async function removeFromWatchlist(ticker) {
    try {
        await fetch(`${API_BASE}/api/watchlist/${ticker}`, { method: 'DELETE' });
        loadWatchlist();
    } catch (error) {
        console.error('Remove watchlist error:', error);
    }
}

async function loadProfile() {
    try {
        const response = await fetch(`${API_BASE}/api/settings`);
        const profile = await response.json();

        if (profile.name) {
            elements.userName.value = profile.name;
        }
    } catch (error) {
        console.error('Load profile error:', error);
    }
}

async function saveProfile() {
    const name = elements.userName.value.trim();
    if (!name) return;

    try {
        await fetch(`${API_BASE}/api/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });

        alert('Profile saved!');
    } catch (error) {
        console.error('Save profile error:', error);
    }
}

function loadSettings() {
    // Check notification permission
    if (Notification.permission === 'granted') {
        elements.enableNotificationsBtn.textContent = 'Notifications Enabled';
        elements.enableNotificationsBtn.disabled = true;
    }
}

// ============================================
// Push Notifications
// ============================================

async function registerServiceWorker() {
    if ('serviceWorker' in navigator) {
        try {
            const registration = await navigator.serviceWorker.register('/sw.js');
            console.log('Service Worker registered:', registration);
        } catch (error) {
            console.error('Service Worker registration failed:', error);
        }
    }
}

async function requestNotificationPermission() {
    if (!('Notification' in window)) {
        alert('This browser does not support notifications.');
        return;
    }

    const permission = await Notification.requestPermission();

    if (permission === 'granted') {
        elements.enableNotificationsBtn.textContent = 'Notifications Enabled';
        elements.enableNotificationsBtn.disabled = true;

        // Show test notification
        new Notification('Stockman', {
            body: 'Notifications are now enabled! You\'ll receive your morning briefing at 8 AM.',
            icon: '/icons/icon-192.png'
        });
    }
}

// ============================================
// Utilities
// ============================================

function showLoading() {
    elements.loading.classList.remove('hidden');
}

function hideLoading() {
    elements.loading.classList.add('hidden');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Make functions globally available for onclick handlers
window.removeFromPortfolio = removeFromPortfolio;
window.removeFromWatchlist = removeFromWatchlist;
