/**
 * Patients Workspace Interactive Controller
 * Features:
 * - Persistent Keyboard shortcuts (/, ArrowUp, ArrowDown, Esc) with UI toggle switch
 * - Dynamic Drag & Drop active visual zones
 * - Asynchronous AJAX file uploads using XHR to support upload progress meters
 */

(function() {
  'use strict';

  // State
  let shortcutsEnabled = true;

  // DOM Elements
  const shortcutToggle = document.getElementById('shortcutToggle');
  const searchInput = document.getElementById('patientSearchInput');
  const queueList = document.getElementById('patientQueueList');
  const fileInputs = document.querySelectorAll('.js-file-upload');
  const asyncForms = document.querySelectorAll('.js-async-upload-form');
  const dragZones = document.querySelectorAll('.js-drag-zone');

  // --- 1. Keyboard Shortcuts Config & Toggle ---
  function initShortcuts() {
    if (!shortcutToggle) return;

    // Load persistent state from localStorage (default to true)
    const storedState = localStorage.getItem('patients-shortcuts-enabled');
    if (storedState === 'false') {
      shortcutsEnabled = false;
      shortcutToggle.checked = false;
    } else {
      shortcutsEnabled = true;
      shortcutToggle.checked = true;
    }

    shortcutToggle.addEventListener('change', function() {
      shortcutsEnabled = shortcutToggle.checked;
      localStorage.setItem('patients-shortcuts-enabled', shortcutsEnabled);
      showToast(shortcutsEnabled ? 'Keyboard shortcuts enabled' : 'Keyboard shortcuts disabled');
    });

    // Global Keydown Listener
    document.addEventListener('keydown', handleGlobalKeydown);
  }

  function handleGlobalKeydown(e) {
    if (!shortcutsEnabled) return;

    const activeEl = document.activeElement;
    const isInputActive = activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA' || activeEl.tagName === 'SELECT';

    // 1. "/" - Focus patient search (if not already typing in another input)
    if (e.key === '/' && !isInputActive) {
      e.preventDefault();
      if (searchInput) {
        searchInput.focus();
        searchInput.select();
      }
    }

    // 2. "Esc" - Blur patient search
    if (e.key === 'Escape' && activeEl === searchInput) {
      searchInput.blur();
    }

    // 3. ArrowUp / ArrowDown - Navigate patient queue sidebar list
    if ((e.key === 'ArrowDown' || e.key === 'ArrowUp') && !isInputActive) {
      if (!queueList) return;

      const items = Array.from(queueList.querySelectorAll('.queue-item'));
      if (items.length === 0) return;

      e.preventDefault();
      const activeIndex = items.findIndex(item => item.classList.contains('active'));
      let targetIndex = -1;

      if (e.key === 'ArrowDown') {
        if (activeIndex === -1) {
          targetIndex = 0;
        } else if (activeIndex < items.length - 1) {
          targetIndex = activeIndex + 1;
        }
      } else if (e.key === 'ArrowUp') {
        if (activeIndex > 0) {
          targetIndex = activeIndex - 1;
        }
      }

      if (targetIndex !== -1 && items[targetIndex]) {
        const url = items[targetIndex].getAttribute('href');
        if (url) {
          window.location.href = url;
        }
      }
    }
  }

  // --- 2. Drag & Drop Upload Zone Configuration ---
  function initDragAndDrop() {
    dragZones.forEach(zone => {
      const inputId = zone.getAttribute('data-input-id');
      const inputEl = document.getElementById(inputId);
      if (!inputEl) return;

      // Prevent defaults for all drag events
      ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        zone.addEventListener(eventName, preventDefaults, false);
      });

      // Visual feedback classes
      ['dragenter', 'dragover'].forEach(eventName => {
        zone.addEventListener(eventName, () => zone.classList.add('dragover'), false);
      });

      ['dragleave', 'drop'].forEach(eventName => {
        zone.addEventListener(eventName, () => zone.classList.remove('dragover'), false);
      });

      // Handle drop event
      zone.addEventListener('drop', function(e) {
        const dt = e.dataTransfer;
        const files = dt.files;

        if (files && files.length > 0) {
          inputEl.files = files;
          // Trigger the standard change label updates
          triggerInputChange(inputEl);
          // Automatically submit form asynchronously on drop
          const form = zone.closest('form');
          if (form) {
            submitFormAsync(form);
          }
        }
      }, false);
    });
  }

  function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
  }

  function triggerInputChange(input) {
    const event = new Event('change', { bubbles: true });
    input.dispatchEvent(event);
  }

  // --- 3. Label Sync for Native File Inputs ---
  function initFileInputLabels() {
    fileInputs.forEach(input => {
      const targetId = input.getAttribute('data-target');
      const label = targetId ? document.getElementById(targetId) : null;
      if (!label) return;

      const defaultText = label.textContent;
      input.addEventListener('change', function() {
        if (input.files && input.files.length) {
          label.textContent = input.files[0].name;
        } else {
          label.textContent = defaultText;
        }
      });
    });
  }

  // --- 4. Asynchronous AJAX File Upload Handling (XHR with Progress Bar) ---
  function initAsyncUploads() {
    asyncForms.forEach(form => {
      form.addEventListener('submit', function(e) {
        e.preventDefault();
        submitFormAsync(form);
      });
    });
  }

  function submitFormAsync(form) {
    const formData = new FormData(form);
    const actionUrl = form.getAttribute('action') || window.location.href;
    const submitBtn = form.querySelector('.js-submit-btn');

    // Progress Bar Elements
    const progressBarId = form.id === 'insuranceUploadForm' ? 'insuranceProgressBar' : 'docProgressBar';
    const progressContainerId = form.id === 'insuranceUploadForm' ? 'insuranceProgressContainer' : 'docProgressContainer';
    const progressBar = document.getElementById(progressBarId);
    const progressContainer = document.getElementById(progressContainerId);

    if (submitBtn) submitBtn.disabled = true;
    if (progressContainer) progressContainer.style.display = 'block';
    if (progressBar) progressBar.style.width = '0%';

    const xhr = new XMLHttpRequest();
    xhr.open('POST', actionUrl, true);
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

    // Track upload progress
    xhr.upload.addEventListener('progress', function(e) {
      if (e.lengthComputable && progressBar) {
        const percent = Math.round((e.loaded / e.total) * 100);
        progressBar.style.width = percent + '%';
      }
    });

    xhr.onload = function() {
      if (submitBtn) submitBtn.disabled = false;

      // Smooth hide progress meter
      setTimeout(() => {
        if (progressContainer) progressContainer.style.display = 'none';
      }, 600);

      if (xhr.status === 200) {
        try {
          const res = JSON.parse(xhr.responseText);
          if (res.success) {
            showToast(res.message);
            updatePageDOM(form.id, res);
            form.reset();
            // Reset input display label
            const fileInput = form.querySelector('.js-file-upload');
            if (fileInput) triggerInputChange(fileInput);
          } else {
            alert('Upload error: ' + (res.error || 'Unknown error occurred.'));
          }
        } catch (err) {
          // Fallback if parsing failed or non-JSON returned
          window.location.reload();
        }
      } else {
        alert('Server returned an error status: ' + xhr.status);
      }
    };

    xhr.onerror = function() {
      if (submitBtn) submitBtn.disabled = false;
      if (progressContainer) progressContainer.style.display = 'none';
      alert('Upload failed due to connection error.');
    };

    xhr.send(formData);
  }

  // --- 5. DOM Injection on Successful Upload (Zero Page Flash) ---
  function updatePageDOM(formId, data) {
    if (formId === 'insuranceUploadForm') {
      const previewContainer = document.getElementById('insurancePreviewContainer');
      const insuranceFileName = document.getElementById('insuranceFileName');
      const openLink = document.getElementById('openInsuranceLink');
      const metaBlock = document.getElementById('insuranceMetaBlock');

      if (!previewContainer) return;

      // Update image visual or placeholder
      if (data.is_image) {
        previewContainer.innerHTML = `
          <img src="${data.file_url}" alt="${data.title}" id="insurancePreviewImg">
          <span class="insurance-preview-badge">
            <i class="ti-upload"></i>
            <span id="insuranceBadgeLabel">Click to replace</span>
          </span>
        `;
      } else {
        previewContainer.innerHTML = `
          <div class="insurance-placeholder" id="insurancePlaceholder">
            <i class="ti-files"></i>
            <strong id="insuranceDocTitle">${data.title}</strong>
            <div class="small mt-1" id="insuranceDocFilename">${data.filename}</div>
          </div>
          <span class="insurance-preview-badge">
            <i class="ti-upload"></i>
            <span id="insuranceBadgeLabel">Click to replace</span>
          </span>
        `;
      }

      if (insuranceFileName) {
        insuranceFileName.textContent = `Current: ${data.filename}`;
      }

      if (openLink) {
        openLink.setAttribute('href', data.file_url);
      } else {
        // Create the open button if it didn't exist
        const toolbarActions = previewContainer.closest('.insurance-panel').querySelector('.insurance-toolbar-actions');
        if (toolbarActions) {
          const newLink = document.createElement('a');
          newLink.className = 'btn btn-outline-dark btn-sm';
          newLink.id = 'openInsuranceLink';
          newLink.setAttribute('href', data.file_url);
          newLink.setAttribute('target', '_blank');
          newLink.textContent = 'Open Current';
          toolbarActions.insertBefore(newLink, toolbarActions.firstChild);
        }
      }

      // Update meta block details
      if (metaBlock) {
        metaBlock.innerHTML = `Latest file: <span id="metaFilename">${data.filename}</span> · <span id="metaUploadedAt">${data.uploaded_at}</span>`;
      } else {
        const formEl = document.getElementById('insuranceUploadForm');
        const metaDiv = document.createElement('div');
        metaDiv.className = 'insurance-meta';
        metaDiv.id = 'insuranceMetaBlock';
        metaDiv.innerHTML = `Latest file: <span id="metaFilename">${data.filename}</span> · <span id="metaUploadedAt">${data.uploaded_at}</span>`;
        // Insert right above the toolbar
        const toolbar = formEl.querySelector('.insurance-toolbar');
        formEl.insertBefore(metaDiv, toolbar);
      }
    } else if (formId === 'documentUploadForm') {
      const itemsList = document.getElementById('documentItemsList');
      const noDocPlaceholder = document.getElementById('noDocumentsPlaceholder');
      if (!itemsList) return;

      if (noDocPlaceholder) {
        noDocPlaceholder.remove();
      }

      // Create new agreement item node
      const newItem = document.createElement('div');
      newItem.className = 'doc-item';
      newItem.innerHTML = `
        <div class="d-flex justify-content-between align-items-start">
          <div class="d-flex mr-2">
            <div class="doc-icon mr-2">
              ${data.is_image ? '<i class="ti-image"></i>' : '<i class="ti-files"></i>'}
            </div>
            <div>
              <h6>${data.title}</h6>
              <p class="doc-subtitle">${data.doc_type}</p>
              <p class="doc-meta">${data.filename} · ${data.size} · ${data.uploaded_at}</p>
            </div>
          </div>
          <a class="btn btn-outline-primary btn-sm" href="${data.file_url}" target="_blank">
            <i class="ti-download mr-1"></i> Open
          </a>
        </div>
      `;

      // Prepend to list for instantaneous premium feel
      itemsList.insertBefore(newItem, itemsList.firstChild);
    }
  }

  // --- Helper UI Toast notification ---
  function showToast(message) {
    // Check if simple alert banner exists, else create one
    let toast = document.getElementById('patients-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'patients-toast';
      toast.style.cssText = `
        position: fixed;
        bottom: 24px;
        right: 24px;
        background: #252836;
        color: #ffffff;
        padding: 0.75rem 1.25rem;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
        z-index: 9999;
        box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        opacity: 0;
        transform: translateY(10px);
        transition: opacity 0.25s ease, transform 0.25s ease;
      `;
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.style.opacity = '1';
    toast.style.transform = 'translateY(0)';

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
    }, 2800);
  }

  // Initialize
  document.addEventListener('DOMContentLoaded', () => {
    initShortcuts();
    initFileInputLabels();
    initDragAndDrop();
    initAsyncUploads();
  });

})();
