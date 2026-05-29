import { useRef } from "react";
import { Input } from "@/components/ui/input";

interface ScoreRangeInputsProps {
  scoreMin: number;
  scoreMax: number;
  onChange: (from: number, to: number) => void;
}

export function ScoreRangeInputs({
  scoreMin,
  scoreMax,
  onChange,
}: ScoreRangeInputsProps) {
  const minRef = useRef<HTMLInputElement>(null);
  const maxRef = useRef<HTMLInputElement>(null);

  function handleSubmit() {
    const rawMin = Number(minRef.current?.value);
    const rawMax = Number(maxRef.current?.value);
    if (Number.isNaN(rawMin) || Number.isNaN(rawMax)) return;
    const clampedMin = Math.max(0, Math.min(rawMin, 100));
    const clampedMax = Math.max(clampedMin, Math.min(rawMax, 100));
    if (minRef.current) minRef.current.value = String(clampedMin);
    if (maxRef.current) maxRef.current.value = String(clampedMax);
    onChange(clampedMin / 100, clampedMax / 100);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSubmit();
      (e.target as HTMLInputElement).blur();
    }
  }

  return (
    <div className="flex items-center gap-1.5 text-xs">
      <Input
        ref={minRef}
        type="number"
        min={0}
        max={100}
        key={scoreMin}
        defaultValue={Math.round(scoreMin * 100)}
        onKeyDown={handleKeyDown}
        onBlur={handleSubmit}
        className="h-6 w-14 px-1.5 text-xs tabular-nums text-center"
      />
      <span className="text-muted-foreground">–</span>
      <Input
        ref={maxRef}
        type="number"
        min={0}
        max={100}
        key={scoreMax}
        defaultValue={Math.round(scoreMax * 100)}
        onKeyDown={handleKeyDown}
        onBlur={handleSubmit}
        className="h-6 w-14 px-1.5 text-xs tabular-nums text-center"
      />
      <span className="text-muted-foreground">%</span>
    </div>
  );
}
