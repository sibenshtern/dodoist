import { describe, it, expect, vi } from 'vitest';
import { of } from 'rxjs';

function makeCommentsService() {
  const http = { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() };
  const comment = { id: 'c1', task_id: 't1', body: {}, is_edited: false, created_at: '', updated_at: '', parent_comment_id: null, author: { id: 'u1', display_name: 'Alice', email: 'a@b.com', avatar_url: '' } };

  http.get.mockReturnValue(of([comment]));
  http.post.mockReturnValue(of(comment));
  http.patch.mockReturnValue(of({ ...comment, is_edited: true }));
  http.delete.mockReturnValue(of(undefined));

  return {
    list: (taskId: string) => http.get(`/api/tasks/${taskId}/comments/`),
    get: (commentId: string) => http.get(`/api/comments/${commentId}/`),
    create: (taskId: string, body: unknown) => http.post(`/api/tasks/${taskId}/comments/`, { body }),
    update: (commentId: string, body: unknown) => http.patch(`/api/comments/${commentId}/`, { body }),
    delete: (commentId: string) => http.delete(`/api/comments/${commentId}/`),
    _http: http,
    _comment: comment,
  };
}

describe('CommentsService', () => {
  it('list calls the correct endpoint', () => {
    const svc = makeCommentsService();
    let result: unknown[] = [];
    svc.list('task-123').subscribe((c: unknown) => result = c as unknown[]);
    expect(svc._http.get).toHaveBeenCalledWith('/api/tasks/task-123/comments/');
    expect((result as { id: string }[])[0].id).toBe('c1');
  });

  it('create posts to task comments endpoint', () => {
    const svc = makeCommentsService();
    const body = { type: 'doc', content: [] };
    svc.create('task-123', body).subscribe();
    expect(svc._http.post).toHaveBeenCalledWith('/api/tasks/task-123/comments/', { body });
  });

  it('delete calls comment endpoint', () => {
    const svc = makeCommentsService();
    svc.delete('c1').subscribe();
    expect(svc._http.delete).toHaveBeenCalledWith('/api/comments/c1/');
  });

  it('update patches body', () => {
    const svc = makeCommentsService();
    const newBody = { type: 'doc', content: [{ type: 'text', text: 'hi' }] };
    let updated: { is_edited?: boolean } = {};
    svc.update('c1', newBody).subscribe((c: unknown) => updated = c as { is_edited?: boolean });
    expect(updated.is_edited).toBe(true);
  });
});
