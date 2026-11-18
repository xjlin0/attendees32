import { Ref } from 'vue';
import { FilterState } from '../types';
import { gatheringsRegistry, meetsMap } from './useLookups';

const SYNC_POLLING_INTERVAL = 15000;
const FIFTEEN_MINUTES_MS = 15 * 60 * 1000;

export function useSmartPolling(gridInstanceRef: Ref<any>, filterData: FilterState) {
  let pollingTimer: any = null;

  const isAnyGatheringActiveNow = () => {
    const now = Date.now();

    // Short-circuit if date filter does not cover current time
    if (filterData.startDate) {
      const startMs = new Date(filterData.startDate).getTime();
      if (!isNaN(startMs) && now < startMs - FIFTEEN_MINUTES_MS) {
        return false;
      }
    }
    if (filterData.endDate) {
      const endMs = new Date(filterData.endDate).getTime();
      if (!isNaN(endMs) && now > endMs + FIFTEEN_MINUTES_MS) {
        return false;
      }
    }

    const selectedMeetIds = new Set(
      (filterData.meets || []).map((slug) => {
        const m = meetsMap.get(slug) || meetsMap.get(String(slug));
        return m ? String(m.id) : null;
      }).filter(Boolean),
    );

    for (const g of gatheringsRegistry.values()) {
      if (!g || !g.start) continue;
      if (selectedMeetIds.size > 0 && g.meet_id && !selectedMeetIds.has(String(g.meet_id))) {
        continue;
      }
      const gStart = new Date(g.start).getTime();
      if (isNaN(gStart)) continue;
      let gFinish = g.finish ? new Date(g.finish).getTime() : NaN;
      if (isNaN(gFinish)) {
        gFinish = gStart + 2 * 60 * 60 * 1000;
      }
      const windowStart = gStart - FIFTEEN_MINUTES_MS;
      const windowEnd = gFinish + FIFTEEN_MINUTES_MS;
      if (now >= windowStart && now <= windowEnd) {
        return true;
      }
    }
    return false;
  };

  const poll = async () => {
    if (document.hidden) return;
    if ((window as any).Attendees?.utilities?.editingEnabled) return;
    if (!filterData.meets || filterData.meets.length === 0) return;
    if (!gridInstanceRef.value) return;
    if (!isAnyGatheringActiveNow()) return;

    try {
      await gridInstanceRef.value.refresh();
    } catch (e) {
      console.warn('Smart polling refresh skipped or failed:', e);
    }
  };

  const startPolling = () => {
    if (pollingTimer) clearInterval(pollingTimer);
    pollingTimer = setInterval(poll, SYNC_POLLING_INTERVAL);
  };

  const stopPolling = () => {
    if (pollingTimer) {
      clearInterval(pollingTimer);
      pollingTimer = null;
    }
  };

  return {
    startPolling,
    stopPolling,
    poll,
  };
}
