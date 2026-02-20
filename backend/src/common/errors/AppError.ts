/**
 * Base application error for centralized handling.
 */
export class AppError extends Error {
  constructor(
    public readonly statusCode: number,
    message: string,
    public readonly code?: string
  ) {
    super(message);
    Object.setPrototypeOf(this, AppError.prototype);
    this.name = 'AppError';
  }
}

/** 400 Bad Request */
export class BadRequestError extends AppError {
  constructor(message = 'Bad Request') {
    super(400, message, 'BAD_REQUEST');
  }
}

/** 401 Unauthorized */
export class UnauthorizedError extends AppError {
  constructor(message = 'Unauthorized') {
    super(401, message, 'UNAUTHORIZED');
  }
}

/** 403 Forbidden */
export class ForbiddenError extends AppError {
  constructor(message = 'Forbidden') {
    super(403, message, 'FORBIDDEN');
  }
}

/** 404 Not Found */
export class NotFoundError extends AppError {
  constructor(message = 'Not Found') {
    super(404, message, 'NOT_FOUND');
  }
}

/** 409 Conflict */
export class ConflictError extends AppError {
  constructor(message = 'Conflict') {
    super(409, message, 'CONFLICT');
  }
}
