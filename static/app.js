;(function(){
  'use strict';

  // --- Configuration ---
  const CONFIG = {
    MAX_HISTORY_ITEMS: 25,
    PREVIEW_DEBOUNCE_MS: 300,
    MAX_RETRIES: 3,
    RETRY_DELAY_MS: 1000,
    MAX_FILE_SIZE_MB: 50,
    ANALYTICS: {
      MEASUREMENT_ID: 'G-X9B77HX3KT',
      API_SECRET: 'IjyeGKEFTJun8jHtcM_Jwg'
    }
  };

  // --- Analytics Integration ---
  class Analytics {
    constructor() {
      this.clientId = this.getOrCreateClientId();
      this.sessionId = Date.now().toString();
    }

    getOrCreateClientId() {
      let clientId = localStorage.getItem('docright_client_id');
      if (!clientId) {
        clientId = 'client_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
        localStorage.setItem('docright_client_id', clientId);
      }
      return clientId;
    }

    async trackEvent(eventName, parameters = {}) {
      try {
        // Client-side tracking
        if (typeof gtag !== 'undefined') {
          gtag('event', eventName, parameters);
        }

        // Server-side tracking via Measurement Protocol
        const payload = {
          client_id: this.clientId,
          events: [{
            name: eventName,
            params: {
              session_id: this.sessionId,
              engagement_time_msec: 1,
              ...parameters
            }
          }]
        };

        await fetch(`https://www.google-analytics.com/mp/collect?measurement_id=${CONFIG.ANALYTICS.MEASUREMENT_ID}&api_secret=${CONFIG.ANALYTICS.API_SECRET}`, {
          method: 'POST',
          body: JSON.stringify(payload),
          headers: { 'Content-Type': 'application/json' }
        });
      } catch (error) {
        console.warn('Analytics tracking failed:', error);
      }
    }
  }

  // --- Enhanced Application Class ---
  class DocRightApp {
    constructor() {
      this.analytics = new Analytics();
      this.history = [];
      this.objectUrls = new Set();
      this.previewTimer = null;
      this.retryAttempts = new Map();
      
      this.initializeElements();
      this.loadHistory();
      this.setupEventListeners();
      this.renderHistory();
      this.trackPageLoad();
    }

    initializeElements() {
      this.elements = {
        input: document.getElementById("input"),
        preview: document.getElementById("preview"),
        history: document.getElementById("history"),
        btnPreview: document.getElementById("btn-preview"),
        btnDocx: document.getElementById("btn-docx"),
        btnClear: document.getElementById("btn-clear"),
        spinner: document.getElementById("spinner"),
        progressBar: document.getElementById("progress-bar"),
        statusMessage: document.getElementById("status-message")
      };

      // Log missing elements for debugging
      Object.entries(this.elements).forEach(([key, element]) => {
        if (!element) {
          console.warn(`[DocRight] Element '${key}' not found in DOM`);
        }
      });

      // Verify critical elements
      const critical = ['input', 'preview', 'btnPreview', 'btnDocx'];
      const missing = critical.filter(key => !this.elements[key]);
      if (missing.length > 0) {
        console.error(`[DocRight] Critical elements missing: ${missing.join(', ')}`);
        this.showError('خطای اولیه: عناصر ضروری صفحه یافت نشدند.');
        return;
      }
    }

    setupEventListeners() {
      // Input handlers
      if (this.elements.input) {
        this.elements.input.addEventListener('input', this.handleInputChange.bind(this));
        this.elements.input.addEventListener('paste', this.handlePaste.bind(this));
        this.elements.input.addEventListener('dragover', this.handleDragOver.bind(this));
        this.elements.input.addEventListener('drop', this.handleDrop.bind(this));
      }

      // Button handlers
      if (this.elements.btnPreview) {
        this.elements.btnPreview.addEventListener('click', this.handlePreviewClick.bind(this));
      }

      if (this.elements.btnDocx) {
        this.elements.btnDocx.addEventListener('click', this.handleDocxClick.bind(this));
      }

      if (this.elements.btnClear) {
        this.elements.btnClear.addEventListener('click', this.handleClearHistory.bind(this));
      }

      // Cleanup on page unload
      window.addEventListener('beforeunload', this.cleanup.bind(this));
      
      // Keyboard shortcuts
      document.addEventListener('keydown', this.handleKeyboardShortcuts.bind(this));
    }

    handleInputChange() {
      clearTimeout(this.previewTimer);
      
      if (!this.elements.input.value.trim()) {
        this.resetPreview();
        return;
      }

      // Auto-preview with debouncing
      this.previewTimer = setTimeout(() => {
        this.generatePreview(false); // Silent preview
      }, CONFIG.PREVIEW_DEBOUNCE_MS);

      // Track input activity
      this.analytics.trackEvent('text_input_activity', {
        character_count: this.elements.input.value.length,
        word_count: this.elements.input.value.trim().split(/\s+/).length
      });
    }

    handlePaste(event) {
      const pastedText = (event.clipboardData || window.clipboardData).getData('text');
      
      this.analytics.trackEvent('text_pasted', {
        character_count: pastedText.length,
        paste_source: 'clipboard'
      });

      // Check for large pastes
      if (pastedText.length > CONFIG.MAX_FILE_SIZE_MB * 1024 * 1024) {
        event.preventDefault();
        this.showError('متن پیست‌شده بیش از حد طولانی است. لطفاً متن کوتاه‌تری وارد کنید.');
        return;
      }
    }

    handleDragOver(event) {
      event.preventDefault();
      event.dataTransfer.dropEffect = 'copy';
    }

    handleDrop(event) {
      event.preventDefault();
      const files = Array.from(event.dataTransfer.files);
      
      if (files.length > 0) {
        this.handleFileUpload(files[0]);
      }
    }

    async handleFileUpload(file) {
      if (!file.type.includes('text') && !file.name.endsWith('.md')) {
        this.showError('لطفاً فقط فایل‌های متنی یا Markdown آپلود کنید.');
        return;
      }

      if (file.size > CONFIG.MAX_FILE_SIZE_MB * 1024 * 1024) {
        this.showError(`حجم فایل نباید بیش از ${CONFIG.MAX_FILE_SIZE_MB} مگابایت باشد.`);
        return;
      }

      try {
        const text = await file.text();
        this.elements.input.value = text;
        this.generatePreview();
        
        this.analytics.trackEvent('file_uploaded', {
          file_size: file.size,
          file_type: file.type,
          file_name_length: file.name.length
        });
      } catch (error) {
        console.error('File upload error:', error);
        this.showError('خطا در خواندن فایل. لطفاً دوباره تلاش کنید.');
      }
    }

    handleKeyboardShortcuts(event) {
      // Ctrl/Cmd + Enter for preview
      if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
        event.preventDefault();
        this.handlePreviewClick();
      }
      
      // Ctrl/Cmd + Shift + D for DOCX
      if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === 'D') {
        event.preventDefault();
        this.handleDocxClick();
      }
    }

    handlePreviewClick() {
      this.generatePreview(true);
      this.analytics.trackEvent('preview_button_clicked', {
        manual_trigger: true
      });
    }

    async handleDocxClick() {
      const startTime = performance.now();
      
      try {
        await this.generateDocx();
        
        const duration = performance.now() - startTime;
        this.analytics.trackEvent('docx_generation_completed', {
          generation_time_ms: Math.round(duration),
          success: true
        });
      } catch (error) {
        const duration = performance.now() - startTime;
        this.analytics.trackEvent('docx_generation_failed', {
          generation_time_ms: Math.round(duration),
          error_message: error.message,
          success: false
        });
      }
    }

    handleClearHistory() {
      if (!confirm('آیا مطمئن هستید که می‌خواهید تمام تاریخچه را پاک کنید؟')) {
        return;
      }

      const itemCount = this.history.length;
      
      // Revoke all object URLs
      this.objectUrls.forEach(url => {
        URL.revokeObjectURL(url);
      });
      this.objectUrls.clear();

      this.history = [];
      this.saveHistory();
      this.renderHistory();

      this.analytics.trackEvent('history_cleared', {
        items_cleared: itemCount
      });

      this.showSuccess('تاریخچه با موفقیت پاک شد.');
    }

    generatePreview(saveToHistory = false) {
      if (!this.elements.input?.value.trim()) {
        this.showError('لطفاً ابتدا متنی وارد کنید.');
        return;
      }

      try {
        if (typeof marked === 'undefined') {
          throw new Error('کتابخانه Marked.js بارگذاری نشده است.');
        }

        const html = marked.parse(this.elements.input.value);
        this.elements.preview.innerHTML = html;

        if (saveToHistory) {
          this.addToHistory(this.elements.input.value);
        }

        this.analytics.trackEvent('preview_generated', {
          content_length: this.elements.input.value.length,
          has_markdown_headers: /^#{1,6}\s/.test(this.elements.input.value),
          has_markdown_lists: /^[\*\-\+]\s/m.test(this.elements.input.value),
          has_markdown_tables: /\|.*\|/.test(this.elements.input.value)
        });

      } catch (error) {
        console.error('Preview generation error:', error);
        this.elements.preview.innerHTML = `<div class="text-red-500">خطا در تولید پیش‌نمایش: ${error.message}</div>`;
        
        this.analytics.trackEvent('preview_generation_error', {
          error_message: error.message
        });
      }
    }

    async generateDocx() {
      if (!this.elements.input?.value.trim()) {
        this.showError('لطفاً ابتدا متنی وارد کنید.');
        return;
      }

      const conversionId = Date.now().toString();
      
      try {
        this.setLoadingState(true, 'در حال تبدیل...');
        this.updateProgress(10);

        const docxUrl = await this.convertWithRetry('docx', conversionId);
        
        if (!docxUrl) {
          throw new Error('تبدیل ناموفق بود.');
        }

        this.updateProgress(80);

        // Auto-download
        const fileName = this.generateFileName('docx');
        this.downloadFile(docxUrl, fileName);

        this.updateProgress(90);

        // Add to history
        this.addToHistory(this.elements.input.value, docxUrl, fileName);

        this.updateProgress(100);
        this.showSuccess('فایل Word با موفقیت ایجاد و دانلود شد.');

      } catch (error) {
        console.error('DOCX generation error:', error);
        this.showError(`خطا در تولید فایل Word: ${error.message}`);
        throw error;
      } finally {
        this.setLoadingState(false);
        this.updateProgress(0);
      }
    }

    async convertWithRetry(format, conversionId, attempt = 1) {
      try {
        return await this.callConvertAPI(format);
      } catch (error) {
        if (attempt < CONFIG.MAX_RETRIES) {
          console.warn(`Conversion attempt ${attempt} failed, retrying...`, error);
          
          await this.delay(CONFIG.RETRY_DELAY_MS * attempt);
          return this.convertWithRetry(format, conversionId, attempt + 1);
        }
        throw error;
      }
    }

    async callConvertAPI(format) {
      const formData = new FormData();
      formData.append('text', this.elements.input.value);
      formData.append('format', format);

      this.updateProgress(30);

      const response = await fetch('/api/convert', {
        method: 'POST',
        body: formData
      });

      this.updateProgress(60);

      if (!response.ok) {
        let errorMessage = `خطا در تبدیل: ${response.status}`;
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch (e) {
          const errorText = await response.text();
          errorMessage = errorText || errorMessage;
        }
        throw new Error(errorMessage);
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      this.objectUrls.add(url);

      return url;
    }

    downloadFile(url, fileName) {
      const tempLink = document.createElement('a');
      tempLink.href = url;
      tempLink.download = fileName;
      tempLink.style.display = 'none';
      
      document.body.appendChild(tempLink);
      tempLink.click();
      document.body.removeChild(tempLink);
    }

    generateFileName(extension) {
      const timestamp = new Date().toISOString()
        .replace(/:/g, '-')
        .replace('T', '_')
        .slice(0, 19);
      
      const textPreview = this.elements.input.value
        .trim()
        .slice(0, 30)
        .replace(/[^\w\u0600-\u06FF\s]/g, '')
        .replace(/\s+/g, '_');
      
      return `DocRight_${textPreview || 'document'}_${timestamp}.${extension}`;
    }

    addToHistory(content, fileUrl = null, fileName = null) {
      const entry = {
        id: Date.now(),
        timestamp: new Date().toISOString(),
        displayTime: new Date().toLocaleString('fa-IR'),
        content: content,
        snippet: this.generateSnippet(content),
        fileUrl: fileUrl,
        fileName: fileName,
        contentStats: {
          characterCount: content.length,
          wordCount: content.trim().split(/\s+/).length,
          hasMarkdown: this.detectMarkdownFeatures(content)
        }
      };

      this.history.unshift(entry);

      // Maintain history size limit
      while (this.history.length > CONFIG.MAX_HISTORY_ITEMS) {
        const removed = this.history.pop();
        if (removed.fileUrl) {
          URL.revokeObjectURL(removed.fileUrl);
          this.objectUrls.delete(removed.fileUrl);
        }
      }

      this.saveHistory();
      this.renderHistory();

      this.analytics.trackEvent('content_added_to_history', {
        character_count: entry.contentStats.characterCount,
        word_count: entry.contentStats.wordCount,
        has_markdown: entry.contentStats.hasMarkdown
      });
    }

    generateSnippet(content) {
      return content
        .trim()
        .replace(/\s+/g, ' ')
        .slice(0, 80);
    }

    detectMarkdownFeatures(content) {
      const features = {
        headers: /^#{1,6}\s/.test(content),
        lists: /^[\*\-\+]\s/m.test(content),
        tables: /\|.*\|/.test(content),
        bold: /\*\*.*\*\*/.test(content),
        italic: /\*.*\*/.test(content),
        code: /`.*`/.test(content)
      };
      
      return Object.values(features).some(Boolean);
    }

    renderHistory() {
      if (!this.elements.history) return;

      this.elements.history.innerHTML = '';

      if (this.history.length === 0) {
        this.renderEmptyHistory();
        return;
      }

      this.history.forEach(entry => {
        const historyItem = this.createHistoryItem(entry);
        this.elements.history.appendChild(historyItem);
      });

      if (this.elements.btnClear) {
        this.elements.btnClear.style.display = 'block';
      }
    }

    renderEmptyHistory() {
      const emptyDiv = document.createElement('div');
      emptyDiv.className = 'text-gray-500 text-center py-8';
      emptyDiv.innerHTML = `
        <svg class="w-12 h-12 mx-auto mb-3 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
        </svg>
        <p>تاریخچه خالی است</p>
        <p class="text-sm mt-1">موارد تبدیل‌شده اینجا نمایش داده می‌شوند</p>
      `;
      this.elements.history.appendChild(emptyDiv);

      if (this.elements.btnClear) {
        this.elements.btnClear.style.display = 'none';
      }
    }

    createHistoryItem(entry) {
      const li = document.createElement('li');
      li.className = 'history-item p-3 border border-gray-200 rounded-lg hover:shadow-sm cursor-pointer transition-all';
      
      li.innerHTML = `
        <div class="flex justify-between items-start">
          <div class="flex-1 min-w-0">
            <div class="font-medium text-sm text-gray-800 mb-1">${entry.displayTime}</div>
            <div class="text-sm text-gray-600 truncate">${entry.snippet}${entry.snippet.length > 79 ? '...' : ''}</div>
            <div class="text-xs text-gray-400 mt-1">
              ${entry.contentStats.characterCount.toLocaleString('fa-IR')} کاراکتر • 
              ${entry.contentStats.wordCount.toLocaleString('fa-IR')} کلمه
              ${entry.contentStats.hasMarkdown ? ' • Markdown' : ''}
            </div>
          </div>
          <div class="flex flex-col gap-2 mr-3">
            ${entry.fileUrl ? `<a href="${entry.fileUrl}" download="${entry.fileName || 'document.docx'}" class="history-btn px-2 py-1 bg-purple-600 text-white rounded text-xs hover:bg-purple-700 transition">DOCX</a>` : ''}
          </div>
        </div>
      `;

      // Click handler to restore content
      li.addEventListener('click', (e) => {
        if (e.target.classList.contains('history-btn')) return; // Don't trigger on download button
        
        this.elements.input.value = entry.content;
        this.generatePreview();
        
        this.analytics.trackEvent('history_item_restored', {
          entry_age_minutes: Math.round((Date.now() - new Date(entry.timestamp).getTime()) / 60000),
          character_count: entry.contentStats.characterCount
        });
      });

      return li;
    }

    loadHistory() {
      try {
        const saved = localStorage.getItem('docright_history');
        this.history = saved ? JSON.parse(saved) : [];
        
        // Clean up invalid entries
        this.history = this.history.filter(entry => 
          entry && entry.content && entry.timestamp
        );
      } catch (error) {
        console.error('Error loading history:', error);
        this.history = [];
      }
    }

    saveHistory() {
      try {
        // Save only essential data to localStorage
        const historyToSave = this.history.map(entry => ({
          id: entry.id,
          timestamp: entry.timestamp,
          displayTime: entry.displayTime,
          content: entry.content,
          snippet: entry.snippet,
          contentStats: entry.contentStats
          // Don't save fileUrl as blob URLs don't persist
        }));
        
        localStorage.setItem('docright_history', JSON.stringify(historyToSave));
      } catch (error) {
        console.error('Error saving history:', error);
      }
    }

    resetPreview() {
      if (this.elements.preview) {
        this.elements.preview.innerHTML = `
          <div class="text-center text-gray-400 italic py-12">
            <svg class="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
            </svg>
            <p>پیش‌نمایش در اینجا نمایش داده می‌شود</p>
          </div>
        `;
      }
    }

    setLoadingState(isLoading, message = 'در حال پردازش...') {
      const buttons = [this.elements.btnPreview, this.elements.btnDocx].filter(Boolean);
      
      if (isLoading) {
        buttons.forEach(btn => {
          btn.disabled = true;
          btn.classList.add('opacity-50', 'cursor-not-allowed');
        });
        
        if (this.elements.spinner) {
          this.elements.spinner.style.display = 'flex';
        }
        
        this.showStatus(message);
      } else {
        buttons.forEach(btn => {
          btn.disabled = false;
          btn.classList.remove('opacity-50', 'cursor-not-allowed');
        });
        
        if (this.elements.spinner) {
          this.elements.spinner.style.display = 'none';
        }
        
        this.clearStatus();
      }
    }

    updateProgress(percentage) {
      if (this.elements.progressBar) {
        this.elements.progressBar.style.width = `${percentage}%`;
        this.elements.progressBar.style.display = percentage > 0 ? 'block' : 'none';
      }
    }

    showStatus(message) {
      if (this.elements.statusMessage) {
        this.elements.statusMessage.textContent = message;
        this.elements.statusMessage.className = 'text-blue-600 text-sm';
      }
    }

    showSuccess(message) {
      if (this.elements.statusMessage) {
        this.elements.statusMessage.textContent = message;
        this.elements.statusMessage.className = 'text-green-600 text-sm';
        setTimeout(() => this.clearStatus(), 3000);
      }
    }

    showError(message) {
      if (this.elements.statusMessage) {
        this.elements.statusMessage.textContent = message;
        this.elements.statusMessage.className = 'text-red-600 text-sm';
        setTimeout(() => this.clearStatus(), 5000);
      }
      console.error('DocRight Error:', message);
    }

    clearStatus() {
      if (this.elements.statusMessage) {
        this.elements.statusMessage.textContent = '';
      }
    }

    trackPageLoad() {
      this.analytics.trackEvent('page_view', {
        page_title: 'DocRight - تبدیل متن به Word',
        page_location: window.location.href,
        user_agent: navigator.userAgent,
        language: navigator.language
      });
    }

    delay(ms) {
      return new Promise(resolve => setTimeout(resolve, ms));
    }

    cleanup() {
      console.log(`[DocRight] Cleaning up ${this.objectUrls.size} object URLs`);
      
      this.objectUrls.forEach(url => {
        URL.revokeObjectURL(url);
      });
      this.objectUrls.clear();
      
      if (this.previewTimer) {
        clearTimeout(this.previewTimer);
      }
    }
  }

  // --- Initialize Application ---
  document.addEventListener('DOMContentLoaded', () => {
    try {
      window.docRightApp = new DocRightApp();
      console.log('[DocRight] Application initialized successfully');
    } catch (error) {
      console.error('[DocRight] Failed to initialize application:', error);
    }
  });

})();