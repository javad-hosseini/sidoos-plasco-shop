/**
 * CKEditor 5 Internal Link Helper - Sidoos Admin
 *
 * Adds a dedicated "Internal Link" button to CKEditor 5 toolbars across the Django admin
 * (for Products, Articles, etc.), providing real-time search for existing products,
 * articles, and categories by name and inserting relative internal links.
 */

(function () {
    'use strict';

    let currentActiveEditor = null;
    let selectedItem = null;
    let searchDebounceTimer = null;
    let currentFilterType = 'all';

    // SVG icon for Internal Link (link + search magnifier badge)
    const INTERNAL_LINK_ICON_SVG = `
        <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
            <path d="M3.9 12c0-1.71 1.39-3.1 3.1-3.1h4V7H7c-2.76 0-5 2.24-5 5s2.24 5 5 5h4v-1.9H7c-1.71 0-3.1-1.39-3.1-3.1zM8 13h8v-2H8v2zm9-6h-4v1.9h4c1.71 0 3.1 1.39 3.1 3.1 0 1.71-1.39 3.1-3.1 3.1h-4V17h4c2.76 0 5-2.24 5-5s-2.24-5-5-5z"/>
            <circle cx="17.5" cy="17.5" r="3.5" fill="#0d6efd" stroke="#ffffff" stroke-width="1.5"/>
        </svg>
    `;

    // =========================================================================
    // 1. Build and Inject Modal DOM
    // =========================================================================
    function getOrCreateModal() {
        let modalOverlay = document.getElementById('sidoos-internal-link-modal-overlay');
        if (modalOverlay) return modalOverlay;

        modalOverlay = document.createElement('div');
        modalOverlay.id = 'sidoos-internal-link-modal-overlay';
        modalOverlay.className = 'sidoos-link-modal-overlay';
        modalOverlay.innerHTML = `
            <div class="sidoos-link-modal" role="dialog" aria-modal="true" aria-labelledby="sidoos-link-title">
                <div class="sidoos-link-header">
                    <h3 id="sidoos-link-title" class="sidoos-link-header-title">
                        ${INTERNAL_LINK_ICON_SVG}
                        <span>درج لینک داخلی (محصولات و مقالات)</span>
                    </h3>
                    <button type="button" class="sidoos-link-close-btn" id="sidoos-link-close-btn" aria-label="بستن">&times;</button>
                </div>

                <div class="sidoos-link-body">
                    <!-- Link Display Text -->
                    <div class="sidoos-link-form-group">
                        <label for="sidoos-link-text-input" class="sidoos-link-label">متن نمایشی پیوند:</label>
                        <input type="text" id="sidoos-link-text-input" class="sidoos-link-input" placeholder="متنی که کاربر روی آن کلیک می‌کند..." autocomplete="off">
                    </div>

                    <!-- Type Filter Tabs -->
                    <div class="sidoos-link-tabs">
                        <button type="button" class="sidoos-link-tab-btn is-active" data-type="all">همه موارد</button>
                        <button type="button" class="sidoos-link-tab-btn" data-type="product">محصولات</button>
                        <button type="button" class="sidoos-link-tab-btn" data-type="article">مقالات</button>
                        <button type="button" class="sidoos-link-tab-btn" data-type="category">دسته‌بندی‌ها</button>
                    </div>

                    <!-- Search Input -->
                    <div class="sidoos-link-form-group">
                        <label for="sidoos-link-search-input" class="sidoos-link-label">جستجو بر اساس نام یا شناسه:</label>
                        <div class="sidoos-link-input-wrapper">
                            <input type="text" id="sidoos-link-search-input" class="sidoos-link-input sidoos-link-search-input" placeholder="نام محصول، مقاله یا دسته‌بندی را بنویسید..." autocomplete="off">
                            <svg class="sidoos-link-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="11" cy="11" r="8"></circle>
                                <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                            </svg>
                        </div>
                    </div>

                    <!-- Results List -->
                    <div class="sidoos-link-results-container" id="sidoos-link-results-container">
                        <div class="sidoos-link-status-msg" id="sidoos-link-status-msg">
                            <div class="sidoos-link-spinner"></div>
                            <div>در حال دریافت موارد پیشنهادی...</div>
                        </div>
                    </div>

                    <!-- Selected Target URL -->
                    <div class="sidoos-link-form-group">
                        <label for="sidoos-link-url-input" class="sidoos-link-label">آدرس پیوند (URL داخلی):</label>
                        <input type="text" id="sidoos-link-url-input" class="sidoos-link-input ltr-text" placeholder="/products/... یا /blogs/..." autocomplete="off">
                    </div>
                </div>

                <div class="sidoos-link-footer">
                    <span class="sidoos-link-hint">💡 با دو بار کلیک روی هر نتیجه، پیوند فوراً درج می‌شود.</span>
                    <div class="sidoos-link-actions">
                        <button type="button" class="sidoos-link-btn sidoos-link-btn-cancel" id="sidoos-link-cancel-btn">انصراف</button>
                        <button type="button" class="sidoos-link-btn sidoos-link-btn-primary" id="sidoos-link-submit-btn" disabled>درج لینک در متن</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modalOverlay);

        // Attach modal event listeners
        document.getElementById('sidoos-link-close-btn').addEventListener('click', closeModal);
        document.getElementById('sidoos-link-cancel-btn').addEventListener('click', closeModal);
        modalOverlay.addEventListener('click', function (e) {
            if (e.target === modalOverlay) closeModal();
        });

        // Filter tabs
        const tabBtns = modalOverlay.querySelectorAll('.sidoos-link-tab-btn');
        tabBtns.forEach(btn => {
            btn.addEventListener('click', function () {
                tabBtns.forEach(b => b.classList.remove('is-active'));
                this.classList.add('is-active');
                currentFilterType = this.getAttribute('data-type') || 'all';
                performSearch();
            });
        });

        // Search input key events & debouncing
        const searchInput = document.getElementById('sidoos-link-search-input');
        searchInput.addEventListener('input', function () {
            clearTimeout(searchDebounceTimer);
            searchDebounceTimer = setTimeout(performSearch, 220);
        });

        searchInput.addEventListener('keydown', function (e) {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                navigateResults(1);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                navigateResults(-1);
            } else if (e.key === 'Enter') {
                e.preventDefault();
                submitLink();
            }
        });

        // URL input manual edit enables submit
        const urlInput = document.getElementById('sidoos-link-url-input');
        urlInput.addEventListener('input', function () {
            const submitBtn = document.getElementById('sidoos-link-submit-btn');
            submitBtn.disabled = !this.value.trim();
        });

        // Submit button
        document.getElementById('sidoos-link-submit-btn').addEventListener('click', submitLink);

        // Escape key to close
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && modalOverlay.classList.contains('is-active')) {
                closeModal();
            }
        });

        return modalOverlay;
    }

    // =========================================================================
    // 2. Open / Close Modal Logic
    // =========================================================================
    function openModalForEditor(editor) {
        currentActiveEditor = editor;
        selectedItem = null;
        const modal = getOrCreateModal();

        // 1. Detect selected text inside editor
        let selectedText = '';
        try {
            const selection = editor.model.document.selection;
            if (!selection.isCollapsed) {
                for (const range of selection.getRanges()) {
                    for (const item of range.getItems()) {
                        if (item.data) {
                            selectedText += item.data;
                        }
                    }
                }
            }
        } catch (err) {
            console.warn('Could not extract CKEditor selection:', err);
        }

        const textInput = document.getElementById('sidoos-link-text-input');
        const urlInput = document.getElementById('sidoos-link-url-input');
        const searchInput = document.getElementById('sidoos-link-search-input');
        const submitBtn = document.getElementById('sidoos-link-submit-btn');

        textInput.value = selectedText.trim();
        urlInput.value = '';
        searchInput.value = '';
        submitBtn.disabled = true;

        modal.classList.add('is-active');

        // Focus search input
        setTimeout(() => {
            searchInput.focus();
        }, 100);

        // Fetch initial recent items
        performSearch();
    }

    function closeModal() {
        const modal = document.getElementById('sidoos-internal-link-modal-overlay');
        if (modal) {
            modal.classList.remove('is-active');
        }
        if (currentActiveEditor) {
            try {
                currentActiveEditor.editing.view.focus();
            } catch (e) {}
        }
    }

    // =========================================================================
    // 3. Search Fetching & Rendering
    // =========================================================================
    function performSearch() {
        const searchInput = document.getElementById('sidoos-link-search-input');
        const container = document.getElementById('sidoos-link-results-container');
        const query = searchInput ? searchInput.value.trim() : '';

        container.innerHTML = `
            <div class="sidoos-link-status-msg">
                <div class="sidoos-link-spinner"></div>
                <div>در حال جستجو...</div>
            </div>
        `;

        const searchUrl = `/sidoos-administration/internal-link-search/?q=${encodeURIComponent(query)}&type=${encodeURIComponent(currentFilterType)}&limit=15`;

        fetch(searchUrl, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json',
            }
        })
        .then(res => {
            if (!res.ok) throw new Error('Search failed with status ' + res.status);
            return res.json();
        })
        .then(data => {
            renderSearchResults(data.results || []);
        })
        .catch(err => {
            console.error('Internal link search error:', err);
            container.innerHTML = `
                <div class="sidoos-link-status-msg" style="color: #dc2626;">
                    خطا در برقراری ارتباط با سرور. لطفاً مجدداً تلاش کنید.
                </div>
            `;
        });
    }

    function renderSearchResults(results) {
        const container = document.getElementById('sidoos-link-results-container');
        if (!container) return;

        if (results.length === 0) {
            container.innerHTML = `
                <div class="sidoos-link-status-msg">
                    هیچ موردی با این مشخصات یافت نشد.
                </div>
            `;
            return;
        }

        container.innerHTML = '';
        const listWrapper = document.createElement('div');

        results.forEach((item, index) => {
            const itemRow = document.createElement('div');
            itemRow.className = 'sidoos-link-result-item' + (index === 0 ? ' is-selected' : '');
            itemRow.setAttribute('data-index', index);

            // Thumbnail or icon placeholder
            let thumbHtml = '';
            if (item.thumbnail) {
                thumbHtml = `<img src="${item.thumbnail}" alt="" class="sidoos-link-thumb" loading="lazy">`;
            } else {
                let iconChar = '🛍️';
                if (item.type === 'article') iconChar = '📝';
                else if (item.type === 'category') iconChar = '📁';
                thumbHtml = `<div class="sidoos-link-thumb-placeholder">${iconChar}</div>`;
            }

            const badgeClass = `sidoos-link-badge sidoos-link-badge-${item.type}`;

            itemRow.innerHTML = `
                ${thumbHtml}
                <div class="sidoos-link-result-info">
                    <div class="sidoos-link-result-top">
                        <span class="${badgeClass}">${item.type_label}</span>
                        <span class="sidoos-link-result-title">${escapeHtml(item.title)}</span>
                    </div>
                    <div class="sidoos-link-result-meta">${escapeHtml(item.meta || '')}</div>
                    <div class="sidoos-link-result-url">${escapeHtml(item.url)}</div>
                </div>
            `;

            // Click to select
            itemRow.addEventListener('click', function () {
                selectItem(item, itemRow);
            });

            // Double click to insert directly
            itemRow.addEventListener('dblclick', function () {
                selectItem(item, itemRow);
                submitLink();
            });

            listWrapper.appendChild(itemRow);
        });

        container.appendChild(listWrapper);

        // Auto-select first item if available
        if (results.length > 0) {
            const firstRow = container.querySelector('.sidoos-link-result-item');
            selectItem(results[0], firstRow, false);
        }
    }

    function selectItem(item, rowElement, updateTextIfEmpty = true) {
        selectedItem = item;
        const container = document.getElementById('sidoos-link-results-container');
        if (container) {
            container.querySelectorAll('.sidoos-link-result-item').forEach(el => el.classList.remove('is-selected'));
            if (rowElement) {
                rowElement.classList.add('is-selected');
                rowElement.scrollIntoView({ block: 'nearest' });
            }
        }

        const urlInput = document.getElementById('sidoos-link-url-input');
        const textInput = document.getElementById('sidoos-link-text-input');
        const submitBtn = document.getElementById('sidoos-link-submit-btn');

        if (urlInput) urlInput.value = item.url;
        if (textInput && (!textInput.value.trim() || updateTextIfEmpty && !textInput.getAttribute('data-manual'))) {
            textInput.value = item.title;
        }
        if (submitBtn) submitBtn.disabled = false;
    }

    function navigateResults(direction) {
        const container = document.getElementById('sidoos-link-results-container');
        if (!container) return;

        const items = container.querySelectorAll('.sidoos-link-result-item');
        if (!items.length) return;

        let currentIndex = -1;
        items.forEach((el, idx) => {
            if (el.classList.contains('is-selected')) currentIndex = idx;
        });

        let newIndex = currentIndex + direction;
        if (newIndex < 0) newIndex = 0;
        if (newIndex >= items.length) newIndex = items.length - 1;

        items[newIndex].click();
    }

    // =========================================================================
    // 4. Insert Link into CKEditor Model
    // =========================================================================
    function submitLink() {
        if (!currentActiveEditor) return;

        const urlInput = document.getElementById('sidoos-link-url-input');
        const textInput = document.getElementById('sidoos-link-text-input');

        const targetUrl = urlInput ? urlInput.value.trim() : '';
        const linkText = textInput && textInput.value.trim() ? textInput.value.trim() : targetUrl;

        if (!targetUrl) return;

        try {
            currentActiveEditor.model.change(writer => {
                const selection = currentActiveEditor.model.document.selection;
                const linkedText = writer.createText(linkText, { linkHref: targetUrl });
                currentActiveEditor.model.insertContent(linkedText, selection);
            });
        } catch (err) {
            console.error('Error inserting link into CKEditor model:', err);
        }

        closeModal();
    }

    function escapeHtml(str) {
        if (!str) return '';
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    // =========================================================================
    // 5. Attach Button to CKEditor 5 Toolbars
    // =========================================================================
    function attachHelperToEditor(editor, textareaId) {
        if (!editor || !editor.ui || !editor.ui.view || !editor.ui.view.toolbar) {
            return;
        }

        const toolbarElement = editor.ui.view.toolbar.element;
        if (!toolbarElement) return;

        const itemsContainer = toolbarElement.querySelector('.ck-toolbar__items');
        if (!itemsContainer) return;

        // Check if button already attached
        if (itemsContainer.querySelector(`.ck-internal-link-btn[data-editor-id="${textareaId}"]`)) {
            return;
        }

        // Create CKEditor 5 styled toolbar button
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'ck ck-button ck-off ck-button_with-icon ck-internal-link-btn';
        btn.setAttribute('tabindex', '-1');
        btn.setAttribute('data-editor-id', textareaId);
        btn.setAttribute('data-tooltip', 'افزودن لینک داخلی (محصولات و مقالات)');
        btn.setAttribute('title', 'افزودن لینک داخلی (محصولات و مقالات) - Ctrl+Shift+K');
        btn.innerHTML = INTERNAL_LINK_ICON_SVG;

        btn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            openModalForEditor(editor);
        });

        // Try to place it directly next to the native link button
        const nativeLinkBtn = itemsContainer.querySelector('[data-cke-tooltip-text*="پیوند"], [data-cke-tooltip-text*="link"], [data-cke-tooltip-text*="Link"], .ck-button[title*="پیوند"], .ck-button[title*="Link"]');
        if (nativeLinkBtn && nativeLinkBtn.nextSibling) {
            itemsContainer.insertBefore(btn, nativeLinkBtn.nextSibling);
        } else if (nativeLinkBtn) {
            itemsContainer.appendChild(btn);
        } else {
            // Otherwise append after first group or at start
            const firstSeparator = itemsContainer.querySelector('.ck-toolbar__separator');
            if (firstSeparator) {
                itemsContainer.insertBefore(btn, firstSeparator);
            } else {
                itemsContainer.appendChild(btn);
            }
        }

        // Attach keyboard shortcut Ctrl+Shift+K inside editable content area
        const editableElement = editor.ui.view.editable ? editor.ui.view.editable.element : null;
        if (editableElement && !editableElement.hasAttribute('data-link-shortcut-bound')) {
            editableElement.setAttribute('data-link-shortcut-bound', 'true');
            editableElement.addEventListener('keydown', function (e) {
                if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'K' || e.key === 'k')) {
                    e.preventDefault();
                    e.stopPropagation();
                    openModalForEditor(editor);
                }
            });
        }
    }

    // =========================================================================
    // 6. Initialization & Watchers
    // =========================================================================
    function init() {
        // 1. Check existing window.editors
        function checkEditors() {
            if (window.editors && typeof window.editors === 'object') {
                for (const [textareaId, editorInstance] of Object.entries(window.editors)) {
                    if (editorInstance && editorInstance.ui) {
                        attachHelperToEditor(editorInstance, textareaId);
                    }
                }
            }
        }

        // Run checks periodically during initial page load
        checkEditors();
        const intervals = [300, 700, 1500, 3000];
        intervals.forEach(delay => setTimeout(checkEditors, delay));

        // 2. Observe DOM mutations for newly created CKEditor instances
        const observer = new MutationObserver(function (mutations) {
            let shouldCheck = false;
            for (const m of mutations) {
                if (m.addedNodes.length) {
                    for (const node of m.addedNodes) {
                        if (node.nodeType === 1 && (
                            node.classList.contains('ck-editor') ||
                            node.querySelector && node.querySelector('.ck-editor')
                        )) {
                            shouldCheck = true;
                            break;
                        }
                    }
                }
                if (shouldCheck) break;
            }
            if (shouldCheck) {
                setTimeout(checkEditors, 100);
            }
        });

        observer.observe(document.body, { childList: true, subtree: true });

        // 3. Hook into window.ckeditorRegisterCallback if present
        if (typeof window.ckeditorRegisterCallback === 'function') {
            const originalRegister = window.ckeditorRegisterCallback;
            window.ckeditorRegisterCallback = function (textareaId, callback) {
                originalRegister(textareaId, function (editor) {
                    if (typeof callback === 'function') {
                        callback(editor);
                    }
                    setTimeout(() => attachHelperToEditor(editor, textareaId), 50);
                });
            };
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
