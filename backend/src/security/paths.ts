import fs from 'fs';
import path from 'path';
import { validUserId } from './dispatch';

// The recording tree must be owned by the service, never writable by other local users.
// Reject existing symlinks before mkdir/IO; O_NOFOLLOW also protects the final write.
export function assertNoSymlinks(target: string): void {
  const absolute = path.resolve(target);
  const root = path.parse(absolute).root;
  let current = root;
  for (const segment of absolute.slice(root.length).split(path.sep)) {
    current = path.join(current, segment);
    try {
      if (fs.lstatSync(current).isSymbolicLink()) throw new Error('Symlink in recording path');
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error;
    }
  }
}

export function recordingFolder(root: string, userId: string): string {
  if (!validUserId(userId)) throw new Error('Invalid userId');
  const parent = path.resolve(root);
  const target = path.resolve(parent, userId);
  if (!target.startsWith(parent + path.sep)) throw new Error('Recording path escapes root');
  assertNoSymlinks(target);
  return target;
}

export function recordingFile(root: string, userId: string, fileId: string, extension: string): string {
  if (!/^[A-Za-z0-9_-]{1,512}$/.test(fileId) || !/^\.[A-Za-z0-9]{1,10}$/.test(extension)) throw new Error('Invalid recording filename');
  const target = path.join(recordingFolder(root, userId), fileId + extension);
  assertNoSymlinks(target);
  return target;
}
