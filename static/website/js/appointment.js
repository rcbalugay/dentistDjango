document.addEventListener('DOMContentLoaded', () => {
  const dateInput   = document.getElementById('datepicker');     // hidden form field (date)
  const calendarDiv = document.getElementById('calendarHost');   // desktop inline calendar container
  const slotWrap    = document.getElementById('timeslotWrap');
  const slotList    = document.getElementById('timeslotList');
  const slotHint    = document.getElementById('slotHint');
  const timeField   = document.getElementById('appointment_time');
  const form        = document.getElementById('appointmentForm');
  const matrixContainer = document.getElementById('mobileMatrix');
  const clientDialog = document.getElementById('bookingNoticeModal');
  const clientDialogTitle = document.getElementById('bookingNoticeTitle');
  const clientDialogSubtitle = document.getElementById('bookingNoticeSubtitle');
  const clientDialogMessage = document.getElementById('bookingNoticeMessage');
  let selectedDateIso = dateInput && dateInput.value ? dateInput.value : '';
  let selectedTime = timeField && timeField.value ? timeField.value : '';
  let renderMatrix = null;

  if (!form) {
    return;
  }

  // Build time labels: 9:00 AM â€“ 5:00 PM (1-hour steps)
  const buildDefaultSlotLabels = () => {
    const labels = [];
    for (let h = 9; h <= 17; h++) {
      const hour12 = ((h + 11) % 12) + 1; // 1..12
      const ampm   = h < 12 ? 'AM' : 'PM';
      labels.push(`${hour12}:00 ${ampm}`);
    }
    return labels;
  };

  const scheduleEl = document.getElementById('clinic-schedule');
  const fallbackSchedule = {
    open_weekdays_js: [0, 1, 3, 6], // Sun, Mon, Wed, Sat
    slot_labels: buildDefaultSlotLabels(),
  };

  let clinicSchedule = fallbackSchedule;
  if (scheduleEl) {
    try {
      clinicSchedule = {
        ...fallbackSchedule,
        ...JSON.parse(scheduleEl.textContent),
      };
    } catch (error) {
      console.warn('Invalid clinic schedule payload; using fallback schedule.', error);
    }
  }

  const openWeekdays = new Set(clinicSchedule.open_weekdays_js);
  const buildSlotLabels = () => clinicSchedule.slot_labels;

  // MOBILE MATRIX ONLY: strip AM/PM for display
  const displayTimeLabel = (value) =>
    value.replace(' AM', '').replace(' PM', '');

  const formatIsoLocalDate = (d) => {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  const parseIsoLocalDate = (value) => {
    if (!value) {
      return null;
    }

    const [year, month, day] = value.split('-').map(Number);
    if (!year || !month || !day) {
      return null;
    }

    return new Date(year, month - 1, day);
  };

  // Format date like: Tuesday, November 11, 2025
  const formatPrettyDate = (d) =>
    d.toLocaleDateString(undefined, {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric'
    });

  // Open days: Mon (1), Wed (3), Sat (6), Sun (0)
  const isOpenDay = (d) => openWeekdays.has(d.getDay());

  const showDesktopSlotsForDate = (picked) => {
    if (!picked || !isOpenDay(picked)) {
      if (slotWrap) slotWrap.classList.add('timeslots--hidden');
      return;
    }

    if (slotWrap) {
      slotWrap.classList.remove('timeslots--hidden');
    }
    if (slotHint) {
      slotHint.textContent = `Available time slots for ${formatPrettyDate(picked)}`;
    }
    renderDesktopSlots();
  };

  const openClientDialog = ({ title, subtitle, message }) => {
    if (!clientDialog) {
      return;
    }

    if (clientDialogTitle) {
      clientDialogTitle.textContent = title;
    }
    if (clientDialogSubtitle) {
      clientDialogSubtitle.textContent = subtitle;
    }
    if (clientDialogMessage) {
      clientDialogMessage.textContent = message;
    }

    clientDialog.classList.add('is-open');
    document.body.classList.add('booking-modal-open');
  };

  const closeClientDialog = () => {
    if (!clientDialog) {
      return;
    }

    clientDialog.classList.remove('is-open');
    document.body.classList.remove('booking-modal-open');
  };

  if (clientDialog) {
    clientDialog.querySelectorAll('[data-client-dialog-close]').forEach((element) => {
      element.addEventListener('click', closeClientDialog);
    });
  }

  const applySuggestedSlot = (dateValue, timeValue) => {
    if (!dateValue || !timeValue) {
      return;
    }

    const pickedDate = parseIsoLocalDate(dateValue);
    const flatpickrInstance = calendarDiv && calendarDiv._flatpickr ? calendarDiv._flatpickr : null;

    selectedDateIso = dateValue;
    selectedTime = timeValue;

    if (dateInput) {
      dateInput.value = dateValue;
    }
    if (timeField) {
      timeField.value = timeValue;
    }

    if (flatpickrInstance && dateValue) {
      flatpickrInstance.setDate(dateValue, false);
    }

    if (pickedDate) {
      showDesktopSlotsForDate(pickedDate);
    }

    if (typeof renderMatrix === 'function') {
      renderMatrix();
    }
  };

  window.addEventListener('appointment:suggestion-selected', (event) => {
    if (!event.detail) {
      return;
    }

    applySuggestedSlot(event.detail.dateValue, event.detail.timeValue);
  });

  // ===========================
  // DESKTOP: calendar + slot list
  // ===========================
  function renderDesktopSlots() {
    if (!slotList) return;
    slotList.innerHTML = '';
    const selectedTime = timeField.value;

    buildSlotLabels().forEach(label => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'slot-btn';

      // DESKTOP: show full label with AM/PM
      btn.textContent = label;
      if (label === selectedTime) {
        btn.classList.add('is-active');
      }
      btn.addEventListener('click', () => {
        Array.from(slotList.querySelectorAll('.slot-btn'))
          .forEach(b => b.classList.remove('is-active'));
        btn.classList.add('is-active');
        timeField.value = label; // submit full value with AM/PM
      });

      slotList.appendChild(btn);
    });
  }

  // Use flatpickr if present (desktop only)
  if (calendarDiv && typeof flatpickr !== 'undefined') {
    flatpickr(calendarDiv, {
      inline: true,
      minDate: 'today',
      dateFormat: 'Y-m-d',
      defaultDate: dateInput.value || null,
      onReady: (selectedDates) => {
        if (!selectedDates.length) {
          return;
        }

        const picked = selectedDates[0];

        if (!isOpenDay(picked)) {
          return;
        }

        if (slotWrap) {
          slotWrap.classList.remove('timeslots--hidden');
        }
        if (slotHint) {
          slotHint.textContent = `Available time slots for ${formatPrettyDate(picked)}`;
        }

        renderDesktopSlots();
      },
      onChange: (selectedDates, dateStr) => {
        dateInput.value = dateStr || '';
        timeField.value = '';
        if (slotList) {
          slotList.innerHTML = '';
        }

        if (!selectedDates.length) {
          if (slotWrap) slotWrap.classList.add('timeslots--hidden');
          if (slotHint) slotHint.textContent = 'Select a date to see available time slots';
          return;
        }

        const picked = selectedDates[0];

        // respect open days
        if (!isOpenDay(picked)) {
          if (slotWrap) slotWrap.classList.add('timeslots--hidden');
          if (slotHint) {
            slotHint.textContent =
              'We are closed on this day. Please choose Monday, Wednesday, Saturday, or Sunday.';
          }
          return;
        }

        if (slotWrap) slotWrap.classList.remove('timeslots--hidden');
        if (slotHint) {
          slotHint.textContent = `Available time slots for ${formatPrettyDate(picked)}`;
        }
        renderDesktopSlots();
      }
    });
  }

  // ===========================
  // MOBILE/TABLET: matrix view
  // ===========================
  if (matrixContainer) {
    let weekOffset = 0; // 0 = this week (today..today+6)

    renderMatrix = () => {
      matrixContainer.innerHTML = '';

      // header with prev/next
      const header = document.createElement('div');
      header.className = 'appt-matrix-header';

      const prevBtn = document.createElement('button');
      prevBtn.type = 'button';
      prevBtn.className = 'appt-matrix-nav appt-matrix-nav-prev';
      prevBtn.textContent = '<';
      prevBtn.disabled = weekOffset === 0;

      prevBtn.addEventListener('click', () => {
        if (weekOffset > 0) {
          weekOffset -= 1;
          renderMatrix();
        }
      });

      const nextBtn = document.createElement('button');
      nextBtn.type = 'button';
      nextBtn.className = 'appt-matrix-nav appt-matrix-nav-next';
      nextBtn.textContent = '>';

      nextBtn.addEventListener('click', () => {
        weekOffset += 1;
        renderMatrix();
      });

      const weekLabel = document.createElement('div');
      weekLabel.className = 'appt-matrix-week-label';

      const start = new Date();
      start.setHours(0, 0, 0, 0);
      start.setDate(start.getDate() + weekOffset * 7);

      const end = new Date(start);
      end.setDate(start.getDate() + 6);

      const fmtShort = (d) => d.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric'
      });

      weekLabel.textContent = `${fmtShort(start)} â€“ ${fmtShort(end)}`;

      header.appendChild(prevBtn);
      header.appendChild(weekLabel);
      header.appendChild(nextBtn);
      matrixContainer.appendChild(header);

      // caption
      const caption = document.createElement('div');
      caption.className = 'appt-matrix-caption';
      caption.textContent =
        'Tap a circled slot to choose your appointment date & time.';
      matrixContainer.appendChild(caption);

      const inner = document.createElement('div');
      inner.className = 'appt-matrix-inner';

      const table = document.createElement('table');
      table.className = 'appt-matrix-table';

      // build header row (days)
      const thead = document.createElement('thead');
      const headRow = document.createElement('tr');

      const cornerTh = document.createElement('th');
      cornerTh.className = 'appt-matrix-time';
      cornerTh.textContent = 'Time';
      headRow.appendChild(cornerTh);

      const days = [];
      for (let i = 0; i < 7; i++) {
        const d = new Date(start);
        d.setDate(start.getDate() + i);
        const iso = formatIsoLocalDate(d);
        const dowShort = d.toLocaleDateString(undefined, { weekday: 'short' });
        const dayNum = d.getDate();
        const open = isOpenDay(d);
        days.push({ date: d, iso, dowShort, dayNum, open });

        const th = document.createElement('th');
        th.innerHTML = `<div>${dowShort}</div><div>${dayNum}</div>`;
        if (!open) {
          th.classList.add('appt-matrix-closed-header');
        }
        headRow.appendChild(th);
      }

      thead.appendChild(headRow);
      table.appendChild(thead);

      const tbody = document.createElement('tbody');

      buildSlotLabels().forEach(label => {
        // Insert an "Afternoon" section header just before the 1:00 PM row
        if (label === '1:00 PM') {
          const sectionRow = document.createElement('tr');
          const sectionCell = document.createElement('th');
          sectionCell.colSpan = days.length + 1; // time column + all day columns
          sectionCell.className = 'appt-matrix-section';
          sectionCell.textContent = 'Afternoon';
          sectionRow.appendChild(sectionCell);
          tbody.appendChild(sectionRow);
        }

        const row = document.createElement('tr');
        const timeTh = document.createElement('th');
        timeTh.className = 'appt-matrix-time';
        // MOBILE MATRIX: show time without AM/PM for a cleaner look
        timeTh.textContent = displayTimeLabel(label);
        row.appendChild(timeTh);

        days.forEach(day => {
          const td = document.createElement('td');

          if (!day.open) {
            td.className = 'appt-matrix-closed';
            td.textContent = 'â€”';
            row.appendChild(td);
            return;
          }

          const btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'appt-matrix-cell-button';
          btn.dataset.date = day.iso;
          btn.dataset.time = label; // keep full label with AM/PM
          btn.setAttribute(
            'aria-label',
            `${displayTimeLabel(label)} on ${day.dowShort} ${day.dayNum}`
          );

          const dot = document.createElement('span');
          dot.className = 'dot';
          btn.appendChild(dot);

          if (day.iso === selectedDateIso && label === selectedTime) {
            btn.classList.add('is-selected');
            btn.setAttribute('aria-pressed', 'true');
          } else {
            btn.setAttribute('aria-pressed', 'false');
          }

          btn.addEventListener('click', () => {
            selectedDateIso = day.iso;
            selectedTime = label; // store full value
            dateInput.value = day.iso;
            timeField.value = label; // form submits full "9:00 AM" etc.
            renderMatrix();
          });

          td.appendChild(btn);
          row.appendChild(td);
        });

        tbody.appendChild(row);
      });

      table.appendChild(tbody);
      inner.appendChild(table);
      matrixContainer.appendChild(inner);
    };

    // Only render matrix on mobile / tablet widths
    if (window.matchMedia('(max-width: 991.98px)').matches) {
      renderMatrix();
    }
  }

  // ===========================
  // FORM VALIDATION
  // ===========================
  form.addEventListener('submit', (e) => {
    const anyService = !!form.querySelector('input[name="services"]:checked');
    if (!anyService) {
      e.preventDefault();
      openClientDialog({
        title: 'Select a Service',
        subtitle: 'Please choose at least one treatment before submitting your appointment request.',
        message: 'Choose one or more services from the list above, then try submitting again.',
      });
      return;
    }

    if (!dateInput.value) {
      e.preventDefault();
      openClientDialog({
        title: 'Pick a Date',
        subtitle: 'Your appointment request still needs a visit date.',
        message: 'Select a clinic date first, then choose a matching time slot before submitting.',
      });
      return;
    }

    if (!timeField.value) {
      e.preventDefault();
      openClientDialog({
        title: 'Pick a Time Slot',
        subtitle: 'Your appointment request still needs a time slot.',
        message: 'Choose one available time slot for your selected date, then submit your request again.',
      });
      return;
    }
  });
});
