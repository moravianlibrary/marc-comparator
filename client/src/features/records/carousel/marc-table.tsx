import { cn } from "@/lib/utils";
import type {
  MarcRecordData,
  FieldComparisonResult,
  SubfieldComparisonResult,
  ValidationResult,
} from "../types";

export type AnnotationType = "comparison" | "validation";

interface MarcTableProps {
  marc: MarcRecordData;
  annotationType?: AnnotationType;
  comparisonAnnotations?: FieldComparisonResult[];
  validationAnnotations?: ValidationResult[];
  targetTags?: Set<string>;
}

export function MarcTable({
  marc,
  annotationType,
  comparisonAnnotations,
  validationAnnotations,
  targetTags,
}: MarcTableProps) {
  const fixedEntries = Object.entries(marc.fixed_fields)
    .sort(([a], [b]) => parseInt(a) - parseInt(b))
    .filter(([tag]) => !targetTags || targetTags.has(tag));
  const variableEntries = Object.entries(marc.variable_fields)
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
        const valAnnotation = annotationType === "validation"
          ? validationAnnotations?.find((v) => v.target.tag === tag)
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
            validationAnnotation={valAnnotation}
          />
        );
      })}

      {/* Variable fields */}
      {variableEntries.flatMap(([tag, fields]) =>
        fields.map((field, fieldIdx) => {
          rowIndex++;
          const compAnnotation = annotationType === "comparison"
            ? comparisonAnnotations?.find((a) => a.tag === tag)
            : undefined;
          const valAnnotation = annotationType === "validation"
            ? validationAnnotations?.find((v) => v.target.tag === tag)
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
              validationAnnotation={valAnnotation}
            />
          );
        }),
      )}
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
  validationAnnotation?: ValidationResult;
}

function MarcRow({
  tag,
  ind1,
  ind2,
  subfields,
  striped,
  showAnnotationColumn,
  comparisonAnnotation,
  validationAnnotation,
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
        <div className={cn("px-3 py-1.5", showAnnotationColumn ? "w-[50%] flex-none" : "flex-1")}>
          {subfieldRows.map((sf, i) => (
            <div key={i} className="flex gap-3">
              <span className="w-[20px] flex-none font-mono text-sm text-muted-foreground">
                {sf.code === "_" ? "" : sf.code}
              </span>
              <span className="text-sm">{sf.value}</span>
            </div>
          ))}
        </div>

        {/* Annotation column */}
        {showAnnotationColumn && (
          <div className="flex-1 border-l px-3 py-1.5">
            {comparisonAnnotation && !hasSubfieldAnnotations && (
              <ComparisonFieldAnnotation annotation={comparisonAnnotation} />
            )}
            {comparisonAnnotation && hasSubfieldAnnotations && (
              <div>
                {subfieldRows.map((sf, i) => {
                  const srAnnotation = subfieldAnnotationMap.get(sf.code);
                  if (!srAnnotation) return <div key={i} className="text-xs">&nbsp;</div>;
                  return (
                    <div key={i} className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span className="font-mono w-[16px] flex-none">{srAnnotation.code}</span>
                      <ScoreBadge score={srAnnotation.score} />
                      {srAnnotation.value_b != null && (
                        <span className="truncate text-foreground">{srAnnotation.value_b}</span>
                      )}
                    </div>
                  );
                })}
                <ComparisonFieldAnnotation annotation={comparisonAnnotation} />
              </div>
            )}
            {validationAnnotation && (
              <ValidationFieldAnnotation annotation={validationAnnotation} />
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function ComparisonFieldAnnotation({ annotation }: { annotation: FieldComparisonResult }) {
  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground">
      <ScoreBadge score={annotation.score} />
      {annotation.explanation && (
        <span className="truncate">{annotation.explanation}</span>
      )}
    </div>
  );
}

function ValidationFieldAnnotation({ annotation }: { annotation: ValidationResult }) {
  return (
    <div className="space-y-0.5">
      <span
        className={cn(
          "text-xs font-medium",
          annotation.status === "Valid" && "text-green-600 dark:text-green-400",
          annotation.status === "Invalid" && "text-red-600 dark:text-red-400",
          annotation.status === "ForReview" && "text-yellow-600 dark:text-yellow-400",
        )}
      >
        {annotation.status}
      </span>
      {annotation.reason && (
        <p className="text-xs text-muted-foreground truncate">{annotation.reason}</p>
      )}
      {annotation.hint && (
        <p className="text-xs text-muted-foreground/70 truncate">{annotation.hint}</p>
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
