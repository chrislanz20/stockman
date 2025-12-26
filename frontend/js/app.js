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

    // Welcome card
    welcomeCard: document.getElementById('welcome-card'),

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

    // Typing indicator
    typingIndicator: document.getElementById('typing-indicator')
};

// ============================================
// Initialization
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    initNavigation();
    loadSettings();
    registerServiceWorker();
    loadUserGreeting();
    checkMorningWisdom();
    loadTicker();
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

    // Show typing indicator
    showTyping();

    try {
        const response = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, is_voice: false })
        });

        const data = await response.json();

        // Hide typing before showing response
        hideTyping();

        if (data.reply) {
            addMessage('assistant', data.reply);
        }
    } catch (error) {
        console.error('Chat error:', error);
        hideTyping();
        addMessage('assistant', 'Sorry, I encountered an error. Please try again.');
    }
}

function addMessage(role, content) {
    // Hide welcome card when first message is sent
    if (elements.welcomeCard && !elements.welcomeCard.classList.contains('hidden')) {
        elements.welcomeCard.classList.add('hidden');
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // Format assistant messages with markdown, escape user messages
    const formattedContent = role === 'assistant'
        ? formatMessage(content)
        : `<p>${content.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</p>`;

    messageDiv.innerHTML = `
        <div class="message-content">${formattedContent}</div>
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

            // Update status before processing
            elements.voiceStatus.textContent = 'Processing...';

            await processVoice(audioBlob, mode);

            // Stop all tracks
            stream.getTracks().forEach(track => track.stop());

            // Hide modal after processing
            elements.voiceModal.classList.add('hidden');
        };

        mediaRecorder.start();
        isRecording = true;

        // Show voice modal with clear instructions
        elements.voiceModal.classList.remove('hidden');
        elements.voiceStatus.textContent = mode === 'chat'
            ? '🎤 Listening... Tap to stop'
            : '🎤 Speak your message... Tap to stop';

    } catch (error) {
        console.error('Microphone error:', error);
        alert('Could not access microphone. Please check your browser permissions and try again.');
    }
}

function stopVoice() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
    }
}

async function processVoice(audioBlob, mode) {
    showTyping();

    try {
        // Transcribe audio using Whisper API
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.webm');

        const transcribeResponse = await fetch(`${API_BASE}/api/voice/transcribe`, {
            method: 'POST',
            body: formData
        });

        if (!transcribeResponse.ok) {
            throw new Error('Transcription failed');
        }

        const { text } = await transcribeResponse.json();

        if (!text || text.trim() === '') {
            hideTyping();
            addMessage('assistant', "I didn't catch that. Please try speaking again.");
            return;
        }

        if (mode === 'text') {
            // Voice to text - put in input and focus
            elements.messageInput.value = text;
            elements.messageInput.focus();
            hideTyping();
        } else {
            // Voice chat - send message and get audio response
            hideTyping();
            addMessage('user', text);
            showTyping();

            const chatResponse = await fetch(`${API_BASE}/api/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text, is_voice: true })
            });

            const { reply } = await chatResponse.json();
            hideTyping();
            addMessage('assistant', reply);

            // Speak the response
            await speakResponse(reply);
        }
    } catch (error) {
        console.error('Voice processing error:', error);
        hideTyping();

        // Try browser fallback for voice-to-text
        if (mode === 'text') {
            addMessage('assistant', 'Voice service temporarily unavailable. Please type your message.');
        } else {
            addMessage('assistant', 'Sorry, I had trouble with the voice service. Please try again or type your message.');
        }
    }
}

async function speakResponse(text) {
    try {
        // Try ElevenLabs API first
        const response = await fetch(`${API_BASE}/api/voice/synthesize`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });

        if (response.ok) {
            const { audio } = await response.json();

            if (audio) {
                // Convert hex to ArrayBuffer and play
                const bytes = new Uint8Array(audio.match(/.{1,2}/g).map(byte => parseInt(byte, 16)));
                const audioBlob = new Blob([bytes], { type: 'audio/mpeg' });
                const audioUrl = URL.createObjectURL(audioBlob);

                const audioElement = new Audio(audioUrl);
                await audioElement.play();
                return;
            }
        }

        // Fallback to browser speech synthesis
        useBrowserSpeech(text);

    } catch (error) {
        console.error('ElevenLabs error, using browser fallback:', error);
        useBrowserSpeech(text);
    }
}

function useBrowserSpeech(text) {
    // Fallback to browser's built-in speech synthesis
    if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        utterance.volume = 1.0;

        // Try to use a natural voice
        const voices = speechSynthesis.getVoices();
        const preferredVoice = voices.find(v =>
            v.name.includes('Samantha') ||
            v.name.includes('Google') ||
            v.name.includes('Microsoft')
        );
        if (preferredVoice) {
            utterance.voice = preferredVoice;
        }

        speechSynthesis.speak(utterance);
    }
}

// ============================================
// Welcome & Greeting Functions
// ============================================

async function loadUserGreeting() {
    try {
        const response = await fetch(`${API_BASE}/api/settings`);
        const profile = await response.json();

        const greetingEl = document.getElementById('welcome-greeting');
        if (greetingEl && profile.name && profile.name !== 'Friend') {
            greetingEl.querySelector('h2').textContent = `Hey ${profile.name}! I'm Stockman.`;
        }
    } catch (error) {
        console.error('Greeting error:', error);
    }
}

async function checkMorningWisdom() {
    // Check if it's morning (7:00 AM - 9:00 AM)
    const hour = new Date().getHours();
    const minute = new Date().getMinutes();

    // Target: around 7:50 AM, but check window of 7:00-9:00
    if (hour < 7 || hour >= 9) return;

    // Check if we've already shown today's wisdom
    const today = new Date().toDateString();
    const lastShown = localStorage.getItem('stockman_wisdom_date');

    if (lastShown === today) return;

    // Check notification permission
    if (Notification.permission !== 'granted') return;

    try {
        const response = await fetch(`${API_BASE}/api/morning-wisdom`);
        const data = await response.json();

        if (data.wisdom) {
            // Show the notification
            new Notification('Good Morning ☀️', {
                body: data.wisdom,
                icon: '/icons/icon-192.png',
                tag: 'morning-wisdom',
                requireInteraction: false
            });

            // Mark as shown for today
            localStorage.setItem('stockman_wisdom_date', today);
        }
    } catch (error) {
        console.error('Morning wisdom error:', error);
    }
}

function openSettingsToTab(tabName) {
    elements.settingsModal.classList.remove('hidden');
    loadPortfolio();
    loadWatchlist();
    loadProfile();
    switchTab(tabName);
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

function showTyping() {
    // Move typing indicator into messages and show it
    elements.messages.appendChild(elements.typingIndicator);
    elements.typingIndicator.classList.remove('hidden');
    elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
}

function hideTyping() {
    elements.typingIndicator.classList.add('hidden');
}

function formatMessage(text) {
    // Convert markdown-like formatting to HTML
    let html = text
        // Escape HTML first
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        // Bold: **text** or __text__
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/__(.*?)__/g, '<strong>$1</strong>')
        // Italic: *text* or _text_
        .replace(/\*([^*]+)\*/g, '<em>$1</em>')
        .replace(/_([^_]+)_/g, '<em>$1</em>')
        // Bullet points: - item or • item
        .replace(/^[-•]\s+(.+)$/gm, '<li>$1</li>')
        // Numbered lists: 1. item
        .replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>')
        // Line breaks
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');

    // Wrap consecutive <li> in <ul>
    html = html.replace(/(<li>.*?<\/li>)+/gs, '<ul>$&</ul>');

    // Wrap in paragraph if not already structured
    if (!html.startsWith('<')) {
        html = '<p>' + html + '</p>';
    }

    return html;
}

// ============================================
// Stock Ticker
// ============================================

async function loadTicker() {
    const tickerContent = document.getElementById('ticker-content');
    if (!tickerContent) return;

    try {
        // Fetch portfolio and watchlist
        const [portfolioRes, watchlistRes] = await Promise.all([
            fetch(`${API_BASE}/api/portfolio`),
            fetch(`${API_BASE}/api/watchlist`)
        ]);

        const { portfolio } = await portfolioRes.json();
        const { watchlist } = await watchlistRes.json();

        // Default popular stocks - always show these
        const defaultTickers = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA',  // Big tech
            'META', 'NFLX', 'AMD', 'INTC', 'CRM', 'ORCL',      // More tech
            'JPM', 'V', 'MA', 'BAC',                            // Finance
            'JNJ', 'PFE', 'UNH',                                // Healthcare
            'XOM', 'CVX'                                        // Energy
        ];

        // Get all unique tickers (defaults + portfolio + watchlist)
        const tickers = [...new Set([
            ...defaultTickers,
            ...portfolio.map(s => s.ticker),
            ...watchlist.map(s => s.ticker)
        ])];

        await updateTickerWithStocks(tickers, tickerContent);

        // Refresh ticker every 60 seconds
        setInterval(() => loadTicker(), 60000);

    } catch (error) {
        console.error('Ticker error:', error);
        tickerContent.innerHTML = '<span class="ticker-placeholder">Market data unavailable</span>';
    }
}

async function updateTickerWithStocks(tickers, tickerContent) {
    try {
        // Fetch stock data for all tickers
        const stockDataPromises = tickers.map(ticker =>
            fetch(`${API_BASE}/api/stock/${ticker}`)
                .then(res => res.json())
                .catch(() => null)
        );

        const stockData = await Promise.all(stockDataPromises);

        // Build ticker items
        const tickerItems = stockData
            .filter(data => data && data.price)
            .map(data => {
                // API returns change_pct (from Finnhub)
                const changePercent = data.change_pct || data.change_percent || 0;
                const isUp = changePercent >= 0;
                const changeClass = isUp ? 'up' : 'down';
                const changeSign = isUp ? '+' : '';

                return `
                    <div class="ticker-item">
                        <span class="ticker-symbol">${data.ticker || data.symbol}</span>
                        <span class="ticker-price">$${data.price.toFixed(2)}</span>
                        <span class="ticker-change ${changeClass}">${changeSign}${changePercent.toFixed(2)}%</span>
                    </div>
                `;
            });

        if (tickerItems.length > 0) {
            // Duplicate items to create seamless loop
            const allItems = [...tickerItems, ...tickerItems].join('<span class="ticker-divider">•</span>');
            tickerContent.innerHTML = allItems;

            // Adjust animation speed based on content length
            const contentWidth = tickerContent.scrollWidth;
            const duration = Math.max(20, contentWidth / 50); // Slower for more content
            tickerContent.style.animationDuration = `${duration}s`;
        } else {
            tickerContent.innerHTML = '<span class="ticker-placeholder">No stock data available</span>';
        }

    } catch (error) {
        console.error('Error updating ticker:', error);
        tickerContent.innerHTML = '<span class="ticker-placeholder">Market data unavailable</span>';
    }
}

// Make functions globally available for onclick handlers
window.removeFromPortfolio = removeFromPortfolio;
window.removeFromWatchlist = removeFromWatchlist;
window.openSettingsToTab = openSettingsToTab;
window.showStockDetail = showStockDetail;

// ============================================
// Navigation
// ============================================

let currentPage = 'chat';

function initNavigation() {
    const navBtns = document.querySelectorAll('.nav-btn');
    const inputArea = document.querySelector('.input-area');

    navBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const page = btn.dataset.page;
            switchPage(page);
        });
    });

    // Stock modal close
    const closeStockModal = document.getElementById('close-stock-modal');
    const stockModal = document.getElementById('stock-modal');
    if (closeStockModal) {
        closeStockModal.addEventListener('click', () => stockModal.classList.add('hidden'));
    }
    if (stockModal) {
        stockModal.querySelector('.modal-overlay').addEventListener('click', () => stockModal.classList.add('hidden'));
    }
}

function switchPage(page) {
    currentPage = page;

    // Update nav buttons
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.page === page);
    });

    // Update page visibility
    document.querySelectorAll('.page-content').forEach(el => {
        el.classList.toggle('active', el.dataset.page === page);
    });

    // Show/hide input area (only on chat page)
    const inputArea = document.querySelector('.input-area');
    if (inputArea) {
        inputArea.style.display = page === 'chat' ? 'block' : 'none';
    }

    // Load page data
    if (page === 'market') {
        loadMarketData();
    } else if (page === 'calendar') {
        loadEarningsCalendar();
    }
}

// ============================================
// Market Page
// ============================================

async function loadMarketData() {
    // Load all market data in parallel
    Promise.all([
        loadIndices(),
        loadMovers(),
        loadSectors()
    ]).catch(console.error);
}

async function loadIndices() {
    const grid = document.getElementById('indices-grid');
    if (!grid) return;

    try {
        const response = await fetch(`${API_BASE}/api/market/indices`);
        const { indices } = await response.json();

        grid.innerHTML = indices.map(idx => {
            const isUp = idx.change_pct >= 0;
            return `
                <div class="index-card">
                    <span class="index-name">${idx.name}</span>
                    <span class="index-value">$${idx.price.toFixed(2)}</span>
                    <span class="index-change ${isUp ? 'up' : 'down'}">${isUp ? '+' : ''}${idx.change_pct.toFixed(2)}%</span>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading indices:', error);
        grid.innerHTML = '<div class="mover-placeholder">Unable to load indices</div>';
    }
}

async function loadMovers() {
    const gainersList = document.getElementById('gainers-list');
    const losersList = document.getElementById('losers-list');
    if (!gainersList || !losersList) return;

    try {
        const response = await fetch(`${API_BASE}/api/market/movers`);
        const { gainers, losers } = await response.json();

        gainersList.innerHTML = gainers.length > 0
            ? gainers.map(s => renderMoverItem(s, true)).join('')
            : '<div class="mover-placeholder">No gainers today</div>';

        losersList.innerHTML = losers.length > 0
            ? losers.map(s => renderMoverItem(s, false)).join('')
            : '<div class="mover-placeholder">No losers today</div>';

    } catch (error) {
        console.error('Error loading movers:', error);
        gainersList.innerHTML = '<div class="mover-placeholder">Unable to load data</div>';
        losersList.innerHTML = '<div class="mover-placeholder">Unable to load data</div>';
    }
}

function renderMoverItem(stock, isGainer) {
    const isUp = stock.change_pct >= 0;
    return `
        <div class="mover-item" onclick="showStockDetail('${stock.symbol}')">
            <div class="mover-info">
                <span class="mover-symbol">${stock.symbol}</span>
                <span class="mover-name">${stock.name}</span>
            </div>
            <div class="mover-price">
                <span class="mover-price-value">$${stock.price.toFixed(2)}</span>
                <span class="mover-change ${isUp ? 'up' : 'down'}">${isUp ? '+' : ''}${stock.change_pct.toFixed(2)}%</span>
            </div>
        </div>
    `;
}

async function loadSectors() {
    const grid = document.getElementById('sectors-grid');
    if (!grid) return;

    try {
        const response = await fetch(`${API_BASE}/api/market/sectors`);
        const { sectors } = await response.json();

        grid.innerHTML = sectors.map(sector => {
            const isUp = sector.change_pct >= 0;
            return `
                <div class="sector-item">
                    <span class="sector-name">${sector.name}</span>
                    <span class="sector-change ${isUp ? 'up' : 'down'}">${isUp ? '+' : ''}${sector.change_pct.toFixed(2)}%</span>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading sectors:', error);
        grid.innerHTML = '<div class="sector-placeholder">Unable to load sectors</div>';
    }
}

// ============================================
// Earnings Calendar
// ============================================

async function loadEarningsCalendar() {
    const earningsList = document.getElementById('earnings-list');
    const watchlistEarnings = document.getElementById('watchlist-earnings');
    if (!earningsList) return;

    try {
        const response = await fetch(`${API_BASE}/api/earnings`);
        const { earnings } = await response.json();

        if (earnings.length > 0) {
            earningsList.innerHTML = earnings.map(e => renderEarningsItem(e)).join('');
        } else {
            earningsList.innerHTML = '<div class="earnings-placeholder">No earnings scheduled this week</div>';
        }

        // Load watchlist earnings
        if (watchlistEarnings) {
            await loadWatchlistEarnings(earnings);
        }
    } catch (error) {
        console.error('Error loading earnings:', error);
        earningsList.innerHTML = '<div class="earnings-placeholder">Unable to load earnings calendar</div>';
    }
}

async function loadWatchlistEarnings(allEarnings) {
    const container = document.getElementById('watchlist-earnings');
    if (!container) return;

    try {
        // Get user's watchlist
        const response = await fetch(`${API_BASE}/api/watchlist`);
        const { watchlist } = await response.json();

        const watchlistSymbols = new Set(watchlist.map(s => s.ticker.toUpperCase()));

        // Filter earnings for watchlist stocks
        const watchlistEarnings = allEarnings.filter(e =>
            watchlistSymbols.has(e.symbol.toUpperCase())
        );

        if (watchlistEarnings.length > 0) {
            container.innerHTML = watchlistEarnings.map(e => renderEarningsItem(e)).join('');
        } else {
            container.innerHTML = '<div class="earnings-placeholder">None of your watched stocks have earnings this week</div>';
        }
    } catch (error) {
        console.error('Error loading watchlist earnings:', error);
    }
}

function renderEarningsItem(earning) {
    const date = new Date(earning.date);
    const dateStr = date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
    const hourStr = earning.hour === 'bmo' ? 'Before Open' :
                   earning.hour === 'amc' ? 'After Close' : 'TBD';

    return `
        <div class="earnings-item" onclick="showStockDetail('${earning.symbol}')">
            <div class="earnings-info">
                <span class="earnings-symbol">${earning.symbol}</span>
                <span class="earnings-name">Q${earning.quarter} ${earning.year}</span>
            </div>
            <div class="earnings-date">
                <span class="earnings-date-value">${dateStr}</span>
                <span class="earnings-time">${hourStr}</span>
            </div>
        </div>
    `;
}

// ============================================
// Stock Detail Modal
// ============================================

async function showStockDetail(symbol) {
    const modal = document.getElementById('stock-modal');
    const title = document.getElementById('stock-modal-title');
    const content = document.getElementById('stock-detail-content');

    if (!modal || !content) return;

    // Show modal with loading state
    title.textContent = symbol;
    content.innerHTML = '<div class="mover-placeholder">Loading...</div>';
    modal.classList.remove('hidden');

    try {
        const response = await fetch(`${API_BASE}/api/stock/${symbol}`);
        const data = await response.json();

        const isUp = (data.change_pct || 0) >= 0;
        const changeSign = isUp ? '+' : '';

        content.innerHTML = `
            <div class="stock-price-large">
                <div class="stock-price-value">$${(data.price || 0).toFixed(2)}</div>
                <div class="stock-price-change ${isUp ? 'up' : 'down'}">
                    ${changeSign}$${(data.change || 0).toFixed(2)} (${changeSign}${(data.change_pct || 0).toFixed(2)}%)
                </div>
            </div>

            <div class="stock-stats">
                ${data.volume ? `<div class="stat-item"><div class="stat-label">Volume</div><div class="stat-value">${formatNumber(data.volume)}</div></div>` : ''}
                ${data.market_cap ? `<div class="stat-item"><div class="stat-label">Market Cap</div><div class="stat-value">${formatMarketCap(data.market_cap)}</div></div>` : ''}
                ${data.pe_ratio ? `<div class="stat-item"><div class="stat-label">P/E Ratio</div><div class="stat-value">${data.pe_ratio.toFixed(2)}</div></div>` : ''}
                ${data.high_52w ? `<div class="stat-item"><div class="stat-label">52W High</div><div class="stat-value">$${data.high_52w.toFixed(2)}</div></div>` : ''}
                ${data.low_52w ? `<div class="stat-item"><div class="stat-label">52W Low</div><div class="stat-value">$${data.low_52w.toFixed(2)}</div></div>` : ''}
                ${data.avg_volume ? `<div class="stat-item"><div class="stat-label">Avg Volume</div><div class="stat-value">${formatNumber(data.avg_volume)}</div></div>` : ''}
            </div>

            ${data.news && data.news.length > 0 ? `
                <div class="stock-news">
                    <h3>Recent News</h3>
                    ${data.news.slice(0, 3).map(n => `
                        <div class="news-item">
                            <div class="news-headline">${n.headline}</div>
                            <div class="news-source">${n.source} • ${formatNewsDate(n.datetime)}</div>
                        </div>
                    `).join('')}
                </div>
            ` : ''}
        `;
    } catch (error) {
        console.error('Error loading stock detail:', error);
        content.innerHTML = '<div class="mover-placeholder">Unable to load stock data</div>';
    }
}

function formatNumber(num) {
    if (!num) return '—';
    if (num >= 1e9) return (num / 1e9).toFixed(2) + 'B';
    if (num >= 1e6) return (num / 1e6).toFixed(2) + 'M';
    if (num >= 1e3) return (num / 1e3).toFixed(2) + 'K';
    return num.toLocaleString();
}

function formatMarketCap(num) {
    if (!num) return '—';
    if (num >= 1e12) return '$' + (num / 1e12).toFixed(2) + 'T';
    if (num >= 1e9) return '$' + (num / 1e9).toFixed(2) + 'B';
    if (num >= 1e6) return '$' + (num / 1e6).toFixed(2) + 'M';
    return '$' + num.toLocaleString();
}

function formatNewsDate(dateStr) {
    if (!dateStr) return '';
    try {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } catch {
        return dateStr;
    }
}
