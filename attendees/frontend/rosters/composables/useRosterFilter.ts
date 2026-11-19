import { Ref } from 'vue';
import { Endpoints, FilterState } from '../types';
import { meetsMap, meetsInfoMap, gatheringsRegistry } from './useLookups';
import dxForm from 'devextreme/ui/form';
import notify from 'devextreme/ui/notify';
import CustomStore from 'devextreme/data/custom_store';
import DataSource from 'devextreme/data/data_source';

const MAX_DATE_RANGE_YEARS = 5;

const isValidDate = (date: any): boolean => {
  if (!date) return false;
  const d = new Date(date);
  return !isNaN(d.getTime());
};

const addMonths = (date: any, months: number): Date | null => {
  if (!date) return null;
  const d = new Date(date);
  if (isNaN(d.getTime())) return null;
  const currentDay = d.getDate();
  d.setMonth(d.getMonth() + months);
  if (d.getDate() !== currentDay) {
    d.setDate(0); // If day overflowed, set to last day of target month
  }
  return d;
};

export function useRosterFilter(
  endpoints: Endpoints,
  filterData: FilterState,
  reloadCallback: () => void,
  gridInstanceRef: Ref<any>,
  clearLastNewcomer?: () => void,
  getLastNewcomer?: () => any
) {
  let formInstance: any = null;
  const storageOptsKey = (window as any).Attendees?.utilities?.datagridStorageKeys?.['rostersListViewOpts'];

  const checkHasKidMeet = (selectedSlugs?: string[]): boolean => {
    const slugs = selectedSlugs || filterData.meets || [];
    return slugs.some(slug => {
      const m = meetsMap.get(slug) || meetsMap.get(String(slug));
      const showInfos = m?.show_attendee_infos || (m?.infos && m.infos.show_attendee_infos) || {};
      return Boolean(showInfos['infos-grade'] || showInfos['grade']);
    });
  };

  const resetFilters = () => {
    const defaultStart = new Date(new Date().setDate(new Date().getDate() - 5));
    const defaultEnd = new Date(new Date().setMonth(new Date().getMonth() + 1));
    filterData.meets = [];
    filterData.startDate = defaultStart;
    filterData.endDate = defaultEnd;
    filterData.showPhotos = false;
    filterData.showSiblings = true;

    if (typeof clearLastNewcomer === 'function') {
      clearLastNewcomer();
    }

    if (formInstance) {
      const startEd = formInstance.getEditor('startDate');
      const endEd = formInstance.getEditor('endDate');
      if (startEd) {
        startEd.option({ value: defaultStart, isValid: true, validationError: null });
      }
      if (endEd) {
        endEd.option({ value: defaultEnd, isValid: true, validationError: null });
      }
      formInstance.getEditor('showPhotos')?.option('value', false);
      const sibEditor = formInstance.getEditor('showSiblings');
      if (sibEditor) sibEditor.option('value', true);
      formInstance.itemOption('showSiblings', 'visible', false);
      formInstance.itemOption('meets', 'colSpan', 12);
      formInstance.getEditor('meets')?.option('value', []);
    }
    gatheringsRegistry.clear();
    if ((window as any).Attendees?.utilities?.accessItemFromSessionStorage && storageOptsKey) {
      try {
        const storedObject = JSON.parse(window.sessionStorage.getItem(storageOptsKey) || '{}');
        delete storedObject['userGradeVisible'];
        window.sessionStorage.setItem(storageOptsKey, JSON.stringify(storedObject));
      } catch (e) {}
    }

    if (gridInstanceRef.value) {
      if (typeof gridInstanceRef.value.columnOption === 'function') {
        gridInstanceRef.value.columnOption('grade', 'visible', false);
      }
      gridInstanceRef.value.clearGrouping();
      gridInstanceRef.value.clearSorting();
      gridInstanceRef.value.option('dataSource', []);
    }
  };

  /**
   * Formats recurring schedule rules for selected meets into descriptive help text.
   * Displays schedule details only when a single meet is selected; returns empty string otherwise.
   */
  const formatMeetSchedulesHelpText = (selectedMeets: string[]): string => {
    if (!selectedMeets || selectedMeets.length !== 1) {
      return '';
    }

    const meetSlug = selectedMeets[0];
    const meet = meetsMap.get(meetSlug);
    if (!meet) {
      return '';
    }

    const timeRules = meet.schedule_rules || [];
    const noRuleText = 'This meet does not have schedules in EventRelation';
    if (!timeRules || timeRules.length === 0) {
      return noRuleText;
    }

    const newHelpTexts: string[] = [];
    const meetStart = meet.start ? new Date(meet.start).toDateString() : '';
    const meetFinish = meet.finish ? new Date(meet.finish).toDateString() : '';

    timeRules.forEach((timeRule: any) => {
      if (timeRule && timeRule.rule) {
        const toLocaleStringOpts = (window as any).Attendees?.utilities?.timeRules?.[timeRule.rule] || {
          weekday: 'long',
          hour: 'numeric',
          minute: 'numeric',
        };
        const startTime = new Date(timeRule.start);
        const endTime = new Date(timeRule.end);
        const startTimeText = !isNaN(startTime.getTime())
          ? startTime.toLocaleString(navigator.language, toLocaleStringOpts)
          : '';
        const endTimeText = !isNaN(endTime.getTime())
          ? endTime.toLocaleString(navigator.language, toLocaleStringOpts)
          : '';
        const locationText = timeRule.location ? `@${timeRule.location}` : '';
        newHelpTexts.push(`${timeRule.rule} ${startTimeText} ~ ${endTimeText}${locationText}`);
      } else {
        newHelpTexts.push(noRuleText);
      }
    });

    if (newHelpTexts.length === 0) {
      return noRuleText;
    }

    const rangeText = (meetStart && meetFinish) ? ` from ${meetStart} to ${meetFinish}` : '';
    return newHelpTexts.join(', ') + rangeText;
  };

  /**
   * Updates help text on the meets filter item to show schedule information.
   */
  const updateMeetsHelpText = (selectedMeets: string[]) => {
    if (!formInstance) return;
    const text = formatMeetSchedulesHelpText(selectedMeets);
    try {
      formInstance.itemOption('meets', 'helpText', text);
    } catch (e) {
      // Ignore if itemOption is not supported on instance
    }
    const helpEl = formInstance.element()?.querySelector('.filter-item-meets .dx-field-item-help-text');
    if (helpEl) {
      helpEl.textContent = text;
    }
  };

  const initFilterForm = (filterFormEl: HTMLElement) => {
    formInstance = new (dxForm as any)(filterFormEl, {
      formData: filterData,
      colCount: 24,
      colCountByScreen: {
        xs: 1,
        sm: 2,
        md: 4,
        lg: 24
      },
      onFieldDataChanged: (e: any) => {
        filterData[e.dataField as keyof FilterState] = e.value;
        
        // Date Validation & saving to sessionStorage
        if (e.dataField === 'startDate' || e.dataField === 'endDate') {
          const startEd = formInstance.getEditor('startDate');
          const endEd = formInstance.getEditor('endDate');
          const startVal = startEd ? startEd.option('value') : filterData.startDate;
          const endVal = endEd ? endEd.option('value') : filterData.endDate;

          if (e.dataField === 'startDate' && (window as any).Attendees?.utilities?.accessItemFromSessionStorage) {
            (window as any).Attendees.utilities.accessItemFromSessionStorage(storageOptsKey, 'filterFromString', isValidDate(e.value) ? new Date(e.value).toJSON() : null);
          }
          if (e.dataField === 'endDate' && (window as any).Attendees?.utilities?.accessItemFromSessionStorage) {
            (window as any).Attendees.utilities.accessItemFromSessionStorage(storageOptsKey, 'filterTillString', isValidDate(e.value) ? new Date(e.value).toJSON() : null);
          }

          if (isValidDate(startVal) && isValidDate(endVal)) {
            const startMs = new Date(startVal).getTime();
            const endMs = new Date(endVal).getTime();
            const diffMs = endMs - startMs;
            const FIVE_YEARS_MS = MAX_DATE_RANGE_YEARS * 365.25 * 24 * 60 * 60 * 1000;

            if (diffMs < 0) {
              const errMsg = 'From date cannot be after To date';
              startEd?.option({ isValid: false, validationError: { message: errMsg } });
              endEd?.option({ isValid: false, validationError: { message: errMsg } });
              notify({ message: errMsg, type: 'warning', displayTime: 4000 });
              return;
            } else if (diffMs > FIVE_YEARS_MS) {
              const yearsDiff = (diffMs / (365.25 * 24 * 60 * 60 * 1000)).toFixed(1);
              const errMsg = `Date range cannot exceed 5 years (selected: ${yearsDiff} years)`;
              startEd?.option({ isValid: false, validationError: { message: errMsg } });
              endEd?.option({ isValid: false, validationError: { message: errMsg } });
              notify({ message: errMsg, type: 'warning', displayTime: 4500 });
              return;
            } else {
              if (startEd && startEd.option('isValid') === false) {
                startEd.option({ isValid: true, validationError: null });
              }
              if (endEd && endEd.option('isValid') === false) {
                endEd.option({ isValid: true, validationError: null });
              }
            }
          } else {
            if (!isValidDate(startVal)) {
              startEd?.option({ isValid: false, validationError: { message: 'From date is required' } });
            } else if (startEd && startEd.option('isValid') === false) {
              startEd.option({ isValid: true, validationError: null });
            }
            if (!isValidDate(endVal)) {
              endEd?.option({ isValid: false, validationError: { message: 'To date is required' } });
            } else if (endEd && endEd.option('isValid') === false) {
              endEd.option({ isValid: true, validationError: null });
            }
          }
        }

        if (e.dataField === 'meets') {
          const selectedMeets = e.value || [];
          if (typeof clearLastNewcomer === 'function') {
            if (selectedMeets.length === 0) {
              clearLastNewcomer();
            } else if (typeof getLastNewcomer === 'function') {
              const currentNewcomer = getLastNewcomer();
              if (currentNewcomer && currentNewcomer.meetSlug && !selectedMeets.includes(currentNewcomer.meetSlug)) {
                clearLastNewcomer();
              }
            }
          }
          if ((window as any).Attendees?.utilities?.accessItemFromSessionStorage) {
            (window as any).Attendees.utilities.accessItemFromSessionStorage(storageOptsKey, 'selectedMeetSlugs', selectedMeets);
          }
          const shouldShow = checkHasKidMeet(selectedMeets);
          if (formInstance) {
            const currentItem = formInstance.itemOption('showSiblings');
            if (currentItem && currentItem.visible !== shouldShow) {
              formInstance.itemOption('showSiblings', 'visible', shouldShow);
              formInstance.itemOption('meets', 'colSpan', shouldShow ? 10 : 12);
            }
            updateMeetsHelpText(selectedMeets);
          }
          if (gridInstanceRef.value && typeof gridInstanceRef.value.columnOption === 'function') {
            gridInstanceRef.value.columnOption('grade', 'visible', shouldShow);
          }
        }

        if (e.dataField === 'showPhotos' && (window as any).Attendees?.utilities?.accessItemFromSessionStorage) {
          (window as any).Attendees.utilities.accessItemFromSessionStorage(storageOptsKey, 'showPhotos', !!e.value);
        }
        if (e.dataField === 'showSiblings' && (window as any).Attendees?.utilities?.accessItemFromSessionStorage) {
          (window as any).Attendees.utilities.accessItemFromSessionStorage(storageOptsKey, 'showSiblings', !!e.value);
        }

        if (['meets', 'startDate', 'endDate'].includes(e.dataField)) {
          reloadCallback();
        } else if (['showPhotos', 'showSiblings'].includes(e.dataField) && gridInstanceRef.value) {
          gridInstanceRef.value.repaint();
        }
      },
      items: [
        {
          dataField: 'startDate',
          editorType: 'dxDateBox',
          colSpan: 5,
          label: { text: 'From' },
          editorOptions: { 
            type: 'datetime', 
            displayFormat: 'shortDateShortTime',
            showClearButton: true
          }
        },
        {
          dataField: 'endDate',
          editorType: 'dxDateBox',
          colSpan: 5,
          label: { text: 'To' },
          editorOptions: { 
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
                    class: 'btn-extend-range-month'
                  },
                  onClick: () => {
                    const endEd = formInstance.getEditor('endDate');
                    const startEd = formInstance.getEditor('startDate');
                    const startVal = (startEd && startEd.option('value')) || filterData.startDate;
                    const currentEnd = (endEd && endEd.option('value')) || filterData.endDate;
                    const baseDate = (isValidDate(currentEnd) ? new Date(currentEnd) : (isValidDate(startVal) ? new Date(startVal) : new Date()));
                    const newEnd = isValidDate(currentEnd) ? addMonths(currentEnd, 1) : addMonths(baseDate, 1);

                    if (startVal && newEnd) {
                      const startMs = new Date(startVal).getTime();
                      const endMs = newEnd.getTime();
                      const diffMs = endMs - startMs;
                      const FIVE_YEARS_MS = MAX_DATE_RANGE_YEARS * 365.25 * 24 * 60 * 60 * 1000;
                      if (diffMs > FIVE_YEARS_MS) {
                        const yearsDiff = (diffMs / (365.25 * 24 * 60 * 60 * 1000)).toFixed(1);
                        const errMsg = `Date range cannot exceed 5 years (selected: ${yearsDiff} years)`;
                        notify({ message: errMsg, type: 'warning', displayTime: 4500 });
                        return;
                      }
                    }

                    if (endEd) {
                      endEd.option('value', newEnd);
                    } else if (newEnd) {
                      filterData.endDate = newEnd;
                      formInstance.updateData('endDate', newEnd);
                    }
                  }
                }
              }
            ]
          }
        },
        {
          dataField: 'meets',
          editorType: 'dxTagBox',
          colSpan: checkHasKidMeet(filterData.meets) ? 10 : 12,
          cssClass: 'filter-item-meets',
          label: { text: 'Meets' },
          helpText: '',
          editorOptions: {
            searchEnabled: true,
            searchExpr: ['display_name', 'slug'],
            searchMode: 'contains',
            minSearchLength: 0,
            grouped: true,
            displayExpr: 'display_name',
            valueExpr: 'slug',
            placeholder: 'Select Meets...',
            showClearButton: true,
            dataSource: new DataSource({
              store: new CustomStore({
                key: 'slug',
                byKey: (key: string) => {
                  return meetsMap.get(key) || { slug: key, display_name: meetsInfoMap.get(key) || key };
                },
                load: async () => {
                  const queryParams = new URLSearchParams({
                    take: '9999',
                    grouping: 'assembly_name',
                    model: 'attendance'
                  });
                  
                  if (isValidDate(filterData.startDate)) queryParams.set('start', new Date(filterData.startDate).toISOString());
                  if (isValidDate(filterData.endDate)) queryParams.set('finish', new Date(filterData.endDate).toISOString());

                  const response = await fetch(`${endpoints.meets}?${queryParams.toString()}`);
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

                  if (formInstance) {
                    const shouldShow = checkHasKidMeet(filterData.meets);
                    const currentItem = formInstance.itemOption('showSiblings');
                    if (currentItem && currentItem.visible !== shouldShow) {
                      formInstance.itemOption('showSiblings', 'visible', shouldShow);
                      formInstance.itemOption('meets', 'colSpan', shouldShow ? 10 : 12);
                    }
                    updateMeetsHelpText(filterData.meets || []);
                  }

                  return rawData;
                }
              })
            })
          }
        },
        {
          dataField: 'showPhotos',
          name: 'showPhotos',
          editorType: 'dxCheckBox',
          colSpan: 2,
          cssClass: 'filter-item-checkbox',
          label: { text: 'Photo' }
        },
        {
          dataField: 'showSiblings',
          name: 'showSiblings',
          editorType: 'dxCheckBox',
          colSpan: 2,
          cssClass: 'filter-item-checkbox',
          label: { text: 'Siblings' },
          visible: checkHasKidMeet(filterData.meets)
        }
      ]
    });

    updateMeetsHelpText(filterData.meets || []);
  };

  return { initFilterForm, resetFilters };
}
