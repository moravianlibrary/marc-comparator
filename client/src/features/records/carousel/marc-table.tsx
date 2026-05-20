import { cn } from "@/lib/utils";
import type {
  MarcRecordData,
  FieldComparisonResult,
  ValidationResult,
} from "../types";

interface MarcTableProps {
  marc: MarcRecordData;
  comparisonAnnotations?: FieldComparisonResult[];
  validationAnnotations?: ValidationResult[];
}

export function MarcTable({
  marc,
  comparisonAnnotations,
  validationAnnotations,
}: MarcTableProps) {
  const fixedEntries = Object.entries(marc.fixed_fields);
  const variableEntries = Object.entries(marc.variable_fields);
  let rowIndex = 0;

  return (
    <div className="rounded-md border overflow-hidden">
      {/* Leader */}
      <MarcRow
        tag="LDR"
        ind1={null}
        ind2={null}
        subfields={{ _: [marc.leader] }}
        striped={false}
      />

      {/* Fixed fields (001, 003, 005, 008, etc.) */}
      {fixedEntries.map(([tag, value]) => {
        rowIndex++;
        return (
          <MarcRow
            key={`ff-${tag}`}
            tag={tag}
            ind1={null}
            ind2={null}
            subfields={{ _: [value] }}
            striped={rowIndex % 2 === 0}
          />
        );
      })}

      {/* Variable fields (100, 245, 700, etc.) */}
      {variableEntries.flatMap(([tag, fields]) =>
        fields.map((field, fieldIdx) => {
          rowIndex++;
          const compAnnotation = comparisonAnnotations?.find(
            (a) => a.tag === tag,
          );
          const valAnnotation = validationAnnotations?.find(
            (v) => v.target.tag === tag,
          );
          return (
            <MarcRow
              key={`vf-${tag}-${fieldIdx}`}
              tag={tag}
              ind1={field.ind1}
              ind2={field.ind2}
              subfields={field.subfields}
              striped={rowIndex % 2 === 0}
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
  comparisonAnnotation?: FieldComparisonResult;
  validationAnnotation?: ValidationResult;
}

function MarcRow({
  tag,
  ind1,
  ind2,
  subfields,
  striped,
  comparisonAnnotation,
  validationAnnotation,
}: MarcRowProps) {
  const i1 = ind1 ?? "-";
  const i2 = ind2 ?? "-";

  return (
    <div className={cn("border-b last:border-b-0", striped && "bg-muted/50")}>
      <div className="flex">
        <div className="flex w-[100px] flex-none items-start gap-2 px-3 py-1.5">
          <span className="font-mono text-sm font-medium">{tag}</span>
          <span className="font-mono text-sm text-muted-foreground">
            {i1}
            {i2}
          </span>
        </div>
        <div className="flex-1 px-1 py-1.5">
          {Object.entries(subfields).flatMap(([code, values]) =>
            values.map((value, vi) => (
              <div key={`${code}-${vi}`} className="flex gap-3">
                <span className="w-[20px] flex-none font-mono text-sm text-muted-foreground">
                  {code === "_" ? "" : code}
                </span>
                <span className="text-sm">{value}</span>
              </div>
            )),
          )}
        </div>
      </div>

      {comparisonAnnotation && (
        <div className="ml-[100px] border-t border-dashed bg-muted/30 px-3 py-1.5">
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <span>
              Score:{" "}
              <strong>
                {(comparisonAnnotation.score * 100).toFixed(0)}%
              </strong>
            </span>
            {comparisonAnnotation.explanation && (
              <span>{comparisonAnnotation.explanation}</span>
            )}
          </div>
          {comparisonAnnotation.subfield_results?.map((sr, i) => (
            <div
              key={i}
              className="mt-0.5 flex gap-4 text-xs text-muted-foreground"
            >
              <span className="font-mono">{sr.code}</span>
              <span>{(sr.score * 100).toFixed(0)}%</span>
              {sr.explanation && <span>{sr.explanation}</span>}
            </div>
          ))}
        </div>
      )}

      {validationAnnotation && (
        <div className="ml-[100px] border-t border-dashed bg-muted/30 px-3 py-1.5">
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <span
              className={cn(
                "font-medium",
                validationAnnotation.status === "Valid" && "text-green-600",
                validationAnnotation.status === "Invalid" && "text-red-600",
                validationAnnotation.status === "Warning" &&
                  "text-yellow-600",
              )}
            >
              {validationAnnotation.status}
            </span>
            {validationAnnotation.reason && (
              <span>{validationAnnotation.reason}</span>
            )}
          </div>
          {validationAnnotation.hint && (
            <p className="mt-0.5 text-xs text-muted-foreground">
              {validationAnnotation.hint}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
