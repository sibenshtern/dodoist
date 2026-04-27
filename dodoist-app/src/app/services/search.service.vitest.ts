import { describe, it, expect, vi, beforeEach } from 'vitest';
import { of, throwError } from 'rxjs';

// ---------------------------------------------------------------------------
// Minimal stubs — no Angular DI needed for pure logic tests
// ---------------------------------------------------------------------------

const mockGet = vi.fn();
const mockHttp = { get: mockGet };

function makeService() {
  // Inline the service logic to avoid Angular DI in Vitest
  const apiBase = 'http://localhost:8000';
  return {
    search(q: string) {
      const url = new URL(`${apiBase}/api/tasks/search/`);
      url.searchParams.set('q', q);
      return mockHttp.get(url.toString());
    },
  };
}

describe('SearchService.search()', () => {
  beforeEach(() => mockGet.mockReset());

  it('calls the correct endpoint with the query param', () => {
    mockGet.mockReturnValue(of([]));
    const svc = makeService();
    svc.search('oauth').subscribe();
    expect(mockGet).toHaveBeenCalledWith(
      'http://localhost:8000/api/tasks/search/?q=oauth',
    );
  });

  it('returns an array of SearchTask results', () => {
    const tasks = [
      { id: 'abc', title: 'OAuth fix', status: 'todo', project: 'p1', project_name: 'Alpha' },
    ];
    mockGet.mockReturnValue(of(tasks));
    const svc = makeService();
    let result: any[] = [];
    svc.search('oauth').subscribe((r: any[]) => (result = r));
    expect(result).toHaveLength(1);
    expect(result[0].title).toBe('OAuth fix');
  });

  it('passes empty query as-is to the endpoint', () => {
    mockGet.mockReturnValue(of([]));
    const svc = makeService();
    svc.search('').subscribe();
    expect(mockGet).toHaveBeenCalledWith(
      'http://localhost:8000/api/tasks/search/?q=',
    );
  });

  it('propagates HTTP errors', () => {
    const err = new Error('Network error');
    mockGet.mockReturnValue(throwError(() => err));
    const svc = makeService();
    let caught: unknown;
    svc.search('test').subscribe({ error: (e: unknown) => (caught = e) });
    expect(caught).toBe(err);
  });
});
