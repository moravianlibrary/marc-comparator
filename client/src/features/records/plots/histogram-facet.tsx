import { Bar, BarChart, Rectangle, type RectangleProps, XAxis, YAxis } from 'recharts';

/** Bar `shape` render prop — recharts passes the bound datum along as `payload`. */
type ScoreBarProps = RectangleProps & { payload?: { min: number } };

import { type ChartConfig, ChartContainer, ChartTooltip } from '@/components/ui/chart';
import { EXCELLENT_MATCH, MATCH_SCALE_MAX, MODERATE_MATCH } from '../score';
import type { HistogramBucket } from '../types';
import { FacetTooltip } from './facet-tooltip';

interface HistogramFacetProps {
  data: HistogramBucket[];
  previewData?: HistogramBucket[];
}

const chartConfig = {
  preview: { label: 'Preview', color: 'var(--chart-1)' },
  remainder: { label: 'Remainder', color: 'var(--chart-1)' },
} satisfies ChartConfig;

/**
 * Bucket width, mirroring `SCORE_BUCKET` in `catalog_records/analytics.py`.
 *
 * The server buckets the score itself and this only re-bins what it sends, so
 * the two have to agree: a narrower width here would leave visible gaps, a
 * wider one would silently merge pairs of the server's buckets.
 */
const BUCKET_WIDTH = 0.5;
const BUCKET_COUNT = MATCH_SCALE_MAX / BUCKET_WIDTH;

function getScoreColor(min: number): string {
  if (min >= EXCELLENT_MATCH) {
    return 'var(--status-success)';
  }
  if (min >= MODERATE_MATCH) {
    return 'var(--status-warning)';
  }
  return 'var(--status-danger)';
}

/**
 * The server's buckets laid onto the full 0-15 scale, empties included.
 *
 * Only the occupied buckets come back, so without this the bars would close
 * up and a gap in the distribution would read as a score that does not exist.
 */
function normalizeBuckets(raw: HistogramBucket[]): HistogramBucket[] {
  const countByMin = new Map<number, number>();
  for (const b of raw) {
    // A perfect 15 is the top bucket's upper edge rather than a bucket of its
    // own, so it folds into the last one instead of falling off the end.
    const index = Math.min(Math.floor(b.min / BUCKET_WIDTH), BUCKET_COUNT - 1);
    const min = index * BUCKET_WIDTH;
    countByMin.set(min, (countByMin.get(min) ?? 0) + b.count);
  }

  const buckets: HistogramBucket[] = [];
  for (let i = 0; i < BUCKET_COUNT; i++) {
    // `BUCKET_WIDTH` is a power of two, so these are exact and safe as keys.
    const min = i * BUCKET_WIDTH;
    buckets.push({ min, max: min + BUCKET_WIDTH, count: countByMin.get(min) ?? 0 });
  }
  return buckets;
}

export function HistogramFacet({ data, previewData }: HistogramFacetProps) {
  const normalized = normalizeBuckets(data);
  const normalizedPreview = previewData ? normalizeBuckets(previewData) : null;
  const isShowingPreview = normalizedPreview != null;

  const chartData = normalized.map((bucket, index) => {
    const range = `${bucket.min.toFixed(1)}–${bucket.max.toFixed(1)}`;
    const pCount = normalizedPreview?.[index]?.count ?? 0;
    return {
      range,
      name: range,
      min: bucket.min,
      max: bucket.max,
      count: bucket.count,
      fill: getScoreColor(bucket.min),
      preview: isShowingPreview ? pCount : bucket.count,
      previewCount: isShowingPreview ? pCount : undefined,
      remainder: isShowingPreview ? bucket.count - pCount : 0,
    };
  });

  return (
    <ChartContainer config={chartConfig} className="w-full" style={{ height: 200 }}>
      <BarChart data={chartData} stackOffset="none">
        {/* Keyed on the range, which is unique — duplicate category values
            make recharts stack bars on top of each other. Thirty bars will
            not carry thirty readable labels either, so only the whole points
            are written and the half-steps sit unlabelled between them; the
            tooltip still names the exact range under the pointer. */}
        <XAxis
          dataKey="range"
          interval={0}
          tick={{ fontSize: 10 }}
          tickFormatter={(_range: string, index: number) =>
            Number.isInteger(index * BUCKET_WIDTH) ? (index * BUCKET_WIDTH).toFixed(0) : ''
          }
        />
        <YAxis hide />
        <ChartTooltip
          cursor={false}
          content={<FacetTooltip nameKey="range" countKey="count" previewKey="previewCount" />}
        />
        <Bar
          dataKey="preview"
          stackId="score"
          radius={isShowingPreview ? [0, 0, 0, 0] : [4, 4, 0, 0]}
          shape={(props: ScoreBarProps) => (
            <Rectangle {...props} fill={getScoreColor(props.payload!.min)} />
          )}
        />
        <Bar
          dataKey="remainder"
          stackId="score"
          radius={[4, 4, 0, 0]}
          shape={(props: ScoreBarProps) => (
            <Rectangle
              {...props}
              fill={getScoreColor(props.payload!.min)}
              opacity={isShowingPreview ? 0.3 : 1}
            />
          )}
        />
      </BarChart>
    </ChartContainer>
  );
}
