import { ApiError, NETWORK_ERROR } from '@/api/client';

import { en } from './en';
import { te } from './te';
import { translate, translateError } from './index';

describe('dictionaries', () => {
  it('Telugu has every English key', () => {
    expect(Object.keys(te).sort()).toEqual(Object.keys(en).sort());
  });

  it('fills placeholders', () => {
    expect(translate('en', 'dashboard.monthOf', { n: 2, total: 20 })).toBe('Month 2 of 20');
  });
});

describe('translateError', () => {
  it('maps API error codes to text in both languages', () => {
    const err = new ApiError(401, 'AUTH_INVALID_CREDENTIALS', 'Invalid username or password');
    expect(translateError('en', err)).toBe('Invalid username or password.');
    expect(translateError('te', err)).toBe(te['errors.AUTH_INVALID_CREDENTIALS']);
  });

  it('shows lockout minutes from the error details', () => {
    const err = new ApiError(429, 'AUTH_ACCOUNT_LOCKED', 'locked', { retryAfterSeconds: 290 });
    expect(translateError('en', err)).toBe('Too many failed attempts. Try again in 5 minutes.');
  });

  it('falls back to the API message for codes without their own text', () => {
    const err = new ApiError(400, 'CHIT_INVALID_INPUT', 'Months must be between 1 and 120');
    expect(translateError('en', err)).toBe('Months must be between 1 and 120');
  });

  it('handles network failures and unknown errors', () => {
    expect(translateError('en', new ApiError(0, NETWORK_ERROR, ''))).toBe(en['errors.network']);
    expect(translateError('en', new Error('boom'))).toBe(en['errors.unknown']);
  });
});
