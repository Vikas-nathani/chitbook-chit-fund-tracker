import { formatCompactRupees, formatRupees, formatSignedRupees, initials, monthLabel, periodLabel } from './format';

describe('format', () => {
  it('uses Indian grouping for rupees', () => {
    expect(formatRupees(250000)).toBe('₹2,50,000');
    expect(formatSignedRupees(-8500)).toBe('−₹8,500');
    expect(formatSignedRupees(0)).toBe('₹0');
  });

  it('compacts chart amounts into K / L / Cr', () => {
    expect(formatCompactRupees(12500)).toBe('₹13K');
    expect(formatCompactRupees(250000)).toBe('₹2.5L');
    expect(formatCompactRupees(-12000000)).toBe('−₹1.2Cr');
  });

  it('labels chit months from the start month', () => {
    expect(monthLabel('2026-11', 3)).toBe('Jan 27');
    expect(periodLabel('2026-11', 10)).toBe('Nov 2026 – Aug 2027');
  });

  it('builds avatar initials', () => {
    expect(initials('Ravi Kumar')).toBe('RK');
    expect(initials('sita')).toBe('SI');
    expect(initials('  ')).toBe('?');
  });
});
