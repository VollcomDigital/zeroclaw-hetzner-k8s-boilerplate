import jwt from 'jsonwebtoken';
import { User, IUserDocument } from '../users/user.model';
import { RegisterInput, LoginInput } from './auth.validation';
import { ConflictError, UnauthorizedError } from '../../core/errors/app-error';
import { env } from '../../config/env';

interface TokenPayload {
  userId: string;
  email: string;
  role: string;
}

interface AuthResult {
  user: ReturnType<IUserDocument['toPublicJSON']>;
  token: string;
}

export class AuthService {
  async register(data: RegisterInput): Promise<AuthResult> {
    const existingUser = await User.findOne({ email: data.email });
    if (existingUser) {
      throw new ConflictError('A user with this email already exists');
    }

    const user = await User.create(data);
    const token = this.generateToken(user);

    return { user: user.toPublicJSON(), token };
  }

  async login(data: LoginInput): Promise<AuthResult> {
    const user = await User.findByEmail(data.email);
    if (!user || !user.isActive) {
      throw new UnauthorizedError('Invalid email or password');
    }

    const isPasswordValid = await user.comparePassword(data.password);
    if (!isPasswordValid) {
      throw new UnauthorizedError('Invalid email or password');
    }

    const token = this.generateToken(user);

    return { user: user.toPublicJSON(), token };
  }

  verifyToken(token: string): TokenPayload {
    try {
      return jwt.verify(token, env.JWT_SECRET) as TokenPayload;
    } catch {
      throw new UnauthorizedError('Invalid or expired token');
    }
  }

  private generateToken(user: IUserDocument): string {
    const payload: TokenPayload = {
      userId: (user._id as { toString(): string }).toString(),
      email: user.email,
      role: user.role,
    };

    return jwt.sign(payload, env.JWT_SECRET, {
      expiresIn: env.JWT_EXPIRES_IN as string,
    } as jwt.SignOptions);
  }
}

export const authService = new AuthService();
