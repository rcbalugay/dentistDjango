document.addEventListener("DOMContentLoaded", function () {
  // Global Safe Deletion Modal Interceptor
  document.addEventListener("submit", function (e) {
    const form = e.target;
    if (form && (form.getAttribute("action") || "").includes("/delete/")) {
      if (form.dataset.confirmed === "true") {
        return;
      }

      e.preventDefault();

      const backdrop = document.createElement("div");
      backdrop.className = "delete-modal-backdrop";

      backdrop.innerHTML = `
        <div class="delete-modal-card">
          <div class="delete-modal-icon">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#dc3545" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
          </div>
          <h4 class="delete-modal-title">Confirm Deletion</h4>
          <p class="delete-modal-message">Are you absolutely sure you want to delete this item? This action is permanent and cannot be undone.</p>
          <div class="delete-modal-actions">
            <button type="button" class="btn btn-light delete-modal-cancel">Cancel</button>
            <button type="button" class="btn btn-danger delete-modal-confirm">Yes, Delete</button>
          </div>
        </div>
      `;

      document.body.appendChild(backdrop);
      document.body.classList.add("delete-modal-open");

      setTimeout(function () {
        backdrop.classList.add("is-active");
      }, 10);

      const close = function () {
        backdrop.classList.remove("is-active");
        setTimeout(function () {
          backdrop.remove();
          document.body.classList.remove("delete-modal-open");
        }, 300);
      };

      backdrop.querySelector(".delete-modal-cancel").addEventListener("click", close);
      backdrop.querySelector(".delete-modal-confirm").addEventListener("click", function () {
        form.dataset.confirmed = "true";
        close();
        form.submit();
      });

      const escHandler = function (event) {
        if (event.key === "Escape") {
          close();
          document.removeEventListener("keydown", escHandler);
        }
      };
      document.addEventListener("keydown", escHandler);
    }
  });

  const forms = Array.from(document.querySelectorAll(".website-form"));
  const buttons = Array.from(document.querySelectorAll("[data-website-tab]"));
  const sections = Array.from(document.querySelectorAll("[data-website-section]"));
  const columns = Array.from(document.querySelectorAll("[data-website-column]"));
  const statusMessage = document.querySelector("[data-website-status-message]");
  const saveButton = document.querySelector("[data-website-save-button]");
  const storageKey = "websiteManagementActiveTab";
  const fallbackTab = "homepage";

  if (!forms.length) {
    return;
  }

  let justSaved = false;
  let isSubmitting = false;
  try {
    const currentUrl = new URL(window.location.href);
    justSaved = currentUrl.searchParams.get("saved") === "1";

    if (justSaved) {
      currentUrl.searchParams.delete("saved");
      const nextSearch = currentUrl.searchParams.toString();
      const nextUrl = currentUrl.pathname + (nextSearch ? "?" + nextSearch : "") + currentUrl.hash;
      window.history.replaceState({}, "", nextUrl);

      // Generate the toast
      const toast = document.createElement("div");
      toast.className = "website-toast";
      toast.textContent = "Saved just now.";
      document.body.appendChild(toast);
      setTimeout(() => toast.remove(), 4000);
    }
  } catch (error) { }

  window.addEventListener("beforeunload", function (e) {
    if (isSubmitting) {
      return;
    }
    if (document.querySelector(".website-tab-btn.has-changes")) {
      e.preventDefault();
    }
  });

  document.addEventListener("keydown", function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key === "s") {
      e.preventDefault();
      if (saveButton && saveButton.classList.contains("is-dirty")) {
        const activeFormId = saveButton.getAttribute("form");
        const activeForm = document.getElementById(activeFormId);
        if (activeForm) {
          activeForm.requestSubmit(saveButton);
        }
      }
    }
  });

  function clearErrors() {
    document.querySelectorAll(".is-invalid").forEach(function (el) {
      el.classList.remove("is-invalid");
    });
    document.querySelectorAll(".website-field-error").forEach(function (el) {
      el.remove();
    });
  }

  function handleValidationErrors(errors) {
    clearErrors();
    let firstInvalidInput = null;

    Object.keys(errors).forEach(function (fieldName) {
      const fieldErrors = errors[fieldName];
      const input = document.querySelector('[name="' + fieldName + '"]');
      if (input) {
        input.classList.add("is-invalid");

        const errorEl = document.createElement("div");
        errorEl.className = "website-field-error";
        const errorMsgs = fieldErrors.map(function (err) {
          return err.message;
        }).join(" ");
        errorEl.textContent = errorMsgs;

        const formGroup = input.closest(".form-group");
        if (formGroup) {
          const mediaPreview = formGroup.nextElementSibling;
          if (mediaPreview && mediaPreview.classList.contains("website-media-preview")) {
            mediaPreview.insertAdjacentElement("afterend", errorEl);
          } else {
            formGroup.appendChild(errorEl);
          }
        } else {
          input.insertAdjacentElement("afterend", errorEl);
        }

        if (!firstInvalidInput) {
          firstInvalidInput = input;
        }
      }
    });

    if (firstInvalidInput) {
      const section = firstInvalidInput.closest("[data-website-section]");
      if (section) {
        const tabName = section.dataset.websiteSection;
        activateTab(tabName);

        if (section.classList.contains("is-collapsed")) {
          setPanelCollapsed(section, false);
        }

        setTimeout(function () {
          firstInvalidInput.scrollIntoView({ behavior: "smooth", block: "center" });
          firstInvalidInput.focus();
        }, 150);
      }
    }
  }

  const trackedInputs = Array.from(
    document.querySelectorAll(".website-section input, .website-section textarea, .website-section select")
  ).filter(function (input) {
    return !["hidden", "submit", "button"].includes(input.type);
  });
  const fileInputs = trackedInputs.filter(function (input) {
    return input.type === "file";
  });

  const initialValues = new Map();
  const filePreviewState = new Map();

  function getInputState(input) {
    if (input.type === "file") {
      return input.files && input.files.length > 0 ? "__has_file__" : "";
    }

    if (input.type === "checkbox" || input.type === "radio") {
      return input.checked ? "checked" : "unchecked";
    }

    return input.value;
  }

  trackedInputs.forEach(function (input) {
    initialValues.set(input, getInputState(input));
  });

  function getFilePreviewForInput(input) {
    const group = input.closest(".form-group");
    if (!group) {
      return null;
    }

    const existingPreview = group.nextElementSibling;
    if (existingPreview && existingPreview.classList.contains("website-media-preview")) {
      return existingPreview;
    }

    return null;
  }

  function buildFilePreview(input) {
    const group = input.closest(".form-group");
    if (!group) {
      return null;
    }

    const preview = document.createElement("div");
    preview.className = "website-media-preview";
    if (input.name === "page_banner_background") {
      preview.classList.add("website-media-preview--widescreen");
    }

    const label = document.createElement("span");
    label.className = "website-preview-label";
    label.textContent = "Selected image";

    const image = document.createElement("img");
    image.alt = "Selected image preview";

    preview.appendChild(label);
    preview.appendChild(image);
    group.insertAdjacentElement("afterend", preview);
    return preview;
  }

  fileInputs.forEach(function (input) {
    const preview = getFilePreviewForInput(input);
    const previewLabel = preview ? preview.querySelector(".website-preview-label") : null;
    const previewImage = preview ? preview.querySelector("img") : null;

    filePreviewState.set(input, {
      preview: preview,
      initialLabel: previewLabel ? previewLabel.textContent : "",
      initialSrc: previewImage ? previewImage.getAttribute("src") : "",
    });
  });

  function setPanelCollapsed(section, collapsed) {
    section.classList.toggle("is-collapsed", collapsed);
    const toggle = section.querySelector(".website-panel-toggle");
    if (toggle) {
      toggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
    }
  }

  function initialiseSectionPanels() {
    const firstOpenByTab = new Set();

    sections.forEach(function (section) {
      if (section.dataset.panelReady === "true") {
        return;
      }

      const kicker = section.querySelector(".website-kicker");
      const heading = section.querySelector("h5");
      const meta = section.querySelector(".website-meta");

      const toggle = document.createElement("button");
      toggle.type = "button";
      toggle.className = "website-panel-toggle";

      const headingWrap = document.createElement("div");
      headingWrap.className = "website-panel-heading";

      if (kicker) {
        headingWrap.appendChild(kicker);
      }

      if (heading) {
        headingWrap.appendChild(heading);
      }

      if (meta) {
        headingWrap.appendChild(meta);
      }

      const chevron = document.createElement("span");
      chevron.className = "website-panel-chevron";
      chevron.setAttribute("aria-hidden", "true");

      toggle.appendChild(headingWrap);
      toggle.appendChild(chevron);

      section.insertBefore(toggle, section.firstChild);

      const body = document.createElement("div");
      body.className = "website-panel-body";

      Array.from(section.childNodes).forEach(function (node) {
        if (node !== toggle) {
          body.appendChild(node);
        }
      });

      section.appendChild(body);
      section.dataset.panelReady = "true";

      const tabName = section.dataset.websiteSection;
      const shouldCollapse = firstOpenByTab.has(tabName);
      setPanelCollapsed(section, shouldCollapse);
      firstOpenByTab.add(tabName);

      toggle.addEventListener("click", function () {
        const shouldOpen = section.classList.contains("is-collapsed");
        setPanelCollapsed(section, !shouldOpen);
        if (shouldOpen) {
          const anchor = getPreviewAnchorForSection(section);
          if (anchor) {
            scrollToPreviewAnchor(anchor);
          }
        }
      });
    });
  }

  initialiseSectionPanels();

  function formatTabName(name) {
    const labels = {
      homepage: "Homepage",
      about: "About & Subpages",
    };

    return labels[name] || name;
  }

  function formatDirtyTabs(dirtyTabs) {
    const labels = dirtyTabs.map(formatTabName);

    if (labels.length <= 1) {
      return labels[0] || "";
    }

    if (labels.length === 2) {
      return labels.join(" and ");
    }

    return labels.slice(0, -1).join(", ") + ", and " + labels[labels.length - 1];
  }

  function isInputDirty(input) {
    return getInputState(input) !== initialValues.get(input);
  }

  function updateStatusMessage(dirtyTabs) {
    if (!statusMessage || !saveButton) {
      return;
    }

    if (!dirtyTabs.length) {
      if (justSaved) {
        statusMessage.textContent = "Saved just now. You're editing the latest version.";
        statusMessage.classList.remove("is-dirty");
        statusMessage.classList.add("is-saved");
        saveButton.classList.remove("is-dirty");
        saveButton.classList.add("is-saved");
        saveButton.disabled = true;
        return;
      }

      statusMessage.textContent = "No unsaved changes. You're editing the saved version.";
      statusMessage.classList.remove("is-dirty");
      statusMessage.classList.remove("is-saved");
      saveButton.classList.remove("is-dirty");
      saveButton.classList.remove("is-saved");
      saveButton.disabled = true;
      return;
    }

    const tabSummary = formatDirtyTabs(dirtyTabs);
    const copy = dirtyTabs.length === 1
      ? "Unsaved changes in " + tabSummary + ". Save when you're ready."
      : "Unsaved changes in " + tabSummary + ". Save to publish this round of edits.";

    statusMessage.textContent = copy;
    statusMessage.classList.add("is-dirty");
    statusMessage.classList.remove("is-saved");
    saveButton.classList.add("is-dirty");
    saveButton.classList.remove("is-saved");
    saveButton.disabled = false;
  }

  function syncDirtyState() {
    const dirtyTabs = [];

    buttons.forEach(function (button) {
      button.classList.remove("has-changes");
    });

    sections.forEach(function (section) {
      let sectionDirty = false;

      section.querySelectorAll(".form-group").forEach(function (group) {
        group.classList.remove("is-dirty");
      });

      section.querySelectorAll(".website-media-preview").forEach(function (preview) {
        preview.classList.remove("is-dirty");
      });

      trackedInputs.forEach(function (input) {
        if (!section.contains(input) || !isInputDirty(input)) {
          return;
        }

        sectionDirty = true;

        const group = input.closest(".form-group");
        if (group) {
          group.classList.add("is-dirty");

          const preview = group.nextElementSibling;
          if (preview && preview.classList.contains("website-media-preview")) {
            preview.classList.add("is-dirty");
          }
        }
      });

      if (sectionDirty) {
        dirtyTabs.push(section.dataset.websiteSection);

        const button = buttons.find(function (candidate) {
          return candidate.dataset.websiteTab === section.dataset.websiteSection;
        });

        if (button) {
          button.classList.add("has-changes");
        }
      }
    });

    updateStatusMessage(dirtyTabs);
  }

  function updateColumns() {
    const visibleColumns = [];

    columns.forEach(function (column) {
      const visibleSection = column.querySelector(".website-section:not(.is-hidden)");
      column.classList.toggle("is-hidden", !visibleSection);
      column.classList.remove("website-column--expanded");

      if (visibleSection) {
        visibleColumns.push(column);
      }
    });

    if (visibleColumns.length === 1) {
      visibleColumns[0].classList.add("website-column--expanded");
    }
  }

  function updateFilePreview(input) {
    const state = filePreviewState.get(input);
    if (!state) {
      return;
    }

    const selectedFile = input.files && input.files[0];
    let preview = state.preview;

    if (!selectedFile) {
      if (preview && state.initialSrc) {
        const label = preview.querySelector(".website-preview-label");
        const image = preview.querySelector("img");

        if (label) {
          label.textContent = state.initialLabel || "Current image";
        }

        if (image) {
          image.src = state.initialSrc;
        }

        preview.classList.remove("is-dirty");
        return;
      }

      if (preview && !state.initialSrc) {
        preview.remove();
        state.preview = null;
      }
      return;
    }

    if (!preview) {
      preview = buildFilePreview(input);
      state.preview = preview;
    }

    const label = preview ? preview.querySelector(".website-preview-label") : null;
    const image = preview ? preview.querySelector("img") : null;
    if (!preview || !label || !image) {
      return;
    }

    const reader = new FileReader();
    reader.onload = function (event) {
      label.textContent = "Selected image (not saved yet)";
      image.src = event.target.result;
      preview.classList.add("is-dirty");
    };
    reader.readAsDataURL(selectedFile);
  }

  function activateTab(name) {
    const validTabs = buttons.map(function (button) {
      return button.dataset.websiteTab;
    });
    const resolvedName = validTabs.includes(name) ? name : fallbackTab;

    buttons.forEach(function (button) {
      const isActive = button.dataset.websiteTab === resolvedName;
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-selected", isActive ? "true" : "false");
      button.setAttribute("tabindex", isActive ? "0" : "-1");
    });

    sections.forEach(function (section) {
      section.classList.toggle("is-hidden", section.dataset.websiteSection !== resolvedName);
    });

    forms.forEach(function (currentForm) {
      const isActiveForm = currentForm.id === resolvedName + "-form";
      currentForm.style.display = isActiveForm ? "block" : "none";
    });

    if (saveButton) {
      saveButton.setAttribute("form", resolvedName + "-form");
    }

    // Sync active tab preview page
    const previewPages = Array.from(document.querySelectorAll("[data-preview-page]"));
    previewPages.forEach(function (page) {
      page.classList.toggle("is-hidden", page.dataset.previewPage !== resolvedName);
    });

    updateColumns();
    syncDirtyState();
    window.scrollTo({ top: 0, behavior: "smooth" });

    // Automatically focus the first open section in this tab on switch
    setTimeout(function() {
      const activeSection = sections.find(function (sec) {
        return sec.dataset.websiteSection === resolvedName && !sec.classList.contains("is-collapsed");
      });
      if (activeSection) {
        const anchor = getPreviewAnchorForSection(activeSection);
        if (anchor) {
          scrollToPreviewAnchor(anchor, true);
        }
      }
    }, 50);

    try {
      localStorage.setItem(storageKey, resolvedName);
    } catch (error) { }
  }

  let initialTab = window.websiteActiveTab || fallbackTab;
  if (initialTab === "None" || !initialTab) {
    try {
      initialTab = localStorage.getItem(storageKey) || fallbackTab;
    } catch (error) {
      initialTab = fallbackTab;
    }
  }

  activateTab(initialTab);

  buttons.forEach(function (button) {
    button.addEventListener("click", function () {
      activateTab(button.dataset.websiteTab);
    });
  });

  // WAI-ARIA Keyboard arrow key tab cycling
  const tablist = document.querySelector('[role="tablist"]');
  if (tablist) {
    tablist.addEventListener("keydown", function (e) {
      const activeBtn = document.activeElement;
      if (!activeBtn || activeBtn.getAttribute("role") !== "tab") {
        return;
      }

      const tabIndex = buttons.indexOf(activeBtn);
      let nextIndex = -1;

      if (e.key === "ArrowRight") {
        nextIndex = (tabIndex + 1) % buttons.length;
      } else if (e.key === "ArrowLeft") {
        nextIndex = (tabIndex - 1 + buttons.length) % buttons.length;
      } else if (e.key === "Home") {
        nextIndex = 0;
      } else if (e.key === "End") {
        nextIndex = buttons.length - 1;
      }

      if (nextIndex !== -1) {
        e.preventDefault();
        const nextButton = buttons[nextIndex];
        nextButton.focus();
        activateTab(nextButton.dataset.websiteTab);
      }
    });
  }

  // Dynamic Character Counters
  const countableInputs = Array.from(document.querySelectorAll('.form-group input[maxlength], .form-group textarea[maxlength]'));
  countableInputs.forEach(function (input) {
    const maxLength = parseInt(input.getAttribute("maxlength"), 10);
    const counterEl = document.createElement("div");
    counterEl.className = "website-char-counter";

    function updateCounter() {
      const currentLength = input.value.length;
      counterEl.textContent = currentLength + " / " + maxLength;
      counterEl.classList.toggle("is-near-limit", currentLength >= maxLength - 10);
    }

    updateCounter();
    input.addEventListener("input", updateCounter);
    input.insertAdjacentElement("afterend", counterEl);
  });

  // Dynamic Drag-and-Drop File Upload Dropzones
  fileInputs.forEach(function (input) {
    const parent = input.parentNode;
    if (!parent) return;

    const dropzone = document.createElement("div");
    dropzone.className = "website-file-dropzone";

    const icon = document.createElement("div");
    icon.className = "website-dropzone-icon";
    icon.innerHTML = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>';

    const text = document.createElement("div");
    text.className = "website-dropzone-text";
    text.innerHTML = 'Drag and drop or <strong>browse</strong>';

    const hint = document.createElement("div");
    hint.className = "website-dropzone-hint";
    hint.textContent = "Support PNG, JPG, or WEBP (max. 10MB)";

    // Insert dropzone and nest input
    parent.insertBefore(dropzone, input);
    dropzone.appendChild(input);
    dropzone.insertBefore(icon, input);
    dropzone.insertBefore(text, input);
    dropzone.insertBefore(hint, input);

    // Drag events
    ["dragenter", "dragover"].forEach(function (eventName) {
      dropzone.addEventListener(eventName, function (e) {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add("is-dragover");
      }, false);
    });

    ["dragleave", "drop"].forEach(function (eventName) {
      dropzone.addEventListener(eventName, function (e) {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove("is-dragover");
      }, false);
    });

    dropzone.addEventListener("drop", function (e) {
      const dt = e.dataTransfer;
      const files = dt.files;
      if (files && files.length > 0) {
        input.files = files;
        input.dispatchEvent(new Event("change", { bubbles: true }));
        input.dispatchEvent(new Event("input", { bubbles: true }));
      }
    }, false);
  });

  // Live Preview Synchronization Config and Mappings
  const textMappings = {
    // Homepage fields
    'hero_title': '#preview-hero-title',
    'hero_subtitle': '#preview-hero-subtitle',
    'hero_cta_text': '#preview-hero-cta',
    'hero_slide_2_title': '#preview-hero-slide-2-title',
    'hero_slide_2_subtitle': '#preview-hero-slide-2-subtitle',
    'hero_slide_2_cta_text': '#preview-hero-slide-2-cta-text',
    'home_services_kicker': '#preview-home-services-kicker',
    'home_services_heading': '#preview-home-services-heading',
    'home_services_intro': '#preview-home-services-intro',
    'home_intro_heading': '#preview-home-intro-heading',
    'home_intro_text': '#preview-home-intro-text',
    'home_doctor_kicker': '#preview-home-doctor-kicker',
    'home_doctor_heading': '#preview-home-doctor-heading',
    'home_doctor_intro': '#preview-home-doctor-intro',
    'doctor_name': '#preview-doctor-name',
    'doctor_title': '#preview-doctor-title',
    'doctor_bio': '#preview-doctor-bio',

    // About fields
    'about_kicker': '#preview-about-kicker',
    'about_heading': '#preview-about-heading',
    'about_summary': '#preview-about-summary',
    'about_founder_name': '#preview-about-founder-name',
    'about_founder_title': '#preview-about-founder-title',
    'services_page_title': '#preview-services-page-title',
    'contact_page_title': '#preview-contact-page-title',
    'contact_form_heading': '#preview-contact-form-heading'
  };

  const imageMappings = {
    'hero_slide_1_background': { selector: '#preview-hero-bg-1', isBg: true },
    'hero_slide_2_background': { selector: '#preview-hero-bg-2', isBg: true },
    'home_intro_background': { selector: '#preview-home-intro-background', isBg: true },
    'about_side_image': { selector: '#preview-about-side-image', isBg: true },
    'about_founder_photo': { selector: '#preview-about-founder-photo', isBg: true },
    'page_banner_background': { selector: '#preview-page-banner-background', isBg: true }
  };

  const initialImageStates = new Map();

  Object.keys(imageMappings).forEach(function (name) {
    const config = imageMappings[name];
    const target = document.querySelector(config.selector);
    if (target) {
      initialImageStates.set(name, {
        backgroundImage: target.style.backgroundImage || "",
        src: target.tagName === 'IMG' ? target.src : null
      });
    }
  });

  function syncTextInput(input) {
    const selector = textMappings[input.name];
    if (!selector) return;

    const target = document.querySelector(selector);
    if (!target) return;

    const fallback = input.placeholder || "";
    target.textContent = input.value.trim() || fallback;
  }

  function syncImageInput(input) {
    const config = imageMappings[input.name];
    if (!config) return;

    const target = document.querySelector(config.selector);
    if (!target) return;

    const file = input.files && input.files[0];
    const placeholder = target.querySelector(".preview-img-frame-placeholder, svg");

    if (file) {
      const reader = new FileReader();
      reader.onload = function (e) {
        if (config.isBg) {
          target.style.backgroundImage = `url('${e.target.result}')`;
        } else {
          target.src = e.target.result;
        }
        if (placeholder) {
          placeholder.style.display = "none";
        }
      };
      reader.readAsDataURL(file);
    } else {
      const initialState = initialImageStates.get(input.name);
      if (initialState) {
        if (config.isBg) {
          target.style.backgroundImage = initialState.backgroundImage;
        } else {
          target.src = initialState.src;
        }
        const hasOriginal = config.isBg ? initialState.backgroundImage : initialState.src;
        if (placeholder) {
          placeholder.style.display = hasOriginal ? "none" : "";
        }
      }
    }
  }

  function getPreviewAnchorForSection(section) {
    const h5 = section.querySelector("h5");
    if (!h5) return null;
    const title = h5.textContent.trim().toLowerCase();

    if (title.includes("hero slide 1")) return "hero-1";
    if (title.includes("hero slide 2")) return "hero-2";
    if (title.includes("services section intro") || title.includes("services, testimonials")) return "services-intro";
    if (title.includes("intro banner")) return "intro-banner";
    if (title.includes("featured doctor")) return "featured-doctor";
    if (title.includes("about page intro") || title.includes("about page side image")) return "about-intro";
    if (title.includes("founder profile")) return "founder-profile";
    if (title.includes("shared page banner")) return "shared-banner";
    if (title.includes("subpage title")) return "subpage-headings";

    return null;
  }

  function scrollToPreviewAnchor(anchor, instant = false) {
    const targetPreview = document.querySelector('[data-preview-section-anchor="' + anchor + '"]');
    const browserBody = document.querySelector(".preview-browser-body");

    if (browserBody && targetPreview) {
      document.querySelectorAll(".preview-section").forEach(function (sec) {
        sec.classList.remove("is-focused");
      });

      targetPreview.classList.add("is-focused");

      if (anchor === "hero-1") {
        const hero1 = document.getElementById("preview-section-hero-1");
        const hero2 = document.getElementById("preview-section-hero-2");
        if (hero1) hero1.classList.add("is-active");
        if (hero2) hero2.classList.remove("is-active");
      } else if (anchor === "hero-2") {
        const hero1 = document.getElementById("preview-section-hero-1");
        const hero2 = document.getElementById("preview-section-hero-2");
        if (hero1) hero1.classList.remove("is-active");
        if (hero2) hero2.classList.add("is-active");
      }

      const bodyRect = browserBody.getBoundingClientRect();
      const targetRect = targetPreview.getBoundingClientRect();
      const relativeTop = targetRect.top - bodyRect.top + browserBody.scrollTop;
      const scrollPosition = relativeTop - (bodyRect.height / 2) + (targetRect.height / 2);

      browserBody.scrollTo({
        top: Math.max(0, scrollPosition),
        behavior: instant ? "auto" : "smooth"
      });
    }
  }

  // Floating Mobile/Tablet Toggle FAB logic
  const fab = document.getElementById("website-preview-toggle-fab");
  const previewColumn = document.querySelector('[data-website-column="preview"]');
  if (fab && previewColumn) {
    fab.addEventListener("click", function () {
      const isActive = previewColumn.classList.toggle("is-active");
      const eyeOpen = fab.querySelector(".icon-eye-open");
      const eyeClose = fab.querySelector(".icon-eye-close");
      if (eyeOpen && eyeClose) {
        eyeOpen.classList.toggle("is-hidden", isActive);
        eyeClose.classList.toggle("is-hidden", !isActive);
      }
    });

    // Close preview on backdrop overlay click
    previewColumn.addEventListener("click", function (e) {
      if (e.target === previewColumn) {
        previewColumn.classList.remove("is-active");
        const eyeOpen = fab.querySelector(".icon-eye-open");
        const eyeClose = fab.querySelector(".icon-eye-close");
        if (eyeOpen && eyeClose) {
          eyeOpen.classList.remove("is-hidden");
          eyeClose.classList.add("is-hidden");
        }
      }
    });
  }

  // Initialize text preview values on page load
  trackedInputs.forEach(function (input) {
    if (input.type !== "file") {
      syncTextInput(input);
    }
  });

  // Automatically focus first section on load
  setTimeout(function() {
    const activeTabButton = buttons.find(function(btn) { return btn.classList.contains("is-active"); });
    const tabName = activeTabButton ? activeTabButton.dataset.websiteTab : fallbackTab;
    const activeSection = sections.find(function (sec) {
      return sec.dataset.websiteSection === tabName && !sec.classList.contains("is-collapsed");
    });
    if (activeSection) {
      const anchor = getPreviewAnchorForSection(activeSection);
      if (anchor) {
        scrollToPreviewAnchor(anchor, true);
      }
    }
  }, 100);

  // Set up event listeners for syncing input changes
  trackedInputs.forEach(function (input) {
    input.addEventListener("input", function () {
      justSaved = false;
      input.classList.remove("is-invalid");
      const group = input.closest(".form-group");
      if (group) {
        const err = group.querySelector(".website-field-error");
        if (err) err.remove();
      }
      syncDirtyState();
      syncTextInput(input);
    });
    input.addEventListener("change", function () {
      justSaved = false;
      input.classList.remove("is-invalid");
      const group = input.closest(".form-group");
      if (group) {
        const err = group.querySelector(".website-field-error");
        if (err) err.remove();
      }
      if (input.type === "file") {
        updateFilePreview(input);
        syncImageInput(input);
      } else {
        syncTextInput(input);
      }
      syncDirtyState();
    });
  });

  forms.forEach(function (currentForm) {
    currentForm.addEventListener("submit", function (e) {
      e.preventDefault();
      justSaved = false;
      isSubmitting = true;

      if (statusMessage) {
        statusMessage.textContent = "Saving changes...";
        statusMessage.classList.remove("is-dirty");
        statusMessage.classList.remove("is-saved");
      }

      if (saveButton) {
        saveButton.classList.remove("is-dirty");
        saveButton.classList.remove("is-saved");
        saveButton.disabled = true;
      }

      const formData = new FormData(currentForm);
      const action = currentForm.getAttribute("action") || window.location.href;

      fetch(action, {
        method: "POST",
        body: formData,
        headers: {
          "X-Requested-With": "XMLHttpRequest"
        }
      })
      .then(function (response) {
        if (response.status === 403) {
          isSubmitting = false;
          // CSRF or Session expired!
          if (saveButton) {
            saveButton.disabled = false;
            saveButton.classList.add("is-dirty");
          }
          if (statusMessage) {
            statusMessage.textContent = "Session expired. Your changes are preserved — please copy your edits, reload the page, and try again.";
            statusMessage.classList.add("is-dirty");
            statusMessage.classList.remove("is-saved");
          }

          // Show premium red warning toast
          const toast = document.createElement("div");
          toast.className = "website-toast website-toast--danger";
          toast.textContent = "Session expired. Edits preserved. Copy changes, reload, and try again.";
          document.body.appendChild(toast);
          setTimeout(function () {
            toast.remove();
          }, 6000);
          return null;
        }

        if (response.ok) {
          return response.json();
        } else if (response.status === 400) {
          isSubmitting = false;
          return response.json().then(function (data) {
            if (data && data.errors) {
              handleValidationErrors(data.errors);
            }
            if (saveButton) {
              saveButton.disabled = false;
              saveButton.classList.add("is-dirty");
            }
            if (statusMessage) {
              statusMessage.textContent = "Some fields have validation errors. Please fix them before saving.";
              statusMessage.classList.add("is-dirty");
            }
            throw new Error("Validation failed");
          });
        } else {
          isSubmitting = false;
          throw new Error("Server responded with status: " + response.status);
        }
      })
      .then(function (data) {
        if (data && data.success) {
          // Success! Redirect to standard destination page (which triggers standard green toast)
          window.location.href = data.redirect_url;
        }
      })
      .catch(function (error) {
        isSubmitting = false;
        if (error.message === "Validation failed") {
          return;
        }

        if (saveButton) {
          saveButton.disabled = false;
          saveButton.classList.add("is-dirty");
        }
        if (statusMessage) {
          statusMessage.textContent = "An error occurred while saving. Please check your network and try again.";
          statusMessage.classList.add("is-dirty");
        }

        // Show red warning toast for connection issue
        const toast = document.createElement("div");
        toast.className = "website-toast website-toast--danger";
        toast.textContent = "Save failed. Please check your connection and try again.";
        document.body.appendChild(toast);
        setTimeout(function () {
          toast.remove();
        }, 4000);
      });
    });
  });
});
