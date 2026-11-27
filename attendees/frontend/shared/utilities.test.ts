import { describe, it, expect, beforeEach } from 'vitest';
import {
  escapeHtml,
  normalizePhoneNumber,
  validateFastInputPhoneNumber,
  validateFastInputEmail,
  validateFastInputContact,
  getDaysInMonth,
  validateFastInputBirthday,
  getEditingEnabled,
  setEditingEnabled,
} from './utilities';

describe('shared/utilities', () => {
  describe('escapeHtml', () => {
    it('should escape unsafe HTML characters', () => {
      expect(escapeHtml('<script>alert("xss")</script>')).toBe(
        '&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;'
      );
      expect(escapeHtml("John & Mary's")).toBe('John &amp; Mary&#39;s');
    });

    it('should handle empty or null values', () => {
      expect(escapeHtml('')).toBe('');
      expect(escapeHtml(null as any)).toBe('');
      expect(escapeHtml(undefined as any)).toBe('');
    });
  });

  describe('normalizePhoneNumber', () => {
    it('should normalize 10-digit US numbers with +1 prefix', () => {
      expect(normalizePhoneNumber('1234567890')).toBe('+11234567890');
      expect(normalizePhoneNumber('(123) 456-7890')).toBe('+11234567890');
      expect(normalizePhoneNumber('123-456-7890')).toBe('+11234567890');
    });

    it('should normalize 11-digit numbers starting with 1', () => {
      expect(normalizePhoneNumber('11234567890')).toBe('+11234567890');
      expect(normalizePhoneNumber('+1-123-456-7890')).toBe('+11234567890');
    });

    it('should preserve international numbers starting with +', () => {
      expect(normalizePhoneNumber('+886912345678')).toBe('+886912345678');
    });

    it('should handle empty inputs gracefully', () => {
      expect(normalizePhoneNumber('')).toBe('');
      expect(normalizePhoneNumber(null as any)).toBe('');
    });
  });

  describe('validateFastInputPhoneNumber', () => {
    it('should return true for valid phone numbers with 10 or more digits', () => {
      expect(validateFastInputPhoneNumber('1234567890')).toBe(true);
      expect(validateFastInputPhoneNumber('(555) 123-4567')).toBe(true);
      expect(validateFastInputPhoneNumber('+15551234567')).toBe(true);
    });

    it('should return false for invalid phone numbers with less than 10 digits', () => {
      expect(validateFastInputPhoneNumber('12345')).toBe(false);
      expect(validateFastInputPhoneNumber('')).toBe(false);
      expect(validateFastInputPhoneNumber('abc')).toBe(false);
    });
  });

  describe('validateFastInputEmail', () => {
    it('should return true for valid emails', () => {
      expect(validateFastInputEmail('user@example.com')).toBe(true);
      expect(validateFastInputEmail('a@b.co')).toBe(true);
    });

    it('should return false for invalid emails', () => {
      expect(validateFastInputEmail('userexample.com')).toBe(false);
      expect(validateFastInputEmail('user@')).toBe(false);
      expect(validateFastInputEmail('@example.com')).toBe(false);
      expect(validateFastInputEmail('a@b')).toBe(false);
      expect(validateFastInputEmail('')).toBe(false);
    });
  });

  describe('validateFastInputContact', () => {
    it('should validate phone and whatsapp via phone validator', () => {
      expect(validateFastInputContact('phone', '1234567890')).toBe(true);
      expect(validateFastInputContact('whatsapp', '1234567890')).toBe(true);
      expect(validateFastInputContact('phone', '123')).toBe(false);
    });

    it('should validate email via email validator', () => {
      expect(validateFastInputContact('email', 'test@test.com')).toBe(true);
      expect(validateFastInputContact('email', 'invalid')).toBe(false);
    });

    it('should validate generic contact types with length >= 2', () => {
      expect(validateFastInputContact('wechat', 'wx_user')).toBe(true);
      expect(validateFastInputContact('wechat', 'a')).toBe(false);
      expect(validateFastInputContact('line', '  ')).toBe(false);
    });
  });

  describe('getDaysInMonth', () => {
    it('should return correct days for leap years and non-leap years in February', () => {
      expect(getDaysInMonth(2024, 2)).toBe(29); // Leap year
      expect(getDaysInMonth(2023, 2)).toBe(28); // Non-leap year
      expect(getDaysInMonth(2000, 2)).toBe(29); // Century leap year
      expect(getDaysInMonth(1900, 2)).toBe(28); // Non-leap century
    });

    it('should return 30 days for 30-day months', () => {
      expect(getDaysInMonth(2024, 4)).toBe(30);
      expect(getDaysInMonth(2024, 6)).toBe(30);
      expect(getDaysInMonth(2024, 9)).toBe(30);
      expect(getDaysInMonth(2024, 11)).toBe(30);
    });

    it('should return 31 days for 31-day months', () => {
      expect(getDaysInMonth(2024, 1)).toBe(31);
      expect(getDaysInMonth(2024, 3)).toBe(31);
      expect(getDaysInMonth(2024, 5)).toBe(31);
      expect(getDaysInMonth(2024, 7)).toBe(31);
      expect(getDaysInMonth(2024, 8)).toBe(31);
      expect(getDaysInMonth(2024, 10)).toBe(31);
      expect(getDaysInMonth(2024, 12)).toBe(31);
    });

    it('should fallback to 29 for Feb when year is not provided', () => {
      expect(getDaysInMonth(null, 2)).toBe(29);
      expect(getDaysInMonth('', 2)).toBe(29);
    });
  });

  describe('validateFastInputBirthday', () => {
    it('should return valid when all fields are empty (optional)', () => {
      expect(validateFastInputBirthday('', '', '')).toEqual({ valid: true });
      expect(validateFastInputBirthday(null, null, null)).toEqual({ valid: true });
    });

    it('should return error if day is specified without month', () => {
      const res = validateFastInputBirthday('', '', '15');
      expect(res.valid).toBe(false);
      expect(res.message).toContain('Birth month is required');
    });

    it('should return error for birth year earlier than 1900', () => {
      const res = validateFastInputBirthday('1899', '5', '1');
      expect(res.valid).toBe(false);
      expect(res.message).toContain('1900 or later');
    });

    it('should return error for future birth year', () => {
      const futureYear = new Date().getFullYear() + 2;
      const res = validateFastInputBirthday(String(futureYear), '5', '1');
      expect(res.valid).toBe(false);
      expect(res.message).toContain('cannot exceed');
    });

    it('should return error for invalid calendar day like Feb 30', () => {
      const res = validateFastInputBirthday('2024', '2', '30');
      expect(res.valid).toBe(false);
      expect(res.message).toContain('Invalid calendar date');
    });

    it('should return valid for valid full date', () => {
      expect(validateFastInputBirthday('2000', '5', '15')).toEqual({ valid: true });
      expect(validateFastInputBirthday('2024', '2', '29')).toEqual({ valid: true });
    });

    it('should allow partial birthday (month and day without year)', () => {
      expect(validateFastInputBirthday('', '5', '15')).toEqual({ valid: true });
    });
  });

  describe('getEditingEnabled and setEditingEnabled', () => {
    beforeEach(() => {
      setEditingEnabled(false);
    });

    it('should toggle editing state correctly', () => {
      expect(getEditingEnabled()).toBe(false);
      setEditingEnabled(true);
      expect(getEditingEnabled()).toBe(true);
      setEditingEnabled(false);
      expect(getEditingEnabled()).toBe(false);
    });
  });
});
