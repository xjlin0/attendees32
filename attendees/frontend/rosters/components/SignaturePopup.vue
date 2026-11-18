<template>
  <DxPopup
    v-model:visible="visible"
    :max-width="400"
    width="95%"
    :height="200"
    :title="title"
    :show-title="true"
    :drag-enabled="false"
    :hide-on-outside-click="false"
    :show-close-button="false"
    @shown="handleShown"
    @hiding="handleHiding"
  >
    <div style="width: 100%; height: 100px;">
      <canvas ref="canvasRef" class="signature" style="width: 100%; height: 100px;"></canvas>
    </div>
    <DxToolbarItem
      widget="dxButton"
      toolbar="bottom"
      location="before"
      :options="signButtonOptions"
    />
    <DxToolbarItem
      widget="dxButton"
      toolbar="bottom"
      location="after"
      :options="clearButtonOptions"
    />
    <DxToolbarItem
      widget="dxButton"
      toolbar="bottom"
      location="after"
      :options="cancelButtonOptions"
    />
  </DxPopup>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue';
import { DxPopup, DxToolbarItem } from 'devextreme-vue/popup';
import notify from 'devextreme/ui/notify';
import SignaturePad from 'signature_pad';

const visible = ref(false);
const title = ref('Sign here');
const canvasRef = ref<HTMLCanvasElement | null>(null);
let padInstance: SignaturePad | null = null;
let currentOnSign: ((encodedFile: string) => Promise<void>) | null = null;

const initCanvas = () => {
  const canvas = canvasRef.value;
  if (!canvas) return;
  const width = canvas.offsetWidth || 378;
  const height = canvas.offsetHeight || 100;
  canvas.width = width;
  canvas.height = height;

  if (padInstance) {
    try { padInstance.off(); } catch (e) {}
  }
  padInstance = new SignaturePad(canvas, {
    maxWidth: 2,
    backgroundColor: 'rgb(255,255,255)',
  });
  padInstance.clear();
};

const handleShown = () => {
  if ((window as any).Attendees?.utilities) {
    (window as any).Attendees.utilities.editingEnabled = true;
  }
  nextTick(() => {
    initCanvas();
  });
};

const handleHiding = () => {
  if ((window as any).Attendees?.utilities) {
    (window as any).Attendees.utilities.editingEnabled = false;
  }
};

const signButtonOptions = computed(() => ({
  icon: 'edit',
  text: 'Sign',
  type: 'default',
  onClick: async () => {
    if (padInstance && !padInstance.isEmpty()) {
      const encodedFile = padInstance.toDataURL('image/jpeg', 0.5);
      visible.value = false;
      const cb = currentOnSign;
      currentOnSign = null;
      if (cb) {
        await cb(encodedFile);
      }
      padInstance.clear();
    } else {
      notify({
        message: 'Signing requires signature!',
        position: { my: 'center', at: 'center', of: window },
      }, 'error', 5000);
    }
  },
}));

const clearButtonOptions = computed(() => ({
  icon: 'clear',
  text: 'Clear signing',
  stylingMode: 'outlined',
  onClick: () => {
    if (padInstance) padInstance.clear();
  },
}));

const cancelButtonOptions = computed(() => ({
  text: 'Cancel',
  stylingMode: 'text',
  onClick: () => {
    visible.value = false;
    if (padInstance) padInstance.clear();
    currentOnSign = null;
  },
}));

const open = (opts: { title?: string; onSign: (encodedFile: string) => Promise<void> }) => {
  title.value = opts.title || 'Sign here';
  currentOnSign = opts.onSign;
  visible.value = true;
};

defineExpose({ open });
</script>
