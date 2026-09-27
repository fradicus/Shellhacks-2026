/** The two scenes share controls, but keep their own scale range and scoped styles. */
export function SceneControls({ styles: s, flat, onFlat, yearPx, onYearPx, range, onOverview }: {
  styles: Record<string, string>;
  flat: boolean;
  onFlat(flat: boolean): void;
  yearPx: number;
  onYearPx(value: number): void;
  range: readonly [min: number, max: number, step: number];
  onOverview(): void;
}) {
  return (
    <div className={s.controls}>
      <div className={s.seg} role="group" aria-label="Dimensions">
        <button type="button" aria-pressed={flat} onClick={() => onFlat(true)}>2D</button>
        <button type="button" aria-pressed={!flat} onClick={() => onFlat(false)}>3D</button>
      </div>
      <label className={s.slider}>
        <span>1 year = <b>{yearPx}px</b></span>
        <input type="range" min={range[0]} max={range[1]} step={range[2]} value={yearPx} disabled={flat}
          onChange={(event) => onYearPx(Number(event.target.value))} />
      </label>
      <button type="button" className={s.reset} onClick={onOverview}>Overview</button>
    </div>
  );
}
