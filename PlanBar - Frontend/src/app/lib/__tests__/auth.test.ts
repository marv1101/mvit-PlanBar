import { describe, it, expect } from 'vitest';
import { getAccessToken, getRefreshToken, setTokens, clearTokens } from '../auth';

describe('auth', () => {
  describe('getAccessToken', () => {
    it('gibt null zurück', () => {
      expect(getAccessToken()).toBeNull();
    });
  });

  describe('getRefreshToken', () => {
    it('gibt null zurück', () => {
      expect(getRefreshToken()).toBeNull();
    });
  });

  describe('setTokens', () => {
    it('ist ein No-Op und wirft keinen Fehler', () => {
      expect(() => setTokens('access', 'refresh')).not.toThrow();
    });
  });

  describe('clearTokens', () => {
    it('ist ein No-Op und wirft keinen Fehler', () => {
      expect(() => clearTokens()).not.toThrow();
    });
  });
});
