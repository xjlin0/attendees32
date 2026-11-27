// Prevent Permissions policy violation: unload is not allowed in this document.
// Chrome deprecates 'unload' and triggers violations when addEventListener('unload') is invoked.
// Redirect 'unload' to 'pagehide' (the modern W3C standard recommended by Chromium).
if (typeof window !== 'undefined' && window.addEventListener) {
  const origAddEventListener = window.addEventListener;
  window.addEventListener = function (type: string, listener: any, options?: any) {
    if (type === 'unload') {
      return origAddEventListener.call(window, 'pagehide', listener, options);
    }
    return origAddEventListener.apply(this, arguments as any);
  };

  const origRemoveEventListener = window.removeEventListener;
  window.removeEventListener = function (type: string, listener: any, options?: any) {
    if (type === 'unload') {
      return origRemoveEventListener.call(window, 'pagehide', listener, options);
    }
    return origRemoveEventListener.apply(this, arguments as any);
  };
}

import '../shared/base';
import '../shared/utilities';
import 'devextreme/dist/css/dx.light.compact.css';
import './style.css';
import * as Vue from 'vue';

// DevExtreme UI Widgets
import dxDataGrid from 'devextreme/ui/data_grid';
import dxForm from 'devextreme/ui/form';
import dxPopup from 'devextreme/ui/popup';
import dxSelectBox from 'devextreme/ui/select_box';
import dxTabPanel from 'devextreme/ui/tab_panel';
import dxDateBox from 'devextreme/ui/date_box';
import dxTextArea from 'devextreme/ui/text_area';
import dxTagBox from 'devextreme/ui/tag_box';
import dxCheckBox from 'devextreme/ui/check_box';
import dxTextBox from 'devextreme/ui/text_box';
import dxButton from 'devextreme/ui/button';
import dxDropDownBox from 'devextreme/ui/drop_down_box';
import dxNumberBox from 'devextreme/ui/number_box';
import dxRadioGroup from 'devextreme/ui/radio_group';
import dxScrollView from 'devextreme/ui/scroll_view';
import dxToolbar from 'devextreme/ui/toolbar';
import dxLoadIndicator from 'devextreme/ui/load_indicator';
import dxLoadPanel from 'devextreme/ui/load_panel';

import notify from 'devextreme/ui/notify';
import { confirm, alert } from 'devextreme/ui/dialog';
import CustomStore from 'devextreme/data/custom_store';
import DataSource from 'devextreme/data/data_source';
import { exportDataGrid } from 'devextreme/excel_exporter';

// Native Vue 3 components from devextreme-vue
import { DxDataGrid, DxColumn } from 'devextreme-vue/data-grid';
import { DxForm, DxItem, DxGroupItem } from 'devextreme-vue/form';
import { DxPopup } from 'devextreme-vue/popup';
import { DxSelectBox } from 'devextreme-vue/select-box';
import { DxTabPanel } from 'devextreme-vue/tab-panel';
import { DxDateBox } from 'devextreme-vue/date-box';
import { DxButton } from 'devextreme-vue/button';

import App from './App.vue';

// Assemble DevExpress shim object
const DevExpress = {
  ui: {
    dxDataGrid,
    dxForm,
    dxPopup,
    dxSelectBox,
    dxTabPanel,
    dxDateBox,
    dxTextArea,
    dxTagBox,
    dxCheckBox,
    dxTextBox,
    dxButton,
    dxDropDownBox,
    dxNumberBox,
    dxRadioGroup,
    dxScrollView,
    dxToolbar,
    dxLoadIndicator,
    dxLoadPanel,
    notify,
    dialog: { confirm, alert },
  },
  data: {
    CustomStore,
    DataSource,
  },
  excelExporter: {
    exportDataGrid,
  },
};

// Expose Vue and DevExpress globally for transition compatibility
if (typeof window !== 'undefined') {
  (window as any).Vue = Vue;
  (window as any).DevExpress = DevExpress;
}

let appInstance: any = null;

export function initRostersApp(selector = '#app') {
  if (appInstance) return appInstance;
  const mountEl = document.querySelector(selector);
  if (mountEl) {
    appInstance = Vue.createApp(App);
    appInstance.mount(mountEl);
    return appInstance;
  }
  return null;
}

if (typeof window !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      initRostersApp('#app');
    });
  } else {
    initRostersApp('#app');
  }
}

export {
  Vue,
  DevExpress,
  App,
  DxDataGrid,
  DxColumn,
  DxForm,
  DxItem,
  DxGroupItem,
  DxPopup,
  DxSelectBox,
  DxTabPanel,
  DxDateBox,
  DxButton,
};
