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

async function makeTwin(page, original) {
  const response = await call(page, 'POST', API, {
    first_name: original.first_name,
    last_name: original.last_name,
    first_name2: original.first_name2,
    last_name2: original.last_name2,
    gender: original.gender,
    division: original.division,
    actual_birthday: TWIN_BIRTHDAY,
    infos: { names: {}, fixed: {}, contacts: { phone1: TWIN_PHONE } },
  }, { 'X-Target-Attendee-Id': 'new' });
  expect(response.ok(), await response.text()).toBeTruthy();
  return response.json();
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
    await visit(page, '/persons/attendingmeets/');
    // The grid lists the chosen meets; pick the youth group and its students, as a coworker would.
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
});
