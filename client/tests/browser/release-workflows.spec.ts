import { expect, type Page, test } from '@playwright/test';

const TASK_ONE = '11111111-1111-4111-8111-111111111111';
const TASK_TWO = '22222222-2222-4222-8222-222222222222';

const me = {
  id: '33333333-3333-4333-8333-333333333333',
  email: 'cataloguer@example.test',
  first_name: 'Test',
  last_name: 'Cataloguer',
  roles: [],
  permissions: ['ReadRecords', 'ReviewRecords', 'ManageTasks', 'ManageAllTasks'],
};

const tasks = [TASK_ONE, TASK_TWO].map((task_id, index) => ({
  task_id,
  type: 'ProcessRecords',
  name: `Run ${index + 1}`,
  status: 'Success',
  severity: 'Info',
  progress: 1,
  created_by: me.id,
  created_at: '2026-10-16T10:00:00',
  started_at: '2026-10-16T10:00:00',
  finished_at: '2026-10-16T10:00:05',
}));

const record = {
  id: 'MZK01-000000001',
  base: 'MZK01',
  system_number: '000000001',
  title: 'Source title',
  authors: [],
  type_of_record: 'a',
  bibliographic_level: 'm',
  state: [],
  authority_links: [],
  link_attempts: [
    {
      base: 'SKC',
      rank: 0,
      outcome: 'BelowFloor',
      linker: 'marcxml-dump',
      authority_record_id: null,
      authority_base: 'SKC',
      authority_sysno: '000000002',
      confidence: 10,
      matched_by: 'identifier',
      matched_identifier: 'isbn',
      candidate_count: 1,
      detail: null,
    },
  ],
  claims: [] as Array<Record<string, unknown>>,
  comparisons: [],
  validations: [],
  latest_sync: null,
  latest_transaction: null,
  processed_at: '2026-10-16T10:00:00',
  processing_error: null,
};

const marc = {
  leader: '00000nam a2200000 a 4500',
  fixed_fields: { '001': '000000001' },
  variable_fields: {
    '245': [{ ind1: '1', ind2: '0', subfields: { a: ['Source title'] } }],
  },
};

async function mockApi(page: Page) {
  await page.route('**/api/**', async route => {
    const request = route.request();
    const path = new URL(request.url()).pathname.slice(4);
    const json = (body: unknown) => route.fulfill({ json: body });
    if (path === '/system/health') {
      return json({ status: 'ok' });
    }
    if (path === '/system/locks') {
      return json([]);
    }
    if (path === '/auth/me') {
      return json(me);
    }
    if (path === '/tasks/search-all' || path === '/tasks/search-own') {
      const body = request.postDataJSON() as {
        filters?: { task_id?: string[]; status?: string[] };
      };
      const items = body.filters?.status
        ? []
        : body.filters?.task_id
          ? tasks.filter(t => body.filters?.task_id?.includes(t.task_id))
          : tasks;
      return json({ items, total: items.length });
    }
    if (path.startsWith('/tasks/') && path.endsWith('/traceback')) {
      return json(`Log for ${path.split('/')[2]}\n${'long line '.repeat(150)}`);
    }
    if (path === '/reports') {
      return json([
        {
          id: 'report-1',
          task_id: TASK_ONE,
          tool: 'test',
          filename: 'report.txt',
          content_type: 'text/plain',
          size: 12,
          created_at: '2026-10-16T10:00:00',
        },
      ]);
    }
    if (path === '/reports/report-1/download') {
      return route.fulfill({
        body: 'test report\n',
        headers: {
          'content-type': 'text/plain',
          'content-disposition': 'attachment; filename="report.txt"',
        },
      });
    }
    if (path === '/access-control/users') {
      return json({ items: [me] });
    }
    if (path === '/catalog-records/search') {
      return json({ items: [record], total: 1, page: 1, page_size: 25 });
    }
    if (path === '/catalog-records/MZK01/000000001/marc') {
      return json(marc);
    }
    if (path === '/catalog-records/MZK01/000000001/comparisons') {
      return json([]);
    }
    if (path === '/catalog-records/MZK01/000000001/validations') {
      return json([]);
    }
    if (path === '/catalog-records/MZK01/000000001/reviews') {
      return json({ current: [], history: [] });
    }
    if (path === '/system/info') {
      return json({
        system_version: 'test',
        system_commit: 'test',
        uptime_seconds: 1,
        configured_bases: [],
        authority_bases: [],
        enabled_authority_linkers: [],
        enabled_validators: [],
        kramerius_client_urls: {},
      });
    }
    if (path === '/authority-linking/candidates/SKC/000000002/marc') {
      return json({
        ...marc,
        variable_fields: {
          '245': [{ ind1: '1', ind2: '0', subfields: { a: ['Candidate title'] } }],
        },
      });
    }
    if (path === '/authority-linking/candidates/SKC/000000002/comparison') {
      return json({
        overall_score: 11,
        quality: 'Moderate',
        scale: '0-15',
        summary: null,
        field_results: [
          {
            tag: '245',
            value_a: 'Source title',
            value_b: 'Candidate title',
            score: 11,
            explanation: null,
            details: null,
            subfield_results: null,
          },
        ],
      });
    }
    if (
      path === '/authority-linking/records/MZK01-000000001/claims' &&
      request.method() === 'POST'
    ) {
      const claim = request.postDataJSON() as Record<string, unknown>;
      record.claims = [{ ...claim, claimed_at: '2026-10-16T10:01:00', needs_review: false }];
      return json(record.claims[0]);
    }
    return json({});
  });
}

test.beforeEach(async ({ page }) => {
  record.claims = [];
  await mockApi(page);
});

test('task selection is a toggleable master/detail view with a downloadable report', async ({
  page,
}) => {
  await page.goto('/tasks');
  const first = page.locator(`[data-task-id="${TASK_ONE}"]`);
  await expect(first).toBeVisible();
  await first.click();
  await expect(page).toHaveURL(new RegExp(`taskId=${TASK_ONE}`));
  await expect(page.getByText(`Log for ${TASK_ONE}`)).toBeVisible();
  const download = page.waitForEvent('download');
  await page.getByRole('link', { name: /report.txt/ }).click();
  expect((await download).suggestedFilename()).toBe('report.txt');
  await page.locator(`[data-task-id="${TASK_TWO}"]`).click();
  await expect(page.getByText(`Log for ${TASK_TWO}`)).toBeVisible();
  await page.getByRole('button', { name: 'Zavřít podrobnosti' }).click();
  await expect(page).not.toHaveURL(/taskId=/);
  await expect(page.locator(`[data-task-id="${TASK_TWO}"]`)).toBeFocused();
  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`taskId=${TASK_TWO}`));
});

test('narrow task view uses its close control without page scrolling', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 700 });
  await page.goto('/tasks');
  await expect(page.locator(`[data-task-id="${TASK_ONE}"]`)).toBeVisible();
  expect(await page.evaluate(() => document.scrollingElement!.scrollHeight)).toBeLessThanOrEqual(
    700,
  );

  await page.locator(`[data-task-id="${TASK_ONE}"]`).click();
  await expect(page.locator(`[data-task-id="${TASK_ONE}"]`)).toBeHidden();
  await expect(page.getByRole('button', { name: 'Zpět na seznam úkolů' })).toHaveCount(0);
  expect(await page.evaluate(() => document.scrollingElement!.scrollHeight)).toBeLessThanOrEqual(
    700,
  );

  await page.getByRole('button', { name: 'Zavřít podrobnosti' }).click();
  await expect(page.locator(`[data-task-id="${TASK_ONE}"]`)).toBeVisible();
});

test('candidate comparison and claim use the retained candidate key', async ({ page }) => {
  await page.goto('/?tab=carousel&carouselView=cand%3ASKC%3A000000002');
  await expect(page.getByText('Porovnání se záznamem: 11.0 / 15')).toBeVisible();
  await expect(page.getByText('Candidate title')).toBeVisible();
  await page.getByRole('button', { name: 'Rozhodnout' }).click();
  const claimRequest = page.waitForRequest(
    r => r.url().endsWith('/claims') && r.method() === 'POST',
  );
  await page.getByRole('button', { name: 'Totéž dílo' }).click();
  expect((await claimRequest).postDataJSON()).toMatchObject({
    base: 'SKC',
    authority_base: 'SKC',
    authority_sysno: '000000002',
    verdict: 'SameWork',
  });
  await expect(page.getByRole('button', { name: 'Zrušit rozhodnutí' }).first()).toBeVisible();
});

test('a compared base is one badge and one card that open its comparison', async ({ page }) => {
  await page.goto('/?tab=carousel');
  const badge = page.getByText('SKC · nález pod prahem podle ISBN · 10.0 / 15');
  await expect(badge).toBeVisible();
  await expect(page.getByText('Nejlepší')).toBeVisible();

  await badge.click();

  await expect(page).toHaveURL(/carouselView=cand:SKC:000000002/);
  await expect(page.getByText('Porovnání se záznamem: 11.0 / 15')).toBeVisible();
});

test('the records page shows it is waiting for results', async ({ page }) => {
  let releaseSearch = () => {};
  const searchHeld = new Promise<void>(resolve => {
    releaseSearch = resolve;
  });
  await page.route('**/api/catalog-records/search', async route => {
    await searchHeld;
    await route.fulfill({ json: { items: [record], total: 1, page: 1, page_size: 25 } });
  });

  await page.goto('/?tab=table');
  const loading = page.getByRole('progressbar', { name: 'Načítání výsledků…' });
  await expect(loading).toBeVisible();

  releaseSearch();

  await expect(loading).toBeHidden();
});

test('moving to the next record keeps the compared base without rewriting the view', async ({
  page,
}) => {
  const linked = (n: number) => ({
    ...record,
    id: `MZK01-00000000${n}`,
    system_number: `00000000${n}`,
    title: `Title ${n}`,
    link_attempts: [
      {
        ...record.link_attempts[0],
        outcome: 'Linked',
        authority_record_id: `SKC-00000001${n}`,
        authority_sysno: `00000001${n}`,
      },
    ],
    comparisons: [
      {
        comparator: 'default',
        base: 'SKC',
        other_record_id: `SKC-00000001${n}`,
        overall_score: 14,
        match_quality: 'Excellent',
      },
    ],
  });
  await page.route('**/api/catalog-records/search', route =>
    route.fulfill({ json: { items: [linked(1), linked(2)], total: 2, page: 1, page_size: 25 } }),
  );
  await page.route(/\/api\/catalog-records\/MZK01\/\d+\/(comparisons|validations)$/, route =>
    route.fulfill({ json: [] }),
  );
  await page.route(/\/api\/catalog-records\/MZK01\/\d+\/marc$/, route =>
    route.fulfill({ json: marc }),
  );
  await page.route(/\/api\/catalog-records\/MZK01\/\d+\/reviews$/, route =>
    route.fulfill({ json: { current: [], history: [] } }),
  );
  await page.goto('/?tab=carousel&carouselView=comp%3Adefault%3ASKC-000000011');
  await expect(page.getByRole('combobox')).toContainText('SKC-000000011');

  await page.getByRole('button', { name: 'Další záznam' }).click();

  await expect(page.getByRole('heading', { name: 'MZK01-000000002' })).toBeVisible();
  await expect(page.getByRole('combobox')).toContainText('SKC-000000012'); // follows the base
  // URL writes are throttled; give a rewrite of the view the time it would take to land.
  await page.waitForTimeout(500);
  expect(new URL(page.url()).searchParams.get('carouselView')).toBe('comp:default:SKC-000000011');
});
