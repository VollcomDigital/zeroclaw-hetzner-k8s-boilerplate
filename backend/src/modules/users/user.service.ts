import { User, type IUser } from './user.model.js';
import { NotFoundError } from '../../common/errors/AppError.js';

export type UserDto = Pick<IUser, 'email' | 'name'> & { _id: string };

export async function findAll(): Promise<UserDto[]> {
  const docs = await User.find().lean().exec();
  return docs as unknown as UserDto[];
}

export async function findById(id: string): Promise<UserDto | null> {
  const doc = await User.findById(id).lean().exec();
  return doc as unknown as UserDto | null;
}

export async function create(data: { email: string; name: string }): Promise<UserDto> {
  const user = await new User(data).save();
  return { _id: user._id.toString(), email: user.email, name: user.name };
}

export async function update(
  id: string,
  data: Partial<{ email: string; name: string }>
): Promise<UserDto> {
  const user = await User.findByIdAndUpdate(id, data, { new: true }).lean().exec();
  if (!user) throw new NotFoundError('User not found');
  return { _id: user._id.toString(), email: user.email, name: user.name };
}

export async function remove(id: string): Promise<void> {
  const result = await User.findByIdAndDelete(id).exec();
  if (!result) throw new NotFoundError('User not found');
}
