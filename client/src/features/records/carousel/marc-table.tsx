import { cn } from "@/lib/utils";
import { useTranslation } from "react-i18next";
import type {
  MarcRecordData,
  FieldComparisonResult,
  SubfieldComparisonResult,
  ValidationResult,
} from "../types";

export type AnnotationType = "comparison" | "validation";

const VALIDATION_STATUS_ORDER: Record<string, number> = {
  Valid: 0,
  ForReview: 1,
  Invalid: 2,
  AdditionalInfo: 3,
};

function sortByStatus(results: ValidationResult[]): ValidationResult[] {
  return [...results].sort(
    (a, b) =>
      (VALIDATION_STATUS_ORDER[a.status] ?? 99) -
      (VALIDATION_STATUS_ORDER[b.status] ?? 99),
  );
}

interface MarcTableProps {
  marc: MarcRecordData;
  annotationType?: AnnotationType;
  comparisonAnnotations?: FieldComparisonResult[];
  validationAnnotations?: ValidationResult[];
  targetTags?: Set<string>;
  krameriusClientUrl?: string;
}

export function MarcTable({
  marc,
  annotationType,
  comparisonAnnotations,
  validationAnnotations,
  targetTags,
  krameriusClientUrl,
}: MarcTableProps) {
  const fixedEntries = Object.entries(marc.fixed_fields)
    .sort(([a], [b]) => parseInt(a) - parseInt(b))
    .filter(([tag]) => !targetTags || targetTags.has(tag));

  // Build variable entries and inject synthetic rows for missing validation tags
  const existingTags = new Set([
    ...Object.keys(marc.fixed_fields),
    ...Object.keys(marc.variable_fields),
  ]);
  const missingValidationTags: string[] = [];
  if (annotationType === "validation" && validationAnnotations) {
    for (const va of validationAnnotations) {
      const tag = va.target.tag;
      if (!existingTags.has(tag) && !missingValidationTags.includes(tag)) {
        missingValidationTags.push(tag);
      }
    }
  }

  const variableEntries: [string, { ind1: string | null; ind2: string | null; subfields: Record<string, string[]> }[]][] = [
    ...Object.entries(marc.variable_fields),
    ...missingValidationTags.map((tag) => [tag, [{ ind1: null, ind2: null, subfields: {} }]] as [string, { ind1: string | null; ind2: string | null; subfields: Record<string, string[]> }[]]),
  ]
    .sort(([a], [b]) => parseInt(a) - parseInt(b))
    .filter(([tag]) => !targetTags || targetTags.has(tag));

  const showAnnotations = !!annotationType;
  const showLeader = !targetTags;
  let rowIndex = 0;

  return (
    <div className="rounded-md border overflow-hidden">
      {/* Leader */}
      {showLeader && (
        <MarcRow
          tag="LDR"
          ind1={null}
          ind2={null}
          subfields={{ _: [marc.leader] }}
          striped={false}
          showAnnotationColumn={showAnnotations}
        />
      )}

      {/* Fixed fields */}
      {fixedEntries.map(([tag, value]) => {
        rowIndex++;
        const compAnnotation = annotationType === "comparison"
          ? comparisonAnnotations?.find((a) => a.tag === tag)
          : undefined;
        const valAnnotationsForField = annotationType === "validation"
          ? validationAnnotations?.filter((v) =>
              v.target.tag === tag,
            )
          : undefined;
        return (
          <MarcRow
            key={`ff-${tag}`}
            tag={tag}
            ind1={null}
            ind2={null}
            subfields={{ _: [value] }}
            striped={rowIndex % 2 === 0}
            showAnnotationColumn={showAnnotations}
            comparisonAnnotation={compAnnotation}
            validationAnnotations={valAnnotationsForField}
            krameriusClientUrl={krameriusClientUrl}
          />
        );
      })}

      {/* Variable fields */}
      {variableEntries.flatMap(([tag, fields]) => {
        const isMissingTag = !existingTags.has(tag);
        const rows = fields.map((field, fieldIdx) => {
          rowIndex++;
          const compAnnotation = annotationType === "comparison"
            ? comparisonAnnotations?.find((a) => a.tag === tag)
            : undefined;
          const valAnnotationsForField = annotationType === "validation"
            ? validationAnnotations?.filter((v) =>
                v.target.tag === tag &&
                (v.target.field_index === fieldIdx || (isMissingTag && v.target.field_index == null)),
              )
            : undefined;
          return (
            <MarcRow
              key={`vf-${tag}-${fieldIdx}`}
              tag={tag}
              ind1={field.ind1}
              ind2={field.ind2}
              subfields={field.subfields}
              striped={rowIndex % 2 === 0}
              showAnnotationColumn={showAnnotations}
              comparisonAnnotation={compAnnotation}
              validationAnnotations={valAnnotationsForField}
              krameriusClientUrl={krameriusClientUrl}
            />
          );
        });

        // Add a synthetic empty row for non-indexed validation results on existing tags
        if (annotationType === "validation" && !isMissingTag) {
          const nonIndexed = validationAnnotations?.filter(
            (v) => v.target.tag === tag && v.target.field_index == null,
          );
          if (nonIndexed && nonIndexed.length > 0) {
            rowIndex++;
            rows.push(
              <MarcRow
                key={`vf-${tag}-general`}
                tag={tag}
                ind1={null}
                ind2={null}
                subfields={{}}
                striped={rowIndex % 2 === 0}
                showAnnotationColumn={showAnnotations}
                validationAnnotations={nonIndexed}
                krameriusClientUrl={krameriusClientUrl}
              />,
            );
          }
        }

        return rows;
      })}
    </div>
  );
}

interface MarcRowProps {
  tag: string;
  ind1: string | null;
  ind2: string | null;
  subfields: Record<string, string[]>;
  striped: boolean;
  showAnnotationColumn: boolean;
  comparisonAnnotation?: FieldComparisonResult;
  validationAnnotations?: ValidationResult[];
  krameriusClientUrl?: string;
}

function MarcRow({
  tag,
  ind1,
  ind2,
  subfields,
  striped,
  showAnnotationColumn,
  comparisonAnnotation,
  validationAnnotations,
  krameriusClientUrl,
}: MarcRowProps) {
  const i1 = ind1 ?? "-";
  const i2 = ind2 ?? "-";

  // Build subfield rows for rendering
  const subfieldRows: { code: string; value: string }[] = [];
  for (const [code, values] of Object.entries(subfields)) {
    for (const value of values) {
      subfieldRows.push({ code, value });
    }
  }

  // Build a map of subfield code -> annotation for comparison subfield alignment
  const subfieldAnnotationMap = new Map<string, SubfieldComparisonResult>();
  if (comparisonAnnotation?.subfield_results) {
    for (const sr of comparisonAnnotation.subfield_results) {
      subfieldAnnotationMap.set(sr.code, sr);
    }
  }

  const hasSubfieldAnnotations = subfieldAnnotationMap.size > 0;

  // Comparison with subfield annotations: render each subfield as a full-width row
  // so that source value, authority value, and score stay aligned per row
  if (showAnnotationColumn && comparisonAnnotation && hasSubfieldAnnotations) {
    return (
      <div className={cn("border-b last:border-b-0", striped && "bg-muted/50")}>
        {subfieldRows.map((sf, i) => {
          const srAnnotation = subfieldAnnotationMap.get(sf.code);
          return (
            <div key={i} className="flex">
              {/* Tag + indicators (first row only) */}
              <div className="flex w-[120px] flex-none items-start gap-4 px-3 py-0.5">
                {i === 0 && (
                  <>
                    <span className="font-mono text-sm font-medium">{tag}</span>
                    <span className="font-mono text-sm text-muted-foreground">
                      {i1}{i2}
                    </span>
                  </>
                )}
              </div>
              {/* Source subfield */}
              <div className="w-[35%] flex-none px-3 py-0.5">
                <div className="flex gap-3">
                  <span className="w-[20px] flex-none font-mono text-sm text-muted-foreground">
                    {sf.code === "_" ? "" : sf.code}
                  </span>
                  <span className="text-sm">{sf.value}</span>
                </div>
              </div>
              {/* Authority subfield */}
              <div className="w-[35%] flex-none border-l px-3 py-0.5">
                {srAnnotation ? (
                  <div className="flex gap-3 text-sm">
                    <span className="w-[20px] flex-none font-mono text-muted-foreground">
                      {srAnnotation.code}
                    </span>
                    <span>{srAnnotation.value_b ?? ""}</span>
                  </div>
                ) : (
                  <div className="text-sm">&nbsp;</div>
                )}
              </div>
              {/* Score + explanation */}
              <div className="flex-1 px-3 py-0.5">
                {srAnnotation ? (
                  <div className="flex items-center gap-2 text-sm">
                    <ScoreBadge score={srAnnotation.score} />
                    {srAnnotation.explanation && (
                      <ExplanationLabel explanation={srAnnotation.explanation} />
                    )}
                  </div>
                ) : (
                  <div className="text-sm">&nbsp;</div>
                )}
              </div>
            </div>
          );
        })}
        {/* Field-level annotation */}
        <div className="flex">
          <div className="w-[120px] flex-none" />
          <div className="w-[35%] flex-none" />
          <div className="w-[35%] flex-none" />
          <div className="flex-1 px-3 py-0.5">
            <ComparisonFieldAnnotation annotation={comparisonAnnotation} />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("border-b last:border-b-0", striped && "bg-muted/50")}>
      <div className="flex">
        {/* Tag + indicators */}
        <div className="flex w-[120px] flex-none items-start gap-4 px-3 py-1.5">
          <span className="font-mono text-sm font-medium">{tag}</span>
          <span className="font-mono text-sm text-muted-foreground">
            {i1}
            {i2}
          </span>
        </div>

        {/* Subfields */}
        <div className={cn("px-3 py-1.5", showAnnotationColumn ? "w-[35%] flex-none" : "flex-1")}>
          {subfieldRows.map((sf, i) => (
            <div key={i} className="flex gap-3">
              <span className="w-[20px] flex-none font-mono text-sm text-muted-foreground">
                {sf.code === "_" ? "" : sf.code}
              </span>
              <span className="text-sm">{sf.value}</span>
            </div>
          ))}
        </div>

        {/* Annotation columns */}
        {showAnnotationColumn && comparisonAnnotation && !hasSubfieldAnnotations && (
          <>
            <div className="w-[35%] flex-none border-l px-3 py-1.5">
              {comparisonAnnotation.value_b != null && (
                <div className="text-sm">{comparisonAnnotation.value_b}</div>
              )}
            </div>
            <div className="flex-1 px-3 py-1.5">
              <ComparisonFieldAnnotation annotation={comparisonAnnotation} />
            </div>
          </>
        )}
        {showAnnotationColumn && !comparisonAnnotation && validationAnnotations && validationAnnotations.length > 0 && (
          <div className="flex-1 border-l px-3 py-1.5 space-y-2">
            {sortByStatus(validationAnnotations).map((va, i) => (
              <ValidationFieldAnnotation key={i} annotation={va} krameriusClientUrl={krameriusClientUrl} />
            ))}
          </div>
        )}
        {showAnnotationColumn && !comparisonAnnotation && (!validationAnnotations || validationAnnotations.length === 0) && (
          <div className="flex-1 border-l px-3 py-1.5" />
        )}
      </div>
    </div>
  );
}

function ExplanationLabel({ explanation }: { explanation: string }) {
  const { t } = useTranslation("records");
  return (
    <span className="text-xs text-muted-foreground truncate">
      {t(`field-explanation.${explanation}`, { defaultValue: explanation })}
    </span>
  );
}

function ComparisonFieldAnnotation({ annotation }: { annotation: FieldComparisonResult }) {
  const { t } = useTranslation("records");
  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground">
      <span>{t("carousel.field-score")}:</span>
      <ScoreBadge score={annotation.score} />
      {annotation.explanation && (
        <ExplanationLabel explanation={annotation.explanation} />
      )}
    </div>
  );
}

const PID_REGEX = /uuid:[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}/g;

function extractDetailsParams(text: string): Record<string, string> {
  const params: Record<string, string> = {};
  const pidMatch = text.match(PID_REGEX);
  if (pidMatch) params.pid = pidMatch[0];
  const modelMatch = text.match(/model '([^']+)'/);
  if (modelMatch) params.model = modelMatch[1];
  const levelMatch = text.match(/level (\d+)/);
  if (levelMatch) params.level = levelMatch[1];
  const valueMatch = text.match(/Value '([^']+)'/);
  if (valueMatch) params.value = valueMatch[1];
  const patternMatch = text.match(/pattern: (.+)$/);
  if (patternMatch) params.pattern = patternMatch[1];
  return params;
}

function renderDetailsWithPidLinks(text: string, krameriusClientUrl?: string) {
  if (!krameriusClientUrl) return text;
  const parts: (string | JSX.Element)[] = [];
  let lastIndex = 0;
  for (const match of text.matchAll(PID_REGEX)) {
    const pid = match[0];
    const idx = match.index!;
    if (idx > lastIndex) parts.push(text.slice(lastIndex, idx));
    const url = krameriusClientUrl.replace("{pid}", pid);
    parts.push(
      <a key={idx} href={url} target="_blank" rel="noopener noreferrer" className="underline hover:text-foreground">
        {pid}
      </a>,
    );
    lastIndex = idx + pid.length;
  }
  if (lastIndex < text.length) parts.push(text.slice(lastIndex));
  return parts;
}

function ValidationFieldAnnotation({ annotation, krameriusClientUrl }: { annotation: ValidationResult; krameriusClientUrl?: string }) {
  const { t } = useTranslation("records");
  return (
    <div className="space-y-0.5">
      <span
        className={cn(
          "text-xs font-medium",
          annotation.status === "Valid" && "text-green-600 dark:text-green-400",
          annotation.status === "Invalid" && "text-red-600 dark:text-red-400",
          annotation.status === "ForReview" && "text-yellow-600 dark:text-yellow-400",
          annotation.status === "AdditionalInfo" && "text-blue-600 dark:text-blue-400",
        )}
      >
        {t(`validity-status.${annotation.status}`, { defaultValue: annotation.status })}
        {annotation.reason && (
          <> - {t(`validation-reason.${annotation.reason}`, { defaultValue: annotation.reason })}</>
        )}
      </span>
      {annotation.details && annotation.reason && (
        <p className="text-xs text-muted-foreground">
          {renderDetailsWithPidLinks(
            t(`validation-detail.${annotation.reason}`, {
              ...(annotation.details_params ?? extractDetailsParams(annotation.details)),
              defaultValue: annotation.details,
            }),
            krameriusClientUrl,
          )}
        </p>
      )}
      {annotation.hint && (
        <p className="text-xs text-muted-foreground/70">
          {t(`validation-hint.${annotation.hint}`, { defaultValue: annotation.hint })}
        </p>
      )}
    </div>
  );
}

function ScoreBadge({ score }: { score: number }) {
  const pct = (score * 100).toFixed(0);
  return (
    <span
      className={cn(
        "font-mono font-medium text-xs",
        score >= 0.9 && "text-green-600 dark:text-green-400",
        score >= 0.7 && score < 0.9 && "text-yellow-600 dark:text-yellow-400",
        score < 0.7 && "text-red-600 dark:text-red-400",
      )}
    >
      {pct}%
    </span>
  );
}
