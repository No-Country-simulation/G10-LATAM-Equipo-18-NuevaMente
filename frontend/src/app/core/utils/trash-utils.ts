import { environment } from '../../../environments/environment';

export function calculateDaysRemaining(purgeAt?: string | null, nowDate: Date = new Date()): number {
  if (!purgeAt) {
    return environment.trashRetentionDays ?? 15;
  }
  const purgeMs = new Date(purgeAt).getTime();
  const nowMs = nowDate.getTime();
  if (isNaN(purgeMs)) return environment.trashRetentionDays ?? 15;

  const diffMs = purgeMs - nowMs;
  const msPerDay = 1000 * 60 * 60 * 24;
  return Math.ceil(diffMs / msPerDay);
}

export function isExpired(purgeAt?: string | null, nowDate: Date = new Date()): boolean {
  if (!purgeAt) return false;
  const purgeMs = new Date(purgeAt).getTime();
  if (isNaN(purgeMs)) return false;
  return purgeMs < nowDate.getTime() || calculateDaysRemaining(purgeAt, nowDate) < 0;
}

export interface DaysRemainingStatus {
  label: string;
  days: number;
  colorClass: 'green' | 'amber' | 'red';
  ratio: number;
}

export function getDaysRemainingStatus(purgeAt?: string | null, nowDate: Date = new Date()): DaysRemainingStatus {
  const days = calculateDaysRemaining(purgeAt, nowDate);
  const maxDays = environment.trashRetentionDays ?? 15;
  const ratio = Math.max(0, Math.min(1, days / maxDays));

  if (days > 7) {
    return {
      label: `Quedan ${days} días`,
      days,
      colorClass: 'green',
      ratio
    };
  } else if (days >= 4) {
    return {
      label: `Quedan ${days} días`,
      days,
      colorClass: 'amber',
      ratio
    };
  } else if (days >= 1) {
    return {
      label: `Quedan ${days} día${days > 1 ? 's' : ''}`,
      days,
      colorClass: 'red',
      ratio
    };
  } else {
    return {
      label: 'Se elimina hoy',
      days: 0,
      colorClass: 'red',
      ratio: 0
    };
  }
}
