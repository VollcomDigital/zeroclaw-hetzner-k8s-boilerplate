import { User, IUserDocument } from './user.model';
import { CreateUserInput, UpdateUserInput } from './user.validation';
import { ConflictError, NotFoundError } from '../../core/errors/app-error';

const USER_NOT_FOUND = 'User';

export class UserService {
  async create(data: CreateUserInput): Promise<IUserDocument> {
    const existingUser = await User.findOne({ email: data.email });
    if (existingUser) {
      throw new ConflictError('A user with this email already exists');
    }
    return User.create(data);
  }

  async findById(id: string): Promise<IUserDocument> {
    const user = await User.findById(id);
    if (!user) throw new NotFoundError(USER_NOT_FOUND);
    return user;
  }

  async findAll(page: number, limit: number): Promise<{ users: IUserDocument[]; total: number }> {
    const skip = (page - 1) * limit;
    const [users, total] = await Promise.all([
      User.find({ isActive: true }).skip(skip).limit(limit).sort({ createdAt: -1 }),
      User.countDocuments({ isActive: true }),
    ]);
    return { users, total };
  }

  async update(id: string, data: UpdateUserInput): Promise<IUserDocument> {
    const user = await User.findByIdAndUpdate(id, data, { new: true, runValidators: true });
    if (!user) throw new NotFoundError(USER_NOT_FOUND);
    return user;
  }

  async delete(id: string): Promise<void> {
    const user = await User.findByIdAndUpdate(id, { isActive: false }, { new: true });
    if (!user) throw new NotFoundError(USER_NOT_FOUND);
  }
}

export const userService = new UserService();
