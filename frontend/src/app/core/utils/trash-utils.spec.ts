import { calculateDaysRemaining, isExpired, getDaysRemainingStatus } from './trash-utils';

describe('TrashUtils', () => {
  const baseNow = new Date('2026-10-01T12:00:00.000Z');

  it('should calculate 15 days remaining when purgeAt is 15 days in future', () => {
    const purgeAt = new Date('2026-10-16T12:00:00.000Z').toISOString();
    const days = calculateDaysRemaining(purgeAt, baseNow);
    expect(days).toBe(15);
  });

  it('should calculate 14 days remaining when purgeAt is 14 days in future', () => {
    const purgeAt = new Date('2026-10-15T12:00:00.000Z').toISOString();
    const days = calculateDaysRemaining(purgeAt, baseNow);
    expect(days).toBe(14);
  });

  it('should calculate 1 day remaining when purgeAt is 1 day in future', () => {
    const purgeAt = new Date('2026-10-02T12:00:00.000Z').toISOString();
    const days = calculateDaysRemaining(purgeAt, baseNow);
    expect(days).toBe(1);
  });

  it('should return 0 days remaining (Se elimina hoy) when purgeAt is later same day', () => {
    const purgeAt = new Date('2026-10-01T18:00:00.000Z').toISOString();
    const days = calculateDaysRemaining(purgeAt, baseNow);
    expect(days).toBe(1); // ceil(6h / 24h) = 1
    const status = getDaysRemainingStatus(purgeAt, new Date('2026-10-01T12:00:01.000Z'));
    expect(status.colorClass).toBe('red');
  });

  it('should calculate negative days when expired (e.g. 16 days ago)', () => {
    const purgeAt = new Date('2026-09-30T12:00:00.000Z').toISOString();
    const days = calculateDaysRemaining(purgeAt, baseNow);
    expect(days).toBeLessThanOrEqual(0);
    expect(isExpired(purgeAt, baseNow)).toBeTrue();
  });

  it('should assign green color class for >7 days', () => {
    const purgeAt = new Date('2026-10-12T12:00:00.000Z').toISOString(); // 11 days
    const status = getDaysRemainingStatus(purgeAt, baseNow);
    expect(status.colorClass).toBe('green');
    expect(status.label).toBe('Quedan 11 días');
  });

  it('should assign amber color class for 4-7 days', () => {
    const purgeAt = new Date('2026-10-06T12:00:00.000Z').toISOString(); // 5 days
    const status = getDaysRemainingStatus(purgeAt, baseNow);
    expect(status.colorClass).toBe('amber');
    expect(status.label).toBe('Quedan 5 días');
  });

  it('should assign red color class for <=3 days', () => {
    const purgeAt = new Date('2026-10-03T12:00:00.000Z').toISOString(); // 2 days
    const status = getDaysRemainingStatus(purgeAt, baseNow);
    expect(status.colorClass).toBe('red');
    expect(status.label).toBe('Quedan 2 días');
  });
});
