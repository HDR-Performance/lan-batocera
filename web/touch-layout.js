(() => {
  'use strict';

  const STORAGE_KEY = 'lanBatoceraTouchLayoutV1';
  const CONTROL_SELECTOR = [
    '.ejs_virtualGamepad_left',
    '.ejs_virtualGamepad_right',
    '.ejs_virtualGamepad_top',
    '.ejs_virtualGamepad_bottom'
  ].join(',');
  const MINIMUM_SCALE = 0.7;
  const MAXIMUM_SCALE = 1.5;
  const DEFAULT_SCALE = 1;

  function orientationKey() {
    return window.innerWidth >= window.innerHeight ? 'landscape' : 'portrait';
  }

  function readLayouts() {
    try {
      const storedLayouts = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
      return storedLayouts && typeof storedLayouts === 'object' ? storedLayouts : {};
    } catch {
      return {};
    }
  }

  function writeLayouts(layouts) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(layouts));
    } catch {
      // Layout persistence is optional when browser storage is unavailable.
    }
  }

  function controlKey(element, index) {
    const knownClass = [...element.classList].find(className => className.startsWith('ejs_virtualGamepad_'));
    return knownClass || `control-${index}`;
  }

  function clamp(value, minimum, maximum) {
    return Math.min(Math.max(value, minimum), maximum);
  }

  class TouchLayoutEditor {
    constructor(options) {
      this.gameElement = options.gameElement;
      this.toolbarElement = options.toolbarElement;
      this.scaleInput = options.scaleInput;
      this.statusElement = options.statusElement;
      this.selectedElement = null;
      this.activeDrag = null;
      this.editing = false;
      this.controls = [];
      this.boundPointerMove = event => this.handlePointerMove(event);
      this.boundPointerUp = event => this.handlePointerUp(event);
      this.observer = new MutationObserver(() => this.refreshControls());
      this.observer.observe(this.gameElement, { childList: true, subtree: true });
      window.addEventListener('resize', () => this.applySavedLayout());
    }

    refreshControls() {
      this.controls = [...this.gameElement.querySelectorAll(CONTROL_SELECTOR)].filter(element => {
        return !element.parentElement?.closest(CONTROL_SELECTOR);
      });
      this.controls.forEach((element, index) => {
        element.dataset.lanTouchControl = controlKey(element, index);
        element.onpointerdown = event => this.handlePointerDown(event, element);
      });
      this.applySavedLayout();
      this.updateEditingState();
    }

    currentLayout() {
      const layouts = readLayouts();
      const orientation = orientationKey();
      layouts[orientation] ||= {};
      return { layouts, orientation, layout: layouts[orientation] };
    }

    applySavedLayout() {
      const { layout } = this.currentLayout();
      this.controls.forEach(element => {
        const savedControl = layout[element.dataset.lanTouchControl] || {};
        element.style.setProperty('--lan-touch-x', `${Number(savedControl.x) || 0}px`);
        element.style.setProperty('--lan-touch-y', `${Number(savedControl.y) || 0}px`);
        element.style.setProperty('--lan-touch-scale', String(Number(savedControl.scale) || DEFAULT_SCALE));
      });
    }

    saveElement(element, nextValues) {
      const { layouts, orientation, layout } = this.currentLayout();
      const key = element.dataset.lanTouchControl;
      layout[key] = { ...layout[key], ...nextValues };
      layouts[orientation] = layout;
      writeLayouts(layouts);
      this.applySavedLayout();
    }

    start() {
      this.editing = true;
      this.toolbarElement.hidden = false;
      document.body.classList.add('touch-layout-editing');
      this.refreshControls();
      this.statusElement.textContent = this.controls.length
        ? 'Tap a control group, then drag it. Use the slider to resize the selected group.'
        : 'Waiting for the touch controls to load…';
    }

    finish() {
      this.editing = false;
      this.activeDrag = null;
      this.selectedElement = null;
      this.toolbarElement.hidden = true;
      document.body.classList.remove('touch-layout-editing');
      this.updateEditingState();
    }

    reset() {
      const layouts = readLayouts();
      delete layouts[orientationKey()];
      writeLayouts(layouts);
      this.applySavedLayout();
      this.statusElement.textContent = 'Touch layout reset for this screen orientation.';
    }

    select(element) {
      this.selectedElement = element;
      const { layout } = this.currentLayout();
      const savedControl = layout[element.dataset.lanTouchControl] || {};
      this.scaleInput.value = String(Number(savedControl.scale) || DEFAULT_SCALE);
      this.statusElement.textContent = `Selected ${element.dataset.lanTouchControl.replace('ejs_virtualGamepad_', '')} controls.`;
      this.updateEditingState();
    }

    updateEditingState() {
      this.controls.forEach(element => {
        element.classList.toggle('lan-touch-editable', this.editing);
        element.classList.toggle('lan-touch-selected', this.editing && element === this.selectedElement);
      });
    }

    handlePointerDown(event, element) {
      if (!this.editing) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      this.select(element);
      const { layout } = this.currentLayout();
      const savedControl = layout[element.dataset.lanTouchControl] || {};
      this.activeDrag = {
        element,
        pointerId: event.pointerId,
        startX: event.clientX,
        startY: event.clientY,
        originalX: Number(savedControl.x) || 0,
        originalY: Number(savedControl.y) || 0
      };
      element.setPointerCapture?.(event.pointerId);
      window.addEventListener('pointermove', this.boundPointerMove, { capture: true, passive: false });
      window.addEventListener('pointerup', this.boundPointerUp, { capture: true, passive: false });
      window.addEventListener('pointercancel', this.boundPointerUp, { capture: true, passive: false });
    }

    handlePointerMove(event) {
      if (!this.activeDrag || event.pointerId !== this.activeDrag.pointerId) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      const maximumX = window.innerWidth * 0.45;
      const maximumY = window.innerHeight * 0.45;
      const x = clamp(this.activeDrag.originalX + event.clientX - this.activeDrag.startX, -maximumX, maximumX);
      const y = clamp(this.activeDrag.originalY + event.clientY - this.activeDrag.startY, -maximumY, maximumY);
      this.saveElement(this.activeDrag.element, { x: Math.round(x), y: Math.round(y) });
    }

    handlePointerUp(event) {
      if (!this.activeDrag || event.pointerId !== this.activeDrag.pointerId) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      this.activeDrag.element.releasePointerCapture?.(event.pointerId);
      this.activeDrag = null;
      window.removeEventListener('pointermove', this.boundPointerMove, true);
      window.removeEventListener('pointerup', this.boundPointerUp, true);
      window.removeEventListener('pointercancel', this.boundPointerUp, true);
    }

    setSelectedScale(value) {
      if (!this.selectedElement) {
        this.statusElement.textContent = 'Tap a control group before changing its size.';
        return;
      }
      const scale = clamp(Number(value) || DEFAULT_SCALE, MINIMUM_SCALE, MAXIMUM_SCALE);
      this.saveElement(this.selectedElement, { scale });
    }
  }

  function bind(options) {
    const editor = new TouchLayoutEditor(options);
    options.openButton.addEventListener('click', () => {
      options.beforeOpen?.();
      editor.start();
    });
    options.doneButton.addEventListener('click', () => editor.finish());
    options.resetButton.addEventListener('click', () => editor.reset());
    options.scaleInput.addEventListener('input', event => editor.setSelectedScale(event.target.value));
    editor.refreshControls();
    return editor;
  }

  window.LanTouchLayout = Object.freeze({ bind });
})();
