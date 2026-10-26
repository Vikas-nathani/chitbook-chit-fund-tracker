import { useEffect, useMemo, useRef, useState } from 'react';
import { formatCompactRupees, formatSignedRupees, formatRupees } from '../../format';

export interface BarSeries {
  key: string;
  label: string;
  color: string;
}

export interface LineSeries {
  key: string;
  label: string;
  color: string;
}

export interface LegendItem {
  label: string;
  color: string;
  kind: 'bar' | 'line';
}

interface Props {
  /** One row per month: x label plus numeric values keyed by series key. */
  data: { label: string; values: Record<string, number> }[];
  bars: BarSeries[];
  /** Optional per-bar color override (e.g. profit vs loss for one series). */
  barColor?: (seriesKey: string, value: number) => string;
  line?: LineSeries;
  legend: LegendItem[];
  /** Show tooltip values with +/- signs. */
  signed?: boolean;
  /** Highlight this x label (the current month). */
  highlightLabel?: string;
  height?: number;
  ariaLabel: string;
}

const PAD = { top: 16, right: 12, bottom: 30, left: 56 };
const MAX_BAR = 24;
const GAP = 2;
const RADIUS = 4;

/** Clean tick step for a range: 1, 2, 2.5 or 5 x 10^n. */
function niceStep(range: number, targetTicks: number) {
  const raw = range / targetTicks;
  const pow = Math.pow(10, Math.floor(Math.log10(raw || 1)));
  const n = raw / pow;
  const nice = n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10;
  return nice * pow;
}

/** Bar with a rounded data end and a square baseline end; grows up or down from the baseline. */
function barPath(x: number, w: number, base: number, end: number) {
  const h = Math.abs(end - base);
  if (h < 0.5) return '';
  const r = Math.min(RADIUS, h, w / 2);
  if (end < base) {
    // grows upward: rounded top
    return `M${x},${base} V${end + r} Q${x},${end} ${x + r},${end} H${x + w - r} Q${x + w},${end} ${x + w},${end + r} V${base} Z`;
  }
  // grows downward: rounded bottom
  return `M${x},${base} V${end - r} Q${x},${end} ${x + r},${end} H${x + w - r} Q${x + w},${end} ${x + w},${end - r} V${base} Z`;
}

export function MonthlyChart({ data, bars, barColor, line, legend, signed, highlightLabel, height = 260, ariaLabel }: Props) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(640);
  const [hover, setHover] = useState<number | null>(null);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => setWidth(Math.max(280, entry.contentRect.width)));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const keys = useMemo(() => [...bars.map((b) => b.key), ...(line ? [line.key] : [])], [bars, line]);

  const scale = useMemo(() => {
    let min = 0;
    let max = 0;
    for (const row of data) {
      for (const k of keys) {
        const v = row.values[k] ?? 0;
        if (!Number.isFinite(v)) continue;
        min = Math.min(min, v);
        max = Math.max(max, v);
      }
    }
    if (min === 0 && max === 0) max = 1000;
    const step = niceStep(max - min, 4);
    const lo = Math.floor(min / step) * step;
    const hi = Math.ceil(max / step) * step;
    const ticks: number[] = [];
    for (let t = lo; t <= hi + step / 2; t += step) ticks.push(Math.round(t));
    return { lo, hi, ticks };
  }, [data, keys]);

  const innerW = width - PAD.left - PAD.right;
  const innerH = height - PAD.top - PAD.bottom;
  const band = data.length ? innerW / data.length : innerW;
  const y = (v: number) => PAD.top + ((scale.hi - v) / (scale.hi - scale.lo || 1)) * innerH;
  const baseY = y(0);
  const barW = Math.max(4, Math.min(MAX_BAR, (band * 0.62 - GAP * (bars.length - 1)) / bars.length));
  const groupW = barW * bars.length + GAP * (bars.length - 1);
  // Thin out x labels so they never collide (~46px per label)
  const labelEvery = Math.max(1, Math.ceil((data.length * 46) / innerW));

  // Non-finite line values (e.g. future months) are skipped so the line stops instead of running flat
  const linePoints = line
    ? data
        .map((row, i) => ({ i, v: row.values[line.key] }))
        .filter((p) => Number.isFinite(p.v))
        .map((p) => ({ i: p.i, x: PAD.left + band * p.i + band / 2, y: y(p.v) }))
    : [];

  const tooltipLeft = hover === null ? 0 : Math.min(Math.max(PAD.left + band * hover + band / 2, 90), width - 90);

  return (
    <div className="chart">
      <ul className="chart-legend">
        {legend.map((item) => (
          <li key={item.label}>
            <span
              className={item.kind === 'line' ? 'legend-line' : 'legend-swatch'}
              style={{ background: item.color }}
              aria-hidden
            />
            {item.label}
          </li>
        ))}
      </ul>

      <div
        className="chart-plot"
        ref={wrapRef}
        onPointerLeave={(e) => {
          // Touch keeps the tapped month open; mouse clears on leave
          if (e.pointerType === 'mouse') setHover(null);
        }}
      >
        <svg width={width} height={height} role="img" aria-label={ariaLabel}>
          {/* gridlines + y ticks */}
          {scale.ticks.map((t) => (
            <g key={t}>
              <line x1={PAD.left} x2={width - PAD.right} y1={y(t)} y2={y(t)} className={t === 0 ? 'chart-baseline' : 'chart-grid'} />
              <text x={PAD.left - 8} y={y(t)} className="chart-tick" textAnchor="end" dominantBaseline="middle">
                {formatCompactRupees(t)}
              </text>
            </g>
          ))}

          {data.map((row, i) => {
            const x0 = PAD.left + band * i + (band - groupW) / 2;
            const isHi = row.label === highlightLabel;
            return (
              <g key={row.label}>
                {(hover === i || isHi) && (
                  <rect
                    x={PAD.left + band * i + 2}
                    y={PAD.top}
                    width={band - 4}
                    height={innerH}
                    rx={6}
                    className={hover === i ? 'chart-hover-band' : 'chart-now-band'}
                  />
                )}
                {bars.map((s, j) => {
                  const v = row.values[s.key] ?? 0;
                  return (
                    <path
                      key={s.key}
                      d={barPath(x0 + j * (barW + GAP), barW, baseY, y(v))}
                      fill={barColor ? barColor(s.key, v) : s.color}
                    />
                  );
                })}
                {i % labelEvery === 0 && (
                  <text x={PAD.left + band * i + band / 2} y={height - 10} textAnchor="middle" className={`chart-tick ${isHi ? 'is-now' : ''}`}>
                    {row.label}
                  </text>
                )}
              </g>
            );
          })}

          {line && linePoints.length > 1 && (
            <polyline
              points={linePoints.map((p) => `${p.x},${p.y}`).join(' ')}
              fill="none"
              stroke={line.color}
              strokeWidth={2}
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          )}
          {line &&
            linePoints.map((p) => (
              <circle key={p.i} cx={p.x} cy={p.y} r={hover === p.i ? 5 : 4} fill={line.color} stroke="#fff" strokeWidth={2} />
            ))}

          {/* hit targets: the whole month band, bigger than any mark */}
          {data.map((row, i) => (
            <rect
              key={row.label}
              x={PAD.left + band * i}
              y={PAD.top}
              width={band}
              height={innerH}
              fill="transparent"
              onPointerEnter={() => setHover(i)}
              onPointerDown={() => setHover(i)}
              onClick={() => setHover(i)}
            />
          ))}
        </svg>

        {hover !== null && data[hover] && (
          <div className="chart-tooltip" style={{ left: tooltipLeft }}>
            <strong>{data[hover].label}</strong>
            {bars.map((s) => {
              const v = data[hover].values[s.key] ?? 0;
              return (
                <div key={s.key} className="chart-tooltip-row">
                  <span className="legend-swatch" style={{ background: barColor ? barColor(s.key, v) : s.color }} />
                  <span>{s.label}</span>
                  <b>{signed ? formatSignedRupees(v) : formatRupees(v)}</b>
                </div>
              );
            })}
            {line && Number.isFinite(data[hover].values[line.key]) && (
              <div className="chart-tooltip-row">
                <span className="legend-line" style={{ background: line.color }} />
                <span>{line.label}</span>
                <b>{signed ? formatSignedRupees(data[hover].values[line.key]) : formatRupees(data[hover].values[line.key])}</b>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
