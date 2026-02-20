import { NotFoundError } from '../../src/common/errors/AppError';

describe('User Service', () => {
  it('NotFoundError has correct status code', () => {
    const err = new NotFoundError('User not found');
    expect(err.statusCode).toBe(404);
    expect(err.message).toBe('User not found');
  });
});
