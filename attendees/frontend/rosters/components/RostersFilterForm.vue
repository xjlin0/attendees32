<template>
  <div class="rosters-filter-form-wrapper">
    <DxForm
      ref="formRef"
      :form-data="formData"
      :col-count="24"
      :col-count-by-screen="{ xs: 1, sm: 2, md: 4, lg: 24 }"
      @field-data-changed="onFieldDataChanged"
    >
      <DxItem
        data-field="startDate"
        editor-type="dxDateBox"
        :col-span="5"
        :label="{ text: 'From' }"
        :editor-options="startDateEditorOptions"
      />
      <DxItem
        data-field="endDate"
        editor-type="dxDateBox"
        :col-span="5"
        :label="{ text: 'To' }"
        :editor-options="endDateEditorOptions"
      />
      <DxItem
        data-field="meets"
        editor-type="dxTagBox"
        :col-span="hasKidMeet ? 10 : 12"
        css-class="filter-item-meets"
        :label="{ text: 'Meets' }"
        :editor-options="meetsEditorOptions"
      />
      <DxItem
        data-field="showPhotos"
        name="showPhotos"
        editor-type="dxCheckBox"
        :col-span="2"
        css-class="filter-item-checkbox"
        :label="{ text: 'Photo' }"
      />
      <DxItem
        data-field="showSiblings"
        name="showSiblings"
        editor-type="dxCheckBox"
        :col-span="2"
        css-class="filter-item-checkbox"
        :label="{ text: 'Siblings' }"
        :visible="hasKidMeet"
      />
    </DxForm>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { DxForm, DxItem } from 'devextreme-vue/form';
import DataSource from 'devextreme/data/data_source';
import CustomStore from 'devextreme/data/custom_store';
import notify from 'devextreme/ui/notify';
import { Endpoints, FilterState } from '../types';
import { meetsMap, meetsInfoMap } from '../composables/useLookups';

const props = defineProps<{
  endpoints: Endpoints;
  formData: FilterState;
}>();

const emit = defineEmits<{
  (e: 'filter-changed', field: string, value: any): void;
  (e: 'reload'): void;
  (e: 'repaint'): void;
}>();

const formRef = ref<any>(null);
const MAX_DATE_RANGE_YEARS = 5;

const isValidDate = (d: any) => d && !isNaN(new Date(d).getTime());

const addMonths = (date: Date | string, months: number) => {
  if (!date) return null;
  const d = new Date(date);
  if (isNaN(d.getTime())) return null;
  const currentDay = d.getDate();
  d.setMonth(d.getMonth() + months);
  if (d.getDate() !== currentDay) {
    d.setDate(0);
  }
  return d;
};

const checkHasKidMeet = (selectedSlugs?: string[]) => {
  const slugs = selectedSlugs || [];
  return slugs.some((slug) => {
    const m = meetsMap.get(slug) || meetsMap.get(String(slug));
    const showInfos = m?.show_attendee_infos || (m?.infos && m.infos.show_attendee_infos) || {};
    return Boolean(showInfos['infos-grade'] || showInfos['grade']);
  });
};

const hasKidMeet = computed(() => checkHasKidMeet(props.formData.meets));

const startDateEditorOptions = {
  type: 'datetime',
  displayFormat: 'shortDateShortTime',
  showClearButton: true,
};

const endDateEditorOptions = {
  type: 'datetime',
  displayFormat: 'shortDateShortTime',
  showClearButton: true,
  buttons: [
    'clear',
    'dropDown',
    {
      name: 'fastForwardMonth',
      location: 'after',
      options: {
        icon: 'fas fa-forward',
        stylingMode: 'text',
        hint: 'extend range by 1 month',
        elementAttr: {
          title: 'extend range by 1 month',
          'aria-label': 'extend range by 1 month',
          class: 'btn-extend-range-month',
        },
        onClick: () => {
          const form = formRef.value?.instance;
          const endEd = form?.getEditor('endDate');
          const startVal = props.formData.startDate;
          const currentEnd = (endEd && endEd.option('value')) || props.formData.endDate;
          const baseDate = isValidDate(currentEnd) ? new Date(currentEnd!) : (isValidDate(startVal) ? new Date(startVal!) : new Date());
          const newEnd = isValidDate(currentEnd) ? addMonths(currentEnd!, 1) : addMonths(baseDate, 1);

          if (startVal && newEnd) {
            const startMs = new Date(startVal).getTime();
            const endMs = newEnd.getTime();
            const diffMs = endMs - startMs;
            const FIVE_YEARS_MS = MAX_DATE_RANGE_YEARS * 365.25 * 24 * 60 * 60 * 1000;
            if (diffMs > FIVE_YEARS_MS) {
              const yearsDiff = (diffMs / (365.25 * 24 * 60 * 60 * 1000)).toFixed(1);
              notify(`Date range cannot exceed 5 years (selected: ${yearsDiff} years)`, 'warning', 4500);
              return;
            }
          }

          if (endEd) {
            endEd.option('value', newEnd);
          } else {
            props.formData.endDate = newEnd;
            emit('filter-changed', 'endDate', newEnd);
          }
        },
      },
    },
  ],
};

const meetsDataSource = new DataSource({
  store: new CustomStore({
    key: 'slug',
    byKey: (key: string) => ({
      slug: key,
      display_name: meetsInfoMap.get(key) || key,
    }),
    load: async () => {
      const queryParams = new URLSearchParams({
        take: '9999',
        grouping: 'assembly_name',
        model: 'attendance',
      });
      if (isValidDate(props.formData.startDate)) {
        queryParams.set('start', new Date(props.formData.startDate!).toISOString());
      }
      if (isValidDate(props.formData.endDate)) {
        queryParams.set('finish', new Date(props.formData.endDate!).toISOString());
      }

      const response = await fetch(`${props.endpoints.meetsBySlug || props.endpoints.meets}?${queryParams.toString()}`);
      if (!response.ok) throw new Error('Failed to load meets');
      const json = await response.json();
      const rawData = json.data || json.results || json;
      const items = Array.isArray(rawData) ? rawData : [];

      items.forEach((groupOrMeet: any) => {
        if (groupOrMeet.items && Array.isArray(groupOrMeet.items)) {
          groupOrMeet.items.forEach((m: any) => {
            if (m.id !== undefined) {
              meetsInfoMap.set(m.id, m.display_name);
              meetsInfoMap.set(String(m.id), m.display_name);
              meetsMap.set(m.id, m);
              meetsMap.set(String(m.id), m);
            }
            if (m.slug) {
              meetsInfoMap.set(m.slug, m.display_name);
              meetsMap.set(m.slug, m);
            }
          });
        } else {
          if (groupOrMeet.id !== undefined) {
            meetsInfoMap.set(groupOrMeet.id, groupOrMeet.display_name);
            meetsInfoMap.set(String(groupOrMeet.id), groupOrMeet.display_name);
            meetsMap.set(groupOrMeet.id, groupOrMeet);
            meetsMap.set(String(groupOrMeet.id), groupOrMeet);
          }
          if (groupOrMeet.slug) {
            meetsInfoMap.set(groupOrMeet.slug, groupOrMeet.display_name);
            meetsMap.set(groupOrMeet.slug, groupOrMeet);
          }
        }
      });
      return rawData;
    },
  }),
});

const meetsEditorOptions = {
  grouped: true,
  displayExpr: 'display_name',
  valueExpr: 'slug',
  placeholder: 'Select Meets...',
  showClearButton: true,
  dataSource: meetsDataSource,
};

const onFieldDataChanged = (e: any) => {
  props.formData[e.dataField as keyof FilterState] = e.value;
  emit('filter-changed', e.dataField, e.value);

  if (['meets', 'startDate', 'endDate'].includes(e.dataField)) {
    emit('reload');
  } else if (['showPhotos', 'showSiblings'].includes(e.dataField)) {
    emit('repaint');
  }
};

defineExpose({
  getInstance: () => formRef.value?.instance,
  reloadMeets: () => meetsDataSource.reload(),
});
</script>
