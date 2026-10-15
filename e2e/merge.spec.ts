import { expect, test, visit, waitForGridRows } from './fixtures';
import { attendeeId } from './golden';

/**
 * Merging two records of one person: the picker and the merge screen on the
 * person's page, the notice with Undo, the merged-away link that opens the
 * merged record, and the button on the enrollment grid. The twin is made
 * through the API and removed at the end.
 */
const ORIGINAL = 'chen_joshua';
const API = '/persons/api/datagrid_data_attendee/';
const TWIN_BIRTHDAY = '2011-02-03';
const TWIN_PHONE = '+15105550199';
const YOUTH_GROUP_MEET_ID = 100; // GOLDEN_MEET_IDS['youth_group'] in the golden builder
const DAUGHTER = 4; // Relations.DAUGHTER in the golden vocabulary

async function csrfToken(page) {
  const cookie = (await page.context().cookies()).find((c) => c.name === 'csrftoken');
  if (!cookie) throw new Error('no csrftoken cookie after signing in');
  return cookie.value;
}

async function call(page, method: string, path: string, body?: unknown, headers: Record<string, string> = {}) {
  return page.request.fetch(path, {
    method,
    headers: { 'X-CSRFToken': await csrfToken(page), 'Content-Type': 'application/json', ...headers },
    data: body === undefined ? undefined : JSON.stringify(body),
  });
}

async function makeTwin(page, original, fields: Record<string, unknown> = {}, headers: Record<string, string> = {}) {
  const response = await call(page, 'POST', API, {
    first_name: original.first_name,
    last_name: original.last_name,
    first_name2: original.first_name2,
    last_name2: original.last_name2,
    gender: original.gender,
    division: original.division,
    actual_birthday: TWIN_BIRTHDAY,
    infos: { names: {}, fixed: {}, contacts: { phone1: TWIN_PHONE } },
    ...fields,
  }, { 'X-Target-Attendee-Id': 'new', ...headers });
  expect(response.ok(), await response.text()).toBeTruthy();
  return response.json();
}

async function remove(page, id: string) {
  await call(page, 'DELETE', `${API}${id}/`, undefined, { 'X-Target-Attendee-Id': id });
}

/** The enrollment grid, filtered to the youth group's students and searched for a name. */
async function youthGroupRows(page, search: string) {
  await visit(page, '/persons/attendingmeets/');
  await page.waitForSelector('form.filters-dxform .dx-tagbox');
  await page.evaluate(async () => {
    const boxes = (window as any).$('form.filters-dxform .dx-tagbox');
    const meets = boxes.eq(0).dxTagBox('instance');
    const characters = boxes.eq(1).dxTagBox('instance');
    const items = async (box) => {
      const source = box.getDataSource();
      await source.load();
      return source.items().flatMap((group) => group.items || [group]);
    };
    const meet = (await items(meets)).find((m) => /Youth Group/.test(m.display_name));
    meets.option('value', [meet.slug]);
    await new Promise((resolve) => setTimeout(resolve, 1500));
    const character = (await items(characters)).find((c) => /Youth Student/.test(c.display_name));
    characters.option('value', [character[characters.option('valueExpr')]]);
  });
  await waitForGridRows(page, '#attendingmeets-datagrid-container');
  await page.evaluate((text) => (window as any).$('#attendingmeets-datagrid-container').dxDataGrid('instance').searchByText(text), search);
  await page.waitForTimeout(2500);
}

async function record(page, id: string) {
  const response = await call(page, 'GET', `${API}${id}/`);
  return { status: response.status(), body: response.ok() ? await response.json() : null };
}

test.describe('Merging two records', () => {
  test('from the person page: pick, decide, merge, follow the old link, undo', async ({ page, signIn }) => {
    await signIn('golden_data_organizer');
    const original = (await record(page, attendeeId(ORIGINAL))).body;
    const twin = await makeTwin(page, original);
    try {
      await visit(page, `/persons/attendee/${twin.id}`);
      await expect(page.locator('h3.page-title')).toContainText('Details of');

      // The picker, searched by the full name; the twin itself is left out.
      await page.click('button.attendee-merge-button');
      await expect(page.getByText('Which record is the same person as')).toBeVisible();
      await page.locator('.dx-popup-content input.dx-texteditor-input').fill(original.infos.names.original);
      const match = page.locator('.dx-popup-content .dx-list-item', { hasText: original.infos.names.original });
      await expect(match).toHaveCount(1);
      await match.click();

      // The merge screen: the birthdays differ, the newer record's is picked.
      await expect(page.getByText('Merge into one record')).toBeVisible();
      await expect(page.getByText('Contacts from both')).toBeVisible();
      await page.locator('input[type="radio"][name="actual_birthday"][value="duplicate"]').check();
      await page.locator('.dx-popup-bottom .dx-button', { hasText: 'Merge' }).first().click();

      // One record now, with the pick applied and the twin's phone kept.
      await page.waitForURL(new RegExp(`/persons/attendee/${original.id}`));
      await expect(page.locator('.attendee-merge-notices')).toContainText(`Merged with ${twin.infos.names.original}`);
      const merged = (await record(page, original.id)).body;
      expect(merged.actual_birthday).toBe(TWIN_BIRTHDAY);
      expect(Object.values(merged.infos.contacts)).toContain(TWIN_PHONE);
      expect((await record(page, twin.id)).status).toBe(410);

      // The twin's link opens the merged record and says so.
      await visit(page, `/persons/attendee/${twin.id}`);
      await expect(page).toHaveURL(new RegExp(`/persons/attendee/${original.id}\\?merged_from=${twin.id}`));
      await expect(page.locator('.attendee-merge-notices')).toContainText('You followed a link to a record that was merged into this one.');

      // Undo, once: both records come back, the pick included.
      await page.click('button.attendee-unmerge-button');
      await expect(page.getByText('Undo this merge?')).toBeVisible();
      await page.locator('.dx-popup-bottom .dx-button', { hasText: 'Undo merge' }).click();
      await page.waitForURL(/success=/);
      await expect(page.locator('.attendee-merge-notices .alert')).toHaveCount(0);
      const restored = (await record(page, original.id)).body;
      expect(restored.actual_birthday).toBe(original.actual_birthday);
      expect(restored.infos.contacts).toEqual(original.infos.contacts);
      expect((await record(page, twin.id)).status).toBe(200);
    } finally {
      await call(page, 'DELETE', `${API}${twin.id}/`, undefined, { 'X-Target-Attendee-Id': twin.id });
    }
  });

  test('the enrollment grid offers Merge 2 selected only when two people are ticked', async ({ page, signIn }) => {
    await signIn('golden_data_organizer');
    await youthGroupRows(page, '');
    const button = page.locator('#attendingmeets-datagrid-container .dx-button', { hasText: 'Merge 2 selected' });
    await expect(button).toBeHidden();

    const selected = await page.evaluate(() => {
      const grid = (window as any).$('#attendingmeets-datagrid-container').dxDataGrid('instance');
      const keys: unknown[] = [];
      const people = new Set();
      for (const row of grid.getVisibleRows()) {
        if (row.rowType !== 'data' || people.has(row.data.attendee_id)) continue;
        people.add(row.data.attendee_id);
        keys.push(row.key);
        if (keys.length === 2) break;
      }
      grid.selectRows(keys, false);
      return keys.length;
    });
    expect(selected).toBe(2);
    await expect(button).toBeVisible();

    await page.evaluate(() => (window as any).$('#attendingmeets-datagrid-container').dxDataGrid('instance').clearSelection());
    await expect(button).toBeHidden();
  });

  test('three records of one person: a merge from the grid, a merge from the page, one undo', async ({ page, signIn }) => {
    test.setTimeout(180_000);
    await signIn('golden_data_organizer');
    const original = (await record(page, attendeeId('liu_hannah'))).body;

    // Two newer records of Hannah, both in the youth group. The first comes
    // with a family of its own and contacts of three kinds; the second shares
    // one of Hannah's numbers.
    const second = await makeTwin(page, original, {
      actual_birthday: '2010-05-06',
      infos: { names: {}, fixed: { grade: 9, food_pref: 'no nuts' }, contacts: { phone1: '+15105550231', email1: 'hannah.second@example.org', WeChat1: 'hannah_second' } },
    }, { 'X-Join-Meet': String(YOUTH_GROUP_MEET_ID), 'X-Add-Folk': 'new', 'X-Folk-Role': String(DAUGHTER) });
    const third = await makeTwin(page, original, {
      actual_birthday: '2010-05-07',
      infos: { names: {}, fixed: { medical: 'asthma inhaler' }, contacts: { phone1: '+15105550232', phone2: original.infos.contacts.phone1 } },
    }, { 'X-Join-Meet': String(YOUTH_GROUP_MEET_ID) });
    const ids = [original.id, second.id, third.id];
    try {
      // 1. From the grid: Hannah and the second record, ticked together.
      await youthGroupRows(page, 'Hannah Liu');
      const selected = await page.evaluate(([one, two]) => {
        const grid = (window as any).$('#attendingmeets-datagrid-container').dxDataGrid('instance');
        const keys = grid.getVisibleRows().filter((row) => row.rowType === 'data' && [one, two].includes(row.data.attendee_id)).map((row) => row.key);
        grid.selectRows(keys, false);
        return keys.length;
      }, [original.id, second.id]);
      expect(selected).toBe(2);
      await page.locator('#attendingmeets-datagrid-container .dx-button', { hasText: 'Merge 2 selected' }).click();
      await expect(page.getByText('Merge into one record')).toBeVisible();
      // Birthday and grade differ; the newer record's birthday is taken, the rest stays.
      await expect(page.locator('input[type="radio"][name="fixed.grade"]')).toHaveCount(2);
      await page.locator('input[type="radio"][name="actual_birthday"][value="duplicate"]').check();
      await expect(page.locator('.dx-popup-content', { hasText: 'Contacts from both' })).toContainText('hannah_second');
      await page.locator('.dx-popup-bottom .dx-button', { hasText: 'Merge' }).first().click();
      // The merge, then the pick as an edit; the grid shows a toast once both are done.
      await expect(page.locator('.dx-toast-message', { hasText: 'Merged into one record' })).toBeVisible();
      expect((await record(page, second.id)).status).toBe(410);
      let merged = (await record(page, original.id)).body;
      expect(merged.actual_birthday).toBe('2010-05-06');
      expect(merged.infos.fixed.grade).toBe(original.infos.fixed.grade);
      expect(merged.infos.fixed.food_pref).toBe('no nuts');
      expect(Object.values(merged.infos.contacts)).toEqual(expect.arrayContaining(['+15105550231', 'hannah.second@example.org', 'hannah_second']));
      // Every membership moves: the second record's new family and its own "other" folk.
      expect(merged.folkattendee_set.length).toBe(original.folkattendee_set.length + 2);

      // 2. From the page: the third record, through the picker.
      await visit(page, `/persons/attendee/${original.id}`);
      await expect(page.locator('.attendee-merge-notices .alert')).toHaveCount(1);
      await expect(page.locator('h3.page-title')).toContainText('Details of');
      await page.click('button.attendee-merge-button');
      await page.locator('.dx-popup-content input.dx-texteditor-input').fill(original.infos.names.original);
      // The merged-away second record is gone from the matches; only the third is offered.
      await expect(page.locator('.dx-popup-content .dx-list-item')).toHaveCount(1);
      await page.locator('.dx-popup-content .dx-list-item').click();
      await expect(page.getByText('Merge into one record')).toBeVisible();
      await page.locator('.dx-popup-bottom .dx-button', { hasText: 'Merge' }).first().click();
      await page.waitForURL(/success=/);
      await expect(page.locator('.attendee-merge-notices .alert')).toHaveCount(2);
      merged = (await record(page, original.id)).body;
      expect(merged.infos.fixed.medical).toBe('asthma inhaler');
      const phones = Object.entries(merged.infos.contacts).filter(([key]) => key.startsWith('phone')).map(([, value]) => value);
      expect(phones).toEqual([original.infos.contacts.phone1, '+15105550231', '+15105550232']);
      expect((await record(page, third.id)).status).toBe(410);

      // 3. Undo the third record's merge only: it comes back, the second stays merged.
      await page.locator(`button.attendee-unmerge-button[data-duplicate-id="${third.id}"]`).click();
      await page.locator('.dx-popup-bottom .dx-button', { hasText: 'Undo merge' }).click();
      await page.waitForURL(/success=/);
      await expect(page.locator('.attendee-merge-notices .alert')).toHaveCount(1);
      await expect(page.locator(`button.attendee-unmerge-button[data-duplicate-id="${second.id}"]`)).toBeVisible();
      expect((await record(page, third.id)).status).toBe(200);
      expect((await record(page, second.id)).status).toBe(410);
      merged = (await record(page, original.id)).body;
      expect(merged.infos.fixed.medical).toBeUndefined();
      expect(Object.values(merged.infos.contacts)).not.toContain('+15105550232');
      expect(merged.actual_birthday).toBe('2010-05-06');
      expect(merged.infos.fixed.food_pref).toBe('no nuts');
    } finally {
      // Hannah as she was: undo the second record's merge too, then remove both twins.
      await call(page, 'POST', `${API}${second.id}/unmerge/`);
      for (const id of ids.slice(1)) await remove(page, id);
    }
    const restored = (await record(page, original.id)).body;
    expect(restored.actual_birthday).toBe(original.actual_birthday);
    expect(restored.infos.contacts).toEqual(original.infos.contacts);
    expect(restored.infos.fixed).toEqual(original.infos.fixed);
    expect(restored.folkattendee_set.length).toBe(original.folkattendee_set.length);
  });
});
