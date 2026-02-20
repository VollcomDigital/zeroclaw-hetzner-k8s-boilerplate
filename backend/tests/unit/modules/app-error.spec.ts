import {
  AppError,
  NotFoundError,
  BadRequestError,
  UnauthorizedError,
  HttpStatus,
  ValidationError,
} from '../../../src/core/errors/app-error';

describe('AppError', () => {
  it('should create an error with correct properties', () => {
    const error = new AppError('Test error', HttpStatus.BAD_REQUEST);

    expect(error.message).toBe('Test error');
    expect(error.statusCode).toBe(400);
    expect(error.isOperational).toBe(true);
    expect(error).toBeInstanceOf(Error);
    expect(error).toBeInstanceOf(AppError);
  });

  it('should allow non-operational errors', () => {
    const error = new AppError('Critical', HttpStatus.INTERNAL_SERVER_ERROR, false);
    expect(error.isOperational).toBe(false);
  });
});

describe('NotFoundError', () => {
  it('should create a 404 error', () => {
    const error = new NotFoundError('User');
    expect(error.message).toBe('User not found');
    expect(error.statusCode).toBe(404);
  });
});

describe('BadRequestError', () => {
  it('should create a 400 error', () => {
    const error = new BadRequestError('Invalid input');
    expect(error.message).toBe('Invalid input');
    expect(error.statusCode).toBe(400);
  });
});

describe('UnauthorizedError', () => {
  it('should create a 401 error with default message', () => {
    const error = new UnauthorizedError();
    expect(error.message).toBe('Authentication required');
    expect(error.statusCode).toBe(401);
  });

  it('should accept custom message', () => {
    const error = new UnauthorizedError('Token expired');
    expect(error.message).toBe('Token expired');
  });
});

describe('ValidationError', () => {
  it('should create a 422 error with field errors', () => {
    const errors = { email: ['Invalid email'], password: ['Too short'] };
    const error = new ValidationError(errors);

    expect(error.statusCode).toBe(422);
    expect(error.errors).toEqual(errors);
  });
});
