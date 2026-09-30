import { useRef } from 'react';
import { Input } from '@/components/ui/input';
import { MATCH_SCALE_MAX } from '../score';

interface ScoreRangeInputsProps {
  scoreMin: number;
  scoreMax: number;
  onChange: (from: number, to: number) => void;
}

export function ScoreRangeInputs({ scoreMin, scoreMax, onChange }: ScoreRangeInputsProps) {
  const minRef = useRef<HTMLInputElement>(null);
  const maxRef = useRef<HTMLInputElement>(null);

  function handleSubmit() {
    const rawMin = Number(minRef.current?.value);
    const rawMax = Number(maxRef.current?.value);
    if (Number.isNaN(rawMin) || Number.isNaN(rawMax)) {
      return;
    }
    const clampedMin = Math.max(0, Math.min(rawMin, MATCH_SCALE_MAX));
    const clampedMax = Math.max(clampedMin, Math.min(rawMax, MATCH_SCALE_MAX));
    if (minRef.current) {
      minRef.current.value = String(clampedMin);
    }
    if (maxRef.current) {
      maxRef.current.value = String(clampedMax);
    }
    onChange(clampedMin, clampedMax);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter') {
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
        max={MATCH_SCALE_MAX}
        step={0.5}
        key={`min-${scoreMin}`}
        defaultValue={scoreMin}
        onKeyDown={handleKeyDown}
        onBlur={handleSubmit}
        className="h-6 w-14 px-1.5 text-xs tabular-nums text-center"
      />
      <span className="text-muted-foreground">–</span>
      <Input
        ref={maxRef}
        type="number"
        min={0}
        max={MATCH_SCALE_MAX}
        step={0.5}
        key={`max-${scoreMax}`}
        defaultValue={scoreMax}
        onKeyDown={handleKeyDown}
        onBlur={handleSubmit}
        className="h-6 w-14 px-1.5 text-xs tabular-nums text-center"
      />
      <span className="text-muted-foreground">/ {MATCH_SCALE_MAX}</span>
    </div>
  );
}
